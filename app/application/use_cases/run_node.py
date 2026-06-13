from __future__ import annotations

from app.application.dto.node_run_context import NodeRunContext
from app.application.use_cases.errors import ApplicationError
from app.application.use_cases.node_executors import NodeExecutorRegistry
from app.core.config import get_settings
from app.domain.policies.cost_guard_policy import CostGuardPolicy
from app.domain.policies.model_support_policy import ModelSupportPolicy
from app.domain.policies.prompt_source_policy import PromptSourcePolicy
from app.infrastructure.gateways.wavespeed_gateway import WaveSpeedGateway
from app.infrastructure.repositories.json_project_repository import JsonProjectRepository
from app.schemas import EstimateRunRequest, EstimateRunResponse, NodeType, RunNodeRequest, RunNodeResponse, new_id
from app.services import node_runner, project_store
from app.services.cost_estimator import get_estimated_base_cost
from app.services.local_utility_runner import is_runnable_local_utility
from app.services.output_node_builder import sync_storyboard_panel_output_nodes
from app.services.utility_tools import get_utility_tool
from app.services.workflow_resolver import build_graph, resolve_inputs_for_node


class RunNodeUseCase:
    def __init__(
        self,
        *,
        projects: JsonProjectRepository | None = None,
        executor_registry: NodeExecutorRegistry | None = None,
        model_policy: ModelSupportPolicy | None = None,
        prompt_policy: PromptSourcePolicy | None = None,
        cost_policy: CostGuardPolicy | None = None,
    ):
        self.projects = projects or JsonProjectRepository()
        self.executor_registry = executor_registry or NodeExecutorRegistry()
        self.model_policy = model_policy or ModelSupportPolicy()
        self.prompt_policy = prompt_policy or PromptSourcePolicy()
        self.cost_policy = cost_policy or CostGuardPolicy()

    async def estimate(self, payload: EstimateRunRequest) -> EstimateRunResponse:
        project = None
        target_node = None
        if payload.project_id:
            try:
                project = await self.projects.load(payload.project_id)
            except project_store.ProjectStoreError as exc:
                raise self._project_error(exc) from exc
            if payload.node_id:
                target_node = next((node for node in project.nodes if node.id == payload.node_id), None)
                if target_node is None:
                    raise ApplicationError(404, "Node not found in project")

        node_type = target_node.type if target_node else payload.node_type
        node_model_id = target_node.model_id if target_node and target_node.model_id else payload.model_id
        if is_runnable_local_utility(node_type):
            utility = get_utility_tool(node_type)
            return EstimateRunResponse(
                ok=True,
                node_type=node_type,
                model_id=utility.id if utility else f"local/utility/{node_type.value}",
                model_source="utility",
                estimated_base_cost_usd=0.0,
                cost_unit="local",
                pricing_note="Runs locally; no AI model cost.",
                warning="Local utility run; no WaveSpeed call.",
                enabled=True,
                enabled_reason=utility.enabled_reason if utility else "Local utility node.",
                verification_status="local",
                requires_confirmation=False,
                blocked=False,
            )

        model_overrides = project.settings.model_overrides if project else {}
        cost_guard = project.settings.cost_guard if project else None
        estimate = get_estimated_base_cost(
            node_type=node_type,
            model_id=node_model_id,
            project_model_overrides=model_overrides,
            cost_guard=cost_guard,
        )
        if not estimate["ok"]:
            raise ApplicationError(400, estimate["error"])
        return EstimateRunResponse(**estimate)

    async def run(self, payload: RunNodeRequest) -> RunNodeResponse:
        adapter = WaveSpeedGateway(get_settings())

        project = None
        target_node = None
        if payload.project_id and payload.save_to_project:
            try:
                project = await self.projects.load(payload.project_id)
            except project_store.ProjectStoreError as exc:
                raise self._project_error(exc) from exc
            if payload.node_id:
                target_node = next((node for node in project.nodes if node.id == payload.node_id), None)
                if target_node is None:
                    raise ApplicationError(404, "Node not found in project")
                graph = build_graph(project)
                prompt_errors = self.prompt_policy.validate(target_node, graph)
                if prompt_errors:
                    raise ApplicationError(400, prompt_errors[0]["message"])
                resolved_inputs, input_errors = resolve_inputs_for_node(target_node, graph, project)
                if input_errors:
                    raise ApplicationError(400, input_errors[0]["message"])
                payload.inputs = resolved_inputs
                node_runner.mark_node_running(target_node)
                await self.projects.save(project)

        node_type = target_node.type if target_node else payload.node_type
        node_model_id = target_node.model_id if target_node and target_node.model_id else payload.model_id
        if is_runnable_local_utility(node_type):
            if project is None or target_node is None:
                raise ApplicationError(400, "Runnable utility nodes must be run from a saved project node.")
            return await self._run_saved_local_utility_node(project=project, target_node=target_node, payload=payload)

        model_overrides = project.settings.model_overrides if project else {}
        resolution = self.model_policy.resolve(
            node_type=node_type,
            node_model_id=node_model_id,
            project_model_overrides=model_overrides,
        )
        if resolution.error:
            await self._mark_project_node_error(project, target_node, resolution.error)
            raise ApplicationError(400, resolution.error)
        if resolution.model is None or resolution.model_id is None:
            message = f"No model could be resolved for node type {node_type.value}."
            await self._mark_project_node_error(project, target_node, message)
            raise ApplicationError(400, message)
        if not resolution.model.enabled:
            message = resolution.model.enabled_reason or f"Model is disabled in the registry: {resolution.model_id}"
            await self._mark_project_node_error(project, target_node, message)
            raise ApplicationError(400, message)

        if target_node:
            target_node.estimated_base_cost_usd = resolution.model.estimated_base_cost_usd

        guard = self.cost_policy.evaluate_run(
            resolution.model.estimated_base_cost_usd,
            project.settings.cost_guard if project else None,
        )
        if guard["blocked"]:
            message = guard["cost_guard_message"] or "Run blocked by local estimated cost guard."
            await self._mark_project_node_error(project, target_node, message)
            raise ApplicationError(400, message)

        try:
            run_result = await self.executor_registry.run(
                NodeRunContext(
                    project=project,
                    node=target_node,
                    node_type=node_type,
                    effective_model_id=resolution.model_id,
                    resolved_inputs=payload.inputs,
                    request_metadata={"adapter": adapter},
                )
            )
        except Exception as exc:
            await self._mark_project_node_error(project, target_node, str(exc))
            raise ApplicationError(400, str(exc)) from exc

        asset_ids: list[str] = []
        if project:
            run_id = new_id("run")
            for asset in run_result.output_assets:
                asset.lineage.source_project_id = project.id
                asset.lineage.source_node_id = target_node.id if target_node else payload.node_id
                asset.lineage.source_run_id = run_id
                asset.lineage.source_model_id = resolution.model_id
                asset.lineage.source_input_keys = dict(payload.inputs or {})
                asset.lineage.source_artifact_ids = [
                    value
                    for value in payload.inputs.values()
                    if isinstance(value, str) and any(existing.id == value for existing in project.assets)
                ]
                project.assets.append(asset)
                asset_ids.append(asset.id)

            if target_node:
                node_runner.mark_node_success(
                    target_node,
                    resolution.model_id,
                    run_result.raw_output,
                    run_result.output_urls,
                    asset_ids,
                )
            text_output = node_runner.extract_text_output(run_result.raw_output)
            structured_output = run_result.raw_output if not run_result.output_urls and not text_output else {}
            project.runs = [
                {
                    "id": run_id,
                    "run_id": run_id,
                    "project_id": project.id,
                    "type": "single_node",
                    "status": "success",
                    "node_id": target_node.id if target_node else payload.node_id,
                    "model_id": resolution.model_id,
                    "model_display_name": resolution.model.label if resolution.model else None,
                    "primary_capability": resolution.model.primary_capability if resolution.model else None,
                    "category": resolution.model.category if resolution.model else None,
                    "input_snapshot": dict(payload.inputs or {}),
                    "resolved_input_snapshot": dict(payload.inputs or {}),
                    "input_summary": {"keys": sorted((payload.inputs or {}).keys())},
                    "output_artifact_ids": asset_ids,
                    "asset_ids": asset_ids,
                    "output_urls": run_result.output_urls,
                    "raw_output": run_result.raw_output,
                    "text_output": text_output,
                    "structured_output": structured_output,
                    "raw_output_summary": {
                        "output_url_count": len(run_result.output_urls),
                        "keys": sorted(run_result.raw_output.keys())[:20],
                    },
                    "estimated_cost_snapshot": resolution.model.estimated_base_cost_usd if resolution.model else None,
                    "pricing_basis_guess": resolution.model.pricing_basis_guess if resolution.model else None,
                    "pricing_formula_raw": resolution.model.pricing_formula_raw if resolution.model else None,
                    "errors": [],
                    "warnings": [],
                },
                *(project.runs or []),
            ][:100]
            await self.projects.save(project)

        return RunNodeResponse(
            ok=True,
            model_id=resolution.model_id,
            node_id=payload.node_id,
            raw_output=run_result.raw_output,
            output_urls=run_result.output_urls,
            asset_ids=asset_ids,
        )

    async def _run_saved_local_utility_node(self, *, project, target_node, payload: RunNodeRequest) -> RunNodeResponse:
        utility = get_utility_tool(target_node.type)
        model_id = utility.id if utility else f"local/utility/{target_node.type.value}"
        try:
            run_result = await self.executor_registry.run(
                NodeRunContext(
                    project=project,
                    node=target_node,
                    node_type=target_node.type,
                    effective_model_id=model_id,
                    resolved_inputs=payload.inputs,
                )
            )
        except Exception as exc:
            node_runner.mark_node_error(target_node, str(exc))
            await self.projects.save(project)
            raise ApplicationError(400, str(exc)) from exc

        run_id = new_id("run")
        asset_ids: list[str] = []
        output_assets = list(run_result.output_assets)
        for asset in run_result.output_assets:
            asset.lineage.source_project_id = project.id
            asset.lineage.source_node_id = target_node.id
            asset.lineage.source_run_id = run_id
            asset.lineage.source_model_id = model_id
            asset.lineage.source_input_keys = dict(payload.inputs or {})
            if not asset.lineage.source_artifact_ids:
                asset.lineage.source_artifact_ids = [
                    value
                    for value in payload.inputs.values()
                    if isinstance(value, str) and any(existing.id == value for existing in project.assets)
                ]
            project.assets.append(asset)
            asset_ids.append(asset.id)

        created_output_node_ids: list[str] = []
        if target_node.type == NodeType.storyboard_panels:
            created_output_node_ids = sync_storyboard_panel_output_nodes(project, target_node, output_assets)

        target_node.estimated_base_cost_usd = 0.0
        node_runner.mark_node_success(target_node, model_id, run_result.raw_output, run_result.output_urls, asset_ids)
        if created_output_node_ids:
            target_node.last_run["output_node_ids"] = created_output_node_ids
        project.runs = [
            {
                "id": run_id,
                "run_id": run_id,
                "project_id": project.id,
                "type": "single_node",
                "status": "success",
                "node_id": target_node.id,
                "model_id": model_id,
                "model_display_name": utility.label if utility else target_node.title,
                "primary_capability": "local_utility",
                "category": "utility",
                "input_snapshot": dict(target_node.inputs or {}),
                "resolved_input_snapshot": dict(payload.inputs or {}),
                "input_summary": {"keys": sorted((payload.inputs or {}).keys())},
                "output_artifact_ids": asset_ids,
                "asset_ids": asset_ids,
                "output_urls": run_result.output_urls,
                "raw_output": run_result.raw_output,
                "text_output": None,
                "structured_output": {},
                "raw_output_summary": {
                    "output_url_count": len(run_result.output_urls),
                    "keys": sorted(run_result.raw_output.keys())[:20],
                },
                "estimated_cost_snapshot": 0.0,
                "pricing_basis_guess": None,
                "pricing_formula_raw": None,
                "errors": [],
                "warnings": [],
            },
            *(project.runs or []),
        ][:100]
        await self.projects.save(project)

        return RunNodeResponse(
            ok=True,
            model_id=model_id,
            node_id=payload.node_id,
            raw_output=run_result.raw_output,
            output_urls=run_result.output_urls,
            asset_ids=asset_ids,
        )

    async def _mark_project_node_error(self, project, target_node, message: str) -> None:
        if project and target_node:
            node_runner.mark_node_error(target_node, message)
            await self.projects.save(project)

    @staticmethod
    def _project_error(exc: project_store.ProjectStoreError) -> ApplicationError:
        if isinstance(exc, project_store.InvalidProjectIdError):
            return ApplicationError(400, str(exc))
        if isinstance(exc, project_store.ProjectNotFoundError):
            return ApplicationError(404, str(exc))
        if isinstance(exc, project_store.ProjectStorageSchemaError):
            return ApplicationError(500, str(exc))
        return ApplicationError(500, "Project storage error")
