from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas import NodeStatus, Project, new_id
from app.services import node_runner
from app.services import project_store
from app.services.cost_estimator import evaluate_cost_guard
from app.services.registry import resolve_model_for_node
from app.services.wavespeed_adapter import WaveSpeedAdapter
from app.services.workflow_resolver import build_execution_plan, build_workflow_plan, resolve_inputs_for_node

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class RunSelectedRequest(BaseModel):
    node_id: str


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


@router.get("/{project_id}/plan")
async def get_workflow_plan(project_id: str, mode: str = "whole_graph", node_id: str | None = None):
    try:
        project = await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc

    return build_workflow_plan(project=project, mode=mode, node_id=node_id)


@router.post("/{project_id}/run-selected")
async def run_selected_node(project_id: str, payload: RunSelectedRequest):
    project = await load_project_or_404(project_id)
    return await execute_workflow(project=project, run_type="single_node", mode="selected", node_id=payload.node_id)


@router.post("/{project_id}/run-from-node/{node_id}")
async def run_from_node(project_id: str, node_id: str):
    project = await load_project_or_404(project_id)
    return await execute_workflow(project=project, run_type="from_node", mode="from_node", node_id=node_id)


@router.post("/{project_id}/run-all")
async def run_all(project_id: str):
    project = await load_project_or_404(project_id)
    return await execute_workflow(project=project, run_type="whole_graph", mode="whole_graph")


@router.get("/{project_id}/runs")
async def list_workflow_runs(project_id: str):
    project = await load_project_or_404(project_id)
    return project.runs or []


async def load_project_or_404(project_id: str) -> Project:
    try:
        return await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc


async def execute_workflow(project: Project, run_type: str, mode: str, node_id: str | None = None) -> dict[str, Any]:
    plan = build_workflow_plan(project=project, mode=mode, node_id=node_id)
    if plan["errors"]:
        raise HTTPException(
            status_code=400,
            detail={"ok": False, "errors": plan["errors"], "warnings": plan["warnings"]},
        )

    cost_errors = blocked_cost_errors(plan)
    if cost_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "errors": cost_errors,
                "warnings": plan["warnings"],
                "cost_guard": plan["cost_guard"],
                "estimated_total_cost_usd": plan["estimated_total_cost_usd"],
            },
        )

    graph, node_ids, warnings, errors = build_execution_plan(project=project, mode=mode, node_id=node_id)
    if errors:
        raise HTTPException(status_code=400, detail={"ok": False, "errors": errors, "warnings": warnings})

    run = create_run(run_type, node_ids, warnings)
    append_run(project, run)
    queue_or_skip_nodes(project, node_ids, warnings)
    await project_store.save_project(project)

    adapter = WaveSpeedAdapter(get_settings())
    asset_ids: list[str] = []
    output_urls: list[str] = []

    for current_node_id in node_ids:
        node = graph.node_index[current_node_id]
        resolution = resolve_model_for_node(
            node_type=node.type,
            node_model_id=node.model_id,
            project_model_overrides=project.settings.model_overrides,
        )
        if resolution.error:
            node_runner.mark_node_error(node, resolution.error)
            run["status"] = "error"
            run["finished_at"] = utc_iso()
            run["errors"].append(
                {
                    "code": "model_resolution_failed",
                    "message": resolution.error,
                    "details": {
                        "node_id": node.id,
                        "model_id": resolution.model_id,
                        "model_source": resolution.source,
                    },
                }
            )
            await project_store.save_project(project)
            return workflow_run_response(False, project, run)
        if not resolution.model or not resolution.model.enabled or not resolution.model_id:
            node.status = NodeStatus.skipped
            node.error_message = (
                resolution.model.enabled_reason
                if resolution.model
                else "Skipped because this node is not backed by an enabled model."
            )
            continue
        node.estimated_base_cost_usd = resolution.model.estimated_base_cost_usd
        guard = evaluate_cost_guard(resolution.model.estimated_base_cost_usd, project.settings.cost_guard)
        if guard["blocked"]:
            message = guard["cost_guard_message"] or "Run blocked by local estimated cost guard."
            node_runner.mark_node_error(node, message)
            run["status"] = "error"
            run["finished_at"] = utc_iso()
            run["errors"].append(
                {
                    "code": "cost_guard_blocked",
                    "message": message,
                    "details": {"node_id": node.id, "model_id": resolution.model_id},
                }
            )
            await project_store.save_project(project)
            return workflow_run_response(False, project, run)

        resolved_inputs, input_errors = resolve_inputs_for_node(node, graph, project)
        if input_errors:
            message = input_errors[0]["message"]
            node_runner.mark_node_error(node, message)
            run["status"] = "error"
            run["finished_at"] = utc_iso()
            run["errors"].extend(input_errors)
            await project_store.save_project(project)
            return workflow_run_response(False, project, run)

        try:
            node_runner.mark_node_running(node)
            await project_store.save_project(project)
            raw_output, node_output_urls, node_output_assets = await node_runner.run_wavespeed_node(
                adapter=adapter,
                model_id=resolution.model_id,
                node_type=node.type,
                inputs=resolved_inputs,
                project=project,
                target_node=node,
            )
        except Exception as exc:
            node_runner.mark_node_error(node, str(exc))
            run["status"] = "error"
            run["finished_at"] = utc_iso()
            run["errors"].append(
                {
                    "code": "node_execution_failed",
                    "message": str(exc),
                    "details": {"node_id": node.id, "model_id": resolution.model_id, "model_source": resolution.source},
                }
            )
            await project_store.save_project(project)
            return workflow_run_response(False, project, run)

        node_asset_ids: list[str] = []
        for asset in node_output_assets:
            project.assets.append(asset)
            asset_ids.append(asset.id)
            node_asset_ids.append(asset.id)
        output_urls.extend(node_output_urls)
        run["asset_ids"] = asset_ids
        run["output_urls"] = output_urls
        node_runner.mark_node_success(node, resolution.model_id, raw_output, node_output_urls, node_asset_ids)
        await project_store.save_project(project)

    run["status"] = "success"
    run["finished_at"] = utc_iso()
    run["asset_ids"] = asset_ids
    run["output_urls"] = output_urls
    await project_store.save_project(project)
    return workflow_run_response(True, project, run)


