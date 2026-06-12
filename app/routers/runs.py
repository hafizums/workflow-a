from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.schemas import EstimateRunRequest, EstimateRunResponse, RunNodeRequest, RunNodeResponse
from app.schemas import new_id
from app.services import node_runner
from app.services import project_store
from app.services.cost_estimator import evaluate_cost_guard, get_estimated_base_cost
from app.services.registry import resolve_model_for_node
from app.services.wavespeed_adapter import WaveSpeedAdapter
from app.services.workflow_resolver import build_graph, resolve_inputs_for_node, validate_prompt_card_inputs

router = APIRouter(prefix="/api/runs", tags=["runs"])


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


@router.post("/estimate", response_model=EstimateRunResponse)
async def estimate_run(payload: EstimateRunRequest):
    project = None
    target_node = None
    if payload.project_id:
        try:
            project = await project_store.load_project(payload.project_id)
        except project_store.ProjectStoreError as exc:
            raise project_error(exc) from exc
        if payload.node_id:
            target_node = next((node for node in project.nodes if node.id == payload.node_id), None)
            if target_node is None:
                raise HTTPException(status_code=404, detail="Node not found in project")

    node_type = target_node.type if target_node else payload.node_type
    node_model_id = target_node.model_id if target_node and target_node.model_id else payload.model_id
    model_overrides = project.settings.model_overrides if project else {}
    cost_guard = project.settings.cost_guard if project else None
    estimate = get_estimated_base_cost(
        node_type=node_type,
        model_id=node_model_id,
        project_model_overrides=model_overrides,
        cost_guard=cost_guard,
    )
    if not estimate["ok"]:
        raise HTTPException(status_code=400, detail=estimate["error"])
    return EstimateRunResponse(**estimate)


@router.post("/node", response_model=RunNodeResponse)
async def run_node(payload: RunNodeRequest):
    settings = get_settings()
    adapter = WaveSpeedAdapter(settings)

    project = None
    target_node = None
    if payload.project_id and payload.save_to_project:
        try:
            project = await project_store.load_project(payload.project_id)
        except project_store.ProjectStoreError as exc:
            raise project_error(exc) from exc
        if payload.node_id:
            target_node = next((node for node in project.nodes if node.id == payload.node_id), None)
            if target_node is None:
                raise HTTPException(status_code=404, detail="Node not found in project")
            graph = build_graph(project)
            prompt_errors = validate_prompt_card_inputs(target_node, graph)
            if prompt_errors:
                raise HTTPException(status_code=400, detail=prompt_errors[0]["message"])
            resolved_inputs, input_errors = resolve_inputs_for_node(target_node, graph, project)
            if input_errors:
                raise HTTPException(status_code=400, detail=input_errors[0]["message"])
            payload.inputs = resolved_inputs
            node_runner.mark_node_running(target_node)
            await project_store.save_project(project)

    node_type = target_node.type if target_node else payload.node_type
    node_model_id = target_node.model_id if target_node and target_node.model_id else payload.model_id
    model_overrides = project.settings.model_overrides if project else {}
    resolution = resolve_model_for_node(
        node_type=node_type,
        node_model_id=node_model_id,
        project_model_overrides=model_overrides,
    )
    if resolution.error:
        if project and target_node:
            node_runner.mark_node_error(target_node, resolution.error)
            await project_store.save_project(project)
        raise HTTPException(status_code=400, detail=resolution.error)
    if resolution.model is None or resolution.model_id is None:
        message = f"No model could be resolved for node type {node_type.value}."
        if project and target_node:
            node_runner.mark_node_error(target_node, message)
            await project_store.save_project(project)
        raise HTTPException(status_code=400, detail=message)
    if not resolution.model.enabled:
        message = resolution.model.enabled_reason or f"Model is disabled in the registry: {resolution.model_id}"
        if project and target_node:
            node_runner.mark_node_error(target_node, message)
            await project_store.save_project(project)
        raise HTTPException(status_code=400, detail=message)

    if target_node:
        target_node.estimated_base_cost_usd = resolution.model.estimated_base_cost_usd

    guard = evaluate_cost_guard(
        resolution.model.estimated_base_cost_usd,
        project.settings.cost_guard if project else None,
    )
    if guard["blocked"]:
        message = guard["cost_guard_message"] or "Run blocked by local estimated cost guard."
        if project and target_node:
            node_runner.mark_node_error(target_node, message)
            await project_store.save_project(project)
        raise HTTPException(status_code=400, detail=message)

    try:
        raw_output, output_urls, output_assets = await node_runner.run_wavespeed_node(
            adapter=adapter,
            model_id=resolution.model_id,
            node_type=node_type,
            inputs=payload.inputs,
            project=project,
            target_node=target_node,
        )
    except Exception as exc:
        if project and target_node:
            node_runner.mark_node_error(target_node, str(exc))
            await project_store.save_project(project)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    asset_ids: list[str] = []
    if project:
        run_id = new_id("run")
        for asset in output_assets:
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
            node_runner.mark_node_success(target_node, resolution.model_id, raw_output, output_urls, asset_ids)
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
                "input_snapshot": dict(payload.inputs or {}),
                "resolved_input_snapshot": dict(payload.inputs or {}),
                "output_artifact_ids": asset_ids,
                "asset_ids": asset_ids,
                "output_urls": output_urls,
                "raw_output_summary": {"output_url_count": len(output_urls), "keys": sorted(raw_output.keys())[:20]},
                "estimated_cost_snapshot": resolution.model.estimated_base_cost_usd if resolution.model else None,
                "errors": [],
                "warnings": [],
            },
            *(project.runs or []),
        ][:100]
        await project_store.save_project(project)

    return RunNodeResponse(
        ok=True,
        model_id=resolution.model_id,
        node_id=payload.node_id,
        raw_output=raw_output,
        output_urls=output_urls,
        asset_ids=asset_ids,
    )
