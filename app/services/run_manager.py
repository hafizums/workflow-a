from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.schemas import CanvasNode, NodeStatus, Project, RunJob, new_id
from app.services import node_runner, project_store
from app.services.cost_estimator import evaluate_cost_guard
from app.services.registry import resolve_model_for_node
from app.services.utility_tools import UTILITY_NODE_TYPES
from app.services.wavespeed_adapter import WaveSpeedAdapter
from app.services.workflow_resolver import (
    build_execution_plan,
    build_graph,
    build_workflow_plan,
    resolve_inputs_for_node,
    validate_prompt_card_inputs,
)

TERMINAL_STATUSES = {"success", "error", "cancelled"}
ACTIVE_STATUSES = {"queued", "running", "cancel_requested"}


class RunManagerError(ValueError):
    pass


class JobNotFoundError(RunManagerError):
    pass


class LocalRunManager:
    def __init__(self) -> None:
        self.jobs: dict[str, RunJob] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.worker_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self.worker_task and not self.worker_task.done():
            return
        self.worker_task = asyncio.create_task(self._worker(), name="local-run-manager")

    async def stop(self) -> None:
        if not self.worker_task:
            return
        self.worker_task.cancel()
        try:
            await self.worker_task
        except asyncio.CancelledError:
            pass
        self.worker_task = None

    async def list_jobs(
        self,
        *,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[RunJob]:
        jobs = sorted(self.jobs.values(), key=lambda job: job.created_at, reverse=True)
        if project_id:
            jobs = [job for job in jobs if job.project_id == project_id]
        if status:
            jobs = [job for job in jobs if job.status == status]
        return jobs[: max(1, min(limit, 200))]

    async def get_job(self, job_id: str) -> RunJob:
        job = self.jobs.get(job_id)
        if job is None:
            raise JobNotFoundError("Job not found")
        return job

    async def queue_node_run(
        self,
        project_id: str,
        node_id: str,
        save_to_project: bool = True,
        request_metadata: dict[str, Any] | None = None,
    ) -> RunJob:
        project = await project_store.load_project(project_id)
        node = find_node(project, node_id)
        if node is None:
            raise RunManagerError("Node not found in project")
        if node.type in UTILITY_NODE_TYPES:
            raise RunManagerError("Utility nodes are local-only and do not run directly. Connect this node to a runnable WaveSpeed node and run the downstream node or graph.")
        self._assert_no_active_node_job(project_id, node_id)
        graph = build_graph(project)
        prompt_errors = validate_prompt_card_inputs(node, graph)
        if prompt_errors:
            raise RunManagerError(prompt_errors[0]["message"])
        resolution = resolve_model_for_node(
            node_type=node.type,
            node_model_id=node.model_id,
            project_model_overrides=project.settings.model_overrides,
        )
        if resolution.error:
            raise RunManagerError(resolution.error)
        if not resolution.model or not resolution.model.enabled or not resolution.model_id:
            raise RunManagerError("Node is not backed by an enabled model.")
        guard = evaluate_cost_guard(resolution.model.estimated_base_cost_usd, project.settings.cost_guard)
        if guard["blocked"]:
            raise RunManagerError(guard["cost_guard_message"] or "Run blocked by local estimated cost guard.")

        node.status = NodeStatus.queued
        node.error_message = None
        node.estimated_base_cost_usd = resolution.model.estimated_base_cost_usd
        await project_store.save_project(project)

        job = RunJob(
            project_id=project_id,
            kind="single_node",
            node_id=node_id,
            mode="selected",
            request={
                "project_id": project_id,
                "node_id": node_id,
                "save_to_project": save_to_project,
                "model_id": resolution.model_id,
                "model_display_name": resolution.model.label if resolution.model else None,
                "estimated_cost_snapshot": resolution.model.estimated_base_cost_usd if resolution.model else None,
                "input_snapshot": dict(node.inputs or {}),
                **(request_metadata or {}),
            },
            progress_total=1,
            node_ids=[node_id],
            warnings=[],
        )
        await self._enqueue(job)
        return job

    async def queue_workflow_run(self, project_id: str, mode: str, node_id: str | None = None) -> RunJob:
        project = await project_store.load_project(project_id)
        if mode in {"selected", "from_node"} and not node_id:
            raise RunManagerError("node_id is required for this workflow mode.")
        if mode == "whole_graph":
            self._assert_no_active_whole_graph_job(project_id)

        plan = build_workflow_plan(project=project, mode=mode, node_id=node_id)
        if plan.get("errors"):
            raise RunManagerError({"ok": False, "errors": plan["errors"], "warnings": plan.get("warnings", [])})
        cost_errors = blocked_cost_errors(plan)
        if cost_errors:
            raise RunManagerError({"ok": False, "errors": cost_errors, "warnings": plan.get("warnings", [])})

        _graph, node_ids, warnings, errors = build_execution_plan(project=project, mode=mode, node_id=node_id)
        if errors:
            raise RunManagerError({"ok": False, "errors": errors, "warnings": warnings})
        if not node_ids:
            raise RunManagerError("No runnable WaveSpeed nodes were selected. Utility nodes are local-only and only feed connected model nodes.")
        for planned_node_id in node_ids:
            node = find_node(project, planned_node_id)
            if node:
                node.status = NodeStatus.queued
                node.error_message = None
        await project_store.save_project(project)

        kind_by_mode = {
            "selected": "workflow_selected",
            "from_node": "workflow_from_node",
            "whole_graph": "workflow_whole_graph",
        }
        job = RunJob(
            project_id=project_id,
            kind=kind_by_mode[mode],
            node_id=node_id,
            mode=mode,
            request={"project_id": project_id, "mode": mode, "node_id": node_id},
            plan=plan,
            progress_total=len(node_ids),
            node_ids=node_ids,
            warnings=warnings or plan.get("warnings", []),
        )
        await self._enqueue(job)
        return job

    async def cancel_job(self, job_id: str) -> RunJob:
        job = await self.get_job(job_id)
        if job.status in TERMINAL_STATUSES:
            raise RunManagerError("Cannot cancel a terminal job.")
        if job.status == "queued":
            job.status = "cancelled"
            job.cancelled_at = utc_now()
            job.finished_at = job.cancelled_at
            job.errors.append({"code": "job_cancelled", "message": "Queued job cancelled.", "details": {}})
            await self._write_project_run_history(job)
            return job
        job.status = "cancel_requested"
        job.cancelled_at = utc_now()
        job.warnings.append(
            {
                "code": "cancel_requested",
                "message": "Cancel requested. The active WaveSpeed call may finish before the job stops.",
                "details": {},
            }
        )
        return job

    async def retry_job(self, job_id: str) -> RunJob:
        job = await self.get_job(job_id)
        if job.status not in {"error", "cancelled"}:
            raise RunManagerError("Only failed or cancelled jobs can be retried.")
        if job.kind == "single_node":
            return await self.queue_node_run(
                project_id=job.project_id,
                node_id=job.node_id or job.request.get("node_id"),
                save_to_project=bool(job.request.get("save_to_project", True)),
            )
        return await self.queue_workflow_run(
            project_id=job.project_id,
            mode=job.mode or job.request.get("mode") or "whole_graph",
            node_id=job.node_id or job.request.get("node_id"),
        )

    async def clear_completed(self) -> dict[str, int]:
        completed_ids = [job_id for job_id, job in self.jobs.items() if job.status in TERMINAL_STATUSES]
        for job_id in completed_ids:
            self.jobs.pop(job_id, None)
        return {"ok": True, "cleared": len(completed_ids)}

    async def _enqueue(self, job: RunJob) -> None:
        async with self._lock:
            self.jobs[job.id] = job
            await self.queue.put(job.id)

    async def _worker(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                job = self.jobs.get(job_id)
                if job is None or job.status != "queued":
                    continue
                await self._execute_job(job)
            finally:
                self.queue.task_done()

    async def _execute_job(self, job: RunJob) -> None:
        job.status = "running"
        job.started_at = utc_now()
        try:
            if job.kind == "single_node":
                await self._execute_node_job(job)
            else:
                await self._execute_workflow_job(job)
            if job.status == "cancel_requested":
                job.status = "cancelled"
                job.finished_at = utc_now()
                job.cancelled_at = job.cancelled_at or job.finished_at
            elif job.status not in TERMINAL_STATUSES:
                job.status = "success"
                job.finished_at = utc_now()
        except Exception as exc:
            job.status = "error"
            job.finished_at = utc_now()
            job.errors.append({"code": "job_failed", "message": str(exc), "details": {"current_node_id": job.current_node_id}})
            await self._mark_current_node_error(job, str(exc))
        finally:
            job.current_node_id = None
            await self._write_project_run_history(job)

    async def _execute_node_job(self, job: RunJob) -> None:
        project = await project_store.load_project(job.project_id)
        node = find_node(project, job.node_id or "")
        if node is None:
            raise RunManagerError("Node not found in project")
        graph = build_graph(project)
        prompt_errors = validate_prompt_card_inputs(node, graph)
        if prompt_errors:
            raise RunManagerError(prompt_errors[0]["message"])
        resolved_inputs, input_errors = resolve_inputs_for_node(node, graph, project)
        if input_errors:
            job.errors.extend(input_errors)
            raise RunManagerError(input_errors[0]["message"])
        job.current_node_id = node.id
        await self._execute_single_node(project, node, job, resolved_inputs=resolved_inputs)
        job.progress_current = 1
        await project_store.save_project(project)

    async def _execute_workflow_job(self, job: RunJob) -> None:
        project = await project_store.load_project(job.project_id)
        graph, node_ids, warnings, errors = build_execution_plan(project=project, mode=job.mode or "whole_graph", node_id=job.node_id)
        if errors:
            job.errors.extend(errors)
            raise RunManagerError("Workflow plan has errors.")
        job.node_ids = node_ids
        job.progress_total = len(node_ids)
        job.warnings = merge_messages(job.warnings, warnings)
        for node_id in node_ids:
            if job.status == "cancel_requested":
                mark_remaining_nodes_skipped(project, node_ids[node_ids.index(node_id) :])
                await project_store.save_project(project)
                return
            node = graph.node_index[node_id]
            job.current_node_id = node.id
            prompt_errors = validate_prompt_card_inputs(node, graph)
            if prompt_errors:
                job.errors.extend(prompt_errors)
                raise RunManagerError(prompt_errors[0]["message"])
            resolved_inputs, input_errors = resolve_inputs_for_node(node, graph, project)
            if input_errors:
                job.errors.extend(input_errors)
                raise RunManagerError(input_errors[0]["message"])
            await self._execute_single_node(project, node, job, resolved_inputs=resolved_inputs)
            job.progress_current += 1
            await project_store.save_project(project)

    async def _execute_single_node(
        self,
        project: Project,
        node: CanvasNode,
        job: RunJob,
        resolved_inputs: dict[str, Any] | None = None,
    ) -> None:
        resolution = resolve_model_for_node(
            node_type=node.type,
            node_model_id=node.model_id,
            project_model_overrides=project.settings.model_overrides,
        )
        if resolution.error:
            raise RunManagerError(resolution.error)
        if not resolution.model or not resolution.model.enabled or not resolution.model_id:
            raise RunManagerError("Node is not backed by an enabled model.")
        guard = evaluate_cost_guard(resolution.model.estimated_base_cost_usd, project.settings.cost_guard)
        if guard["blocked"]:
            raise RunManagerError(guard["cost_guard_message"] or "Run blocked by local estimated cost guard.")

        node.estimated_base_cost_usd = resolution.model.estimated_base_cost_usd
        node_runner.mark_node_running(node)
        await project_store.save_project(project)
        raw_output, output_urls, output_assets = await node_runner.run_wavespeed_node(
            adapter=WaveSpeedAdapter(get_settings()),
            model_id=resolution.model_id,
            node_type=node.type,
            inputs=resolved_inputs if resolved_inputs is not None else dict(node.inputs or {}),
            project=project,
            target_node=node,
        )
        node_asset_ids: list[str] = []
        for asset in output_assets:
            asset.lineage.source_project_id = project.id
            asset.lineage.source_job_id = job.id
            asset.lineage.source_run_id = job.id
            asset.lineage.source_node_id = node.id
            asset.lineage.source_model_id = resolution.model_id
            asset.lineage.source_input_keys = dict(resolved_inputs if resolved_inputs is not None else node.inputs or {})
            asset.lineage.source_artifact_ids = collect_source_artifact_ids(project, asset.lineage.source_input_keys)
            project.assets.append(asset)
            job.asset_ids.append(asset.id)
            node_asset_ids.append(asset.id)
        job.output_urls.extend(output_urls)
        job.request["model_id"] = resolution.model_id
        job.request["model_display_name"] = resolution.model.label
        job.request["estimated_cost_snapshot"] = resolution.model.estimated_base_cost_usd
        job.request["input_snapshot"] = dict(node.inputs or {})
        job.request["resolved_input_snapshot"] = dict(resolved_inputs if resolved_inputs is not None else node.inputs or {})
        job.request["raw_output_summary"] = summarize_raw_output(raw_output, output_urls)
        node_runner.mark_node_success(node, resolution.model_id, raw_output, output_urls, node_asset_ids)

    async def _mark_current_node_error(self, job: RunJob, message: str) -> None:
        if not job.current_node_id:
            return
        try:
            project = await project_store.load_project(job.project_id)
        except project_store.ProjectStoreError:
            return
        node = find_node(project, job.current_node_id)
        if node:
            node_runner.mark_node_error(node, message)
            await project_store.save_project(project)

    async def _write_project_run_history(self, job: RunJob) -> None:
        try:
            project = await project_store.load_project(job.project_id)
        except project_store.ProjectStoreError:
            return
        if job.request.get("variant_set_id"):
            try:
                from app.services.variant_runner import attach_variant_result

                attach_variant_result(project, str(job.request["variant_set_id"]), job.id, job.asset_ids)
            except Exception:
                pass
        if job.request.get("comparison_id"):
            try:
                from app.services.model_compare import attach_comparison_result

                attach_comparison_result(project, str(job.request["comparison_id"]), job.id, job.asset_ids)
            except Exception:
                pass

        run = {
            "id": job.id,
            "job_id": job.id,
            "project_id": job.project_id,
            "type": job.kind,
            "status": job.status,
            "node_id": job.node_id,
            "run_id": job.id,
            "model_id": job.request.get("model_id"),
            "model_display_name": job.request.get("model_display_name"),
            "model_version": job.request.get("model_version"),
            "input_snapshot": job.request.get("input_snapshot") or job.request,
            "resolved_input_snapshot": job.request.get("resolved_input_snapshot") or {},
            "output_artifact_ids": job.asset_ids,
            "raw_output_summary": job.request.get("raw_output_summary") or {"output_url_count": len(job.output_urls)},
            "estimated_cost_snapshot": job.request.get("estimated_cost_snapshot"),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "cancelled_at": job.cancelled_at.isoformat() if job.cancelled_at else None,
            "node_ids": job.node_ids,
            "asset_ids": job.asset_ids,
            "output_urls": job.output_urls,
            "warnings": job.warnings,
            "errors": job.errors,
            "progress_current": job.progress_current,
            "progress_total": job.progress_total,
        }
        existing = [item for item in project.runs or [] if item.get("job_id") != job.id and item.get("id") != job.id]
        project.runs = [run, *existing][:100]
        await project_store.save_project(project)

    def _assert_no_active_node_job(self, project_id: str, node_id: str) -> None:
        for job in self.jobs.values():
            if job.project_id == project_id and node_id in job.node_ids and job.status in ACTIVE_STATUSES:
                raise RunManagerError("This node already has an active queued or running job.")

    def _assert_no_active_whole_graph_job(self, project_id: str) -> None:
        for job in self.jobs.values():
            if job.project_id == project_id and job.kind == "workflow_whole_graph" and job.status in ACTIVE_STATUSES:
                raise RunManagerError("This project already has an active whole-graph job.")


def blocked_cost_errors(plan: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    workflow_guard = plan.get("cost_guard") or {}
    if workflow_guard.get("blocked"):
        errors.append(
            {
                "code": "workflow_cost_guard_blocked",
                "message": workflow_guard.get("message") or "Workflow blocked by local estimated cost guard.",
                "details": {"estimated_total_cost_usd": plan.get("estimated_total_cost_usd"), "limit_usd": workflow_guard.get("limit_usd")},
            }
        )
    for step in plan.get("steps", []):
        guard = step.get("cost_guard") or {}
        if guard.get("blocked"):
            errors.append(
                {
                    "code": "step_cost_guard_blocked",
                    "message": guard.get("message") or "Step blocked by local estimated cost guard.",
                    "details": {"node_id": step.get("node_id"), "limit_usd": guard.get("limit_usd")},
                }
            )
    return errors


def find_node(project: Project, node_id: str) -> CanvasNode | None:
    return next((node for node in project.nodes if node.id == node_id), None)


def mark_remaining_nodes_skipped(project: Project, node_ids: list[str]) -> None:
    for node_id in node_ids:
        node = find_node(project, node_id)
        if node and node.status in {NodeStatus.queued, NodeStatus.idle}:
            node.status = NodeStatus.skipped
            node.error_message = "Skipped because the job was cancelled."


def merge_messages(first: list[dict[str, Any]], second: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    merged: list[dict[str, Any]] = []
    for item in [*first, *second]:
        key = (item.get("code"), item.get("message"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


run_manager = LocalRunManager()


def collect_source_artifact_ids(project: Project, inputs: dict[str, Any]) -> list[str]:
    known_ids = {asset.id for asset in project.assets}
    found: list[str] = []
    for value in inputs.values():
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate in known_ids and candidate not in found:
                found.append(candidate)
    return found


def summarize_raw_output(raw_output: dict[str, Any], output_urls: list[str]) -> dict[str, Any]:
    return {
        "keys": sorted(raw_output.keys())[:20] if isinstance(raw_output, dict) else [],
        "output_url_count": len(output_urls),
        "has_text": bool(raw_output.get("text")) if isinstance(raw_output, dict) else False,
        "has_json": bool(raw_output.get("json")) if isinstance(raw_output, dict) else False,
    }