def blocked_cost_errors(plan: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    workflow_guard = plan.get("cost_guard") or {}
    if workflow_guard.get("blocked"):
        errors.append(
            {
                "code": "workflow_cost_guard_blocked",
                "message": workflow_guard.get("message") or "Workflow blocked by local estimated cost guard.",
                "details": {
                    "estimated_total_cost_usd": plan.get("estimated_total_cost_usd"),
                    "limit_usd": workflow_guard.get("limit_usd"),
                },
            }
        )

    for step in plan.get("steps", []):
        step_guard = step.get("cost_guard") or {}
        if step_guard.get("blocked"):
            errors.append(
                {
                    "code": "step_cost_guard_blocked",
                    "message": step_guard.get("message") or "Step blocked by local estimated cost guard.",
                    "details": {
                        "node_id": step.get("node_id"),
                        "model_id": step.get("effective_model_id") or step.get("model_id"),
                        "estimated_base_cost_usd": step.get("estimated_base_cost_usd"),
                        "limit_usd": step_guard.get("limit_usd"),
                    },
                }
            )
    return errors


def queue_or_skip_nodes(project: Project, node_ids: list[str], warnings: list[dict[str, Any]]) -> None:
    node_index = {node.id: node for node in project.nodes}
    for node_id in node_ids:
        node = node_index[node_id]
        resolution = resolve_model_for_node(
            node_type=node.type,
            node_model_id=node.model_id,
            project_model_overrides=project.settings.model_overrides,
        )
        if resolution.model and resolution.model.enabled and not resolution.error:
            node.status = NodeStatus.queued
            node.error_message = None
            node.estimated_base_cost_usd = resolution.model.estimated_base_cost_usd
            guard = evaluate_cost_guard(resolution.model.estimated_base_cost_usd, project.settings.cost_guard)
            if guard["blocked"]:
                node.status = NodeStatus.skipped
                node.error_message = guard["cost_guard_message"] or "Run blocked by local estimated cost guard."
                warnings.append(
                    {
                        "code": "cost_guard_blocked",
                        "message": node.error_message,
                        "details": {"node_id": node.id, "model_id": resolution.model_id},
                    }
                )
        else:
            node.status = NodeStatus.skipped
            node.error_message = (
                resolution.error
                or (resolution.model.enabled_reason if resolution.model else None)
                or "Skipped because this node is not backed by an enabled model."
            )
            warnings.append(
                {
                    "code": "node_skipped" if not resolution.error else "model_resolution_failed",
                    "message": node.error_message,
                    "details": {
                        "node_id": node.id,
                        "model_id": resolution.model_id,
                        "model_source": resolution.source,
                    },
                }
            )


def create_run(run_type: str, node_ids: list[str], warnings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": new_id("run"),
        "type": run_type,
        "status": "running",
        "started_at": utc_iso(),
        "finished_at": None,
        "node_ids": node_ids,
        "asset_ids": [],
        "output_urls": [],
        "errors": [],
        "warnings": warnings,
    }


def append_run(project: Project, run: dict[str, Any]) -> None:
    project.runs = [run, *(project.runs or [])][:50]


def workflow_run_response(ok: bool, project: Project, run: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": ok,
        "project_id": project.id,
        "run": run,
        "project": project.model_dump(mode="json"),
    }


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
