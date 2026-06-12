from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas import CanvasEdge, CanvasNode, Project, VariantParameter, VariantRunRequest, VariantSet, new_id, utc_now
from app.services import project_store
from app.services.cost_estimator import evaluate_workflow_cost_guard
from app.services.registry import resolve_model_for_node
from app.services.run_manager import RunManagerError, run_manager


class VariantError(ValueError):
    pass


def build_variant_payloads(node: CanvasNode, request: VariantRunRequest) -> list[dict[str, Any]]:
    base_inputs = dict(node.inputs or {})
    count = max(1, min(int(request.variant_count or 1), 16))
    payloads = [deepcopy(base_inputs) for _ in range(count)]
    parameters = request.parameters or [VariantParameter(field="seed", strategy="seed", values=[])]

    for parameter in parameters:
        if parameter.strategy == "seed":
            start = int(parameter.values[0]) if parameter.values else 1
            for index, payload in enumerate(payloads):
                payload[parameter.field] = start + index
        elif parameter.strategy == "prompt_suffix":
            values = parameter.values or [f"variation {index + 1}" for index in range(count)]
            for index, payload in enumerate(payloads):
                suffix = str(values[index % len(values)])
                current = str(payload.get(parameter.field) or payload.get("prompt") or "")
                payload[parameter.field] = f"{current} {suffix}".strip()
        elif parameter.strategy == "prompt_template":
            values = parameter.values or [{}]
            template = str(base_inputs.get(parameter.field) or base_inputs.get("prompt") or "")
            for index, payload in enumerate(payloads):
                value = values[index % len(values)]
                if isinstance(value, dict):
                    payload[parameter.field] = template.format(**value)
        elif parameter.strategy == "range":
            values = parameter.values
            if len(values) < 2:
                raise VariantError("Range strategy requires at least start and end values.")
            start, end = float(values[0]), float(values[1])
            step = (end - start) / max(1, count - 1)
            for index, payload in enumerate(payloads):
                payload[parameter.field] = round(start + index * step, 6)
        else:
            values = parameter.values or [base_inputs.get(parameter.field)]
            for index, payload in enumerate(payloads):
                payload[parameter.field] = values[index % len(values)]
    return payloads


async def queue_variant_set(project: Project, request: VariantRunRequest) -> VariantSet:
    source_node = next((node for node in project.nodes if node.id == request.node_id), None)
    if source_node is None:
        raise VariantError("Node not found in project")
    resolution = resolve_model_for_node(
        source_node.type,
        node_model_id=source_node.model_id,
        project_model_overrides=project.settings.model_overrides,
    )
    if resolution.error or not resolution.model or not resolution.model.enabled:
        raise VariantError(resolution.error or "Node is not backed by an enabled model.")

    payloads = build_variant_payloads(source_node, request)
    total_cost = None
    if resolution.model.estimated_base_cost_usd is not None:
        total_cost = resolution.model.estimated_base_cost_usd * len(payloads)
    guard = evaluate_workflow_cost_guard(
        estimated_total_cost_usd=total_cost,
        has_unknown_cost=total_cost is None,
        cost_guard=project.settings.cost_guard,
    )
    if guard["blocked"]:
        raise VariantError(guard["message"] or "Variant set blocked by local estimated cost guard.")

    variant_set = VariantSet(
        project_id=project.id,
        source_node_id=source_node.id,
        label=request.label,
        parameters=request.parameters,
        status="queued",
    )
    project.variant_sets.insert(0, variant_set)

    for index, inputs in enumerate(payloads):
        clone = source_node.model_copy(deep=True)
        clone.id = f"{source_node.id}_var_{index + 1}_{variant_set.id[-4:]}"
        clone.title = f"{source_node.title} Variant {index + 1}"
        clone.inputs = inputs
        clone.output_asset_ids = []
        clone.output_urls = []
        clone.last_run = {"variant_set_id": variant_set.id, "variant_index": index}
        clone.x = source_node.x + 340
        clone.y = source_node.y + index * 80
        clone.status = "idle"
        clone.created_at = utc_now()
        clone.updated_at = utc_now()
        project.nodes.append(clone)
        extra_nodes, extra_edges = cloned_incoming_prompt_edges(project, source_node, clone, inputs)
        project.nodes.extend(extra_nodes)
        project.edges.extend(extra_edges)

    await project_store.save_project(project)
    for clone in project.nodes[-len(payloads) :]:
        try:
            job = await run_manager.queue_node_run(
                project.id,
                clone.id,
                save_to_project=request.save_to_project,
                request_metadata={"variant_set_id": variant_set.id},
            )
            variant_set.job_ids.append(job.id)
        except RunManagerError as exc:
            variant_set.errors.append({"node_id": clone.id, "message": str(exc)})
    await project_store.save_project(project)
    return variant_set


def cloned_incoming_prompt_edges(
    project: Project,
    source_node: CanvasNode,
    clone_node: CanvasNode,
    inputs: dict[str, Any],
) -> tuple[list[CanvasNode], list[CanvasEdge]]:
    extra_nodes: list[CanvasNode] = []
    edges: list[CanvasEdge] = []
    for edge in project.edges or []:
        target_id = edge.target_node_id or edge.target or edge.targetNodeId or edge.to
        if target_id != source_node.id:
            continue
        source_id = edge.source_node_id or edge.source or edge.sourceNodeId or edge.from_node
        source = next((node for node in project.nodes if node.id == source_id), None)
        target_input = edge.target_input or edge.target_handle
        clone_edge = edge.model_copy(deep=True)
        clone_edge.id = new_id("edge")
        clone_edge.target_node_id = clone_node.id
        clone_edge.target = None
        clone_edge.targetNodeId = None
        clone_edge.to = None
        if source and source.type.value == "prompt_card" and target_input in {"prompt", "text"} and inputs.get(target_input):
            prompt_clone = source.model_copy(deep=True)
            prompt_clone.id = f"{source.id}_var_{clone_node.id[-6:]}"
            prompt_clone.title = f"{source.title} Variant"
            prompt_clone.inputs = {**prompt_clone.inputs, "text": inputs[target_input]}
            prompt_clone.x = clone_node.x - 340
            prompt_clone.y = clone_node.y
            prompt_clone.output_asset_ids = []
            prompt_clone.output_urls = []
            prompt_clone.last_run = {"variant_parent_prompt_card_id": source.id}
            extra_nodes.append(prompt_clone)
            clone_edge.source_node_id = prompt_clone.id
            clone_edge.source = None
            clone_edge.sourceNodeId = None
            clone_edge.from_node = None
        edges.append(clone_edge)
    return extra_nodes, edges


def attach_variant_result(project: Project, variant_set_id: str, job_id: str, artifact_ids: list[str]) -> None:
    variant_set = next((item for item in project.variant_sets if item.id == variant_set_id), None)
    if variant_set is None:
        return
    if job_id not in variant_set.job_ids:
        variant_set.job_ids.append(job_id)
    for asset_id in artifact_ids:
        if asset_id not in variant_set.artifact_ids:
            variant_set.artifact_ids.append(asset_id)
    variant_set.status = "success" if artifact_ids else variant_set.status
    variant_set.updated_at = utc_now()
