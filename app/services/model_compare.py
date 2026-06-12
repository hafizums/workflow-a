from __future__ import annotations

from app.schemas import CanvasEdge, ComparisonSet, ModelCompareRequest, Project, new_id, utc_now
from app.services import project_store
from app.services.registry import MODELS, get_model_for_node, resolve_model_for_node
from app.services.run_manager import RunManagerError, run_manager
from app.services.tool_compatibility import can_compare_models, compatible_models_for_node


class CompareError(ValueError):
    pass


async def queue_model_comparison(project: Project, request: ModelCompareRequest) -> ComparisonSet:
    source_node = next((node for node in project.nodes if node.id == request.source_node_id), None)
    if source_node is None:
        raise CompareError("Node not found in project")

    if request.model_ids:
        models = []
        for model_id in request.model_ids:
            model = get_model_for_node(source_node.type, model_id)
            if model is None or not model.enabled:
                raise CompareError(f"Model {model_id} is not an enabled model for {source_node.type.value}.")
            models.append(model)
    else:
        models = compatible_models_for_node(source_node, MODELS)

    ok, message = can_compare_models(models)
    if not ok:
        raise CompareError(message)

    comparison = ComparisonSet(
        project_id=project.id,
        source_node_id=source_node.id,
        label=request.label,
        model_ids=[model.default_model_id or model.id for model in models],
        status="queued",
    )
    project.comparison_sets.insert(0, comparison)

    for index, model in enumerate(models):
        clone = source_node.model_copy(deep=True)
        clone.id = f"{source_node.id}_cmp_{index + 1}_{comparison.id[-4:]}"
        clone.title = f"{source_node.title} Compare {index + 1}"
        clone.model_id = model.default_model_id or model.id
        clone.output_asset_ids = []
        clone.output_urls = []
        clone.last_run = {"comparison_id": comparison.id, "model_id": clone.model_id}
        clone.x = source_node.x + 340
        clone.y = source_node.y + index * 80
        project.nodes.append(clone)
        project.edges.extend(cloned_incoming_edges(project, source_node.id, clone.id))

    await project_store.save_project(project)
    for clone in project.nodes[-len(models) :]:
        resolution = resolve_model_for_node(clone.type, clone.model_id, project.settings.model_overrides)
        if resolution.error:
            comparison.errors.append({"node_id": clone.id, "message": resolution.error})
            continue
        try:
            job = await run_manager.queue_node_run(
                project.id,
                clone.id,
                save_to_project=request.save_to_project,
                request_metadata={"comparison_id": comparison.id},
            )
            comparison.job_ids.append(job.id)
        except RunManagerError as exc:
            comparison.errors.append({"node_id": clone.id, "message": str(exc)})
    await project_store.save_project(project)
    return comparison


def cloned_incoming_edges(project: Project, source_node_id: str, clone_node_id: str) -> list[CanvasEdge]:
    edges: list[CanvasEdge] = []
    for edge in project.edges or []:
        target_id = edge.target_node_id or edge.target or edge.targetNodeId or edge.to
        if target_id != source_node_id:
            continue
        clone_edge = edge.model_copy(deep=True)
        clone_edge.id = new_id("edge")
        clone_edge.target_node_id = clone_node_id
        clone_edge.target = None
        clone_edge.targetNodeId = None
        clone_edge.to = None
        edges.append(clone_edge)
    return edges


def attach_comparison_result(project: Project, comparison_id: str, job_id: str, artifact_ids: list[str]) -> None:
    comparison = next((item for item in project.comparison_sets if item.id == comparison_id), None)
    if comparison is None:
        return
    if job_id not in comparison.job_ids:
        comparison.job_ids.append(job_id)
    for asset_id in artifact_ids:
        if asset_id not in comparison.artifact_ids:
            comparison.artifact_ids.append(asset_id)
    comparison.status = "success" if artifact_ids else comparison.status
    comparison.updated_at = utc_now()
