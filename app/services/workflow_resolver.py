from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from app.schemas import Asset, CanvasNode, Project
from app.services.cost_estimator import ESTIMATE_WARNING, evaluate_cost_guard, evaluate_workflow_cost_guard
from app.services.registry import resolve_model_for_node


class WorkflowResolverError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class NormalizedEdge:
    id: str
    source_node_id: str
    target_node_id: str
    source_output: str = "output"
    target_input: str = "image"


@dataclass
class Graph:
    node_index: dict[str, CanvasNode]
    edges: list[NormalizedEdge]
    incoming: dict[str, list[NormalizedEdge]]
    outgoing: dict[str, list[NormalizedEdge]]
    warnings: list[dict[str, Any]]
    errors: list[dict[str, Any]]


def build_workflow_plan(
    project: Project,
    mode: str = "whole_graph",
    node_id: str | None = None,
) -> dict[str, Any]:
    graph = build_graph(project)
    warnings = list(graph.warnings)
    errors = list(graph.errors)

    if mode not in {"selected", "from_node", "whole_graph"}:
        errors.append(error("invalid_mode", "Mode must be selected, from_node, or whole_graph.", {"mode": mode}))
        return plan_response(project, mode, [], [], warnings, errors)

    if mode in {"selected", "from_node"} and not node_id:
        errors.append(error("missing_node_id", "node_id is required for this planning mode.", {"mode": mode}))
        return plan_response(project, mode, [], [], warnings, errors)

    if node_id and node_id not in graph.node_index:
        errors.append(error("missing_node", f"Node {node_id} was not found in the project.", {"node_id": node_id}))
        return plan_response(project, mode, [], [], warnings, errors)

    cycle = find_cycle(graph.node_index, graph.edges)
    if cycle:
        errors.append(error("cycle_detected", "Workflow graph contains a cycle.", {"node_ids": cycle}))
        return plan_response(project, mode, [], [], warnings, errors)

    selected_ids = select_node_ids(graph, mode, node_id, project)
    ordered_ids = topological_sort(graph)
    plan_ids = [current_id for current_id in ordered_ids if current_id in selected_ids]

    steps = [
        build_step(index, graph.node_index[current_id], graph, project, warnings, errors)
        for index, current_id in enumerate(plan_ids)
    ]
    return plan_response(project, mode, plan_ids, steps, warnings, errors)


def build_execution_plan(
    project: Project,
    mode: str,
    node_id: str | None = None,
) -> tuple[Graph, list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    graph = build_graph(project)
    warnings = list(graph.warnings)
    errors = list(graph.errors)

    if mode not in {"selected", "from_node", "whole_graph"}:
        errors.append(error("invalid_mode", "Mode must be selected, from_node, or whole_graph.", {"mode": mode}))
        return graph, [], warnings, errors

    if mode in {"selected", "from_node"} and not node_id:
        errors.append(error("missing_node_id", "node_id is required for this planning mode.", {"mode": mode}))
        return graph, [], warnings, errors

    if node_id and node_id not in graph.node_index:
        errors.append(error("missing_node", f"Node {node_id} was not found in the project.", {"node_id": node_id}))
        return graph, [], warnings, errors

    cycle = find_cycle(graph.node_index, graph.edges)
    if cycle:
        errors.append(error("cycle_detected", "Workflow graph contains a cycle.", {"node_ids": cycle}))
        return graph, [], warnings, errors

    if mode == "whole_graph":
        selected_ids = set(graph.node_index)
    else:
        selected_ids = select_node_ids(graph, mode, node_id, project)
    ordered_ids = topological_sort(graph)
    return graph, [current_id for current_id in ordered_ids if current_id in selected_ids], warnings, errors


def resolve_inputs_for_node(
    node: CanvasNode,
    graph: Graph,
    project: Project,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    resolved_inputs = dict(node.inputs or {})
    for edge in graph.incoming.get(node.id, []):
        source_node = graph.node_index[edge.source_node_id]
        resolved_output = resolve_source_output(source_node, project)
        if resolved_output:
            resolved_inputs[edge.target_input] = resolved_output
        else:
            errors.append(
                error(
                    "missing_upstream_output",
                    f"Source node {source_node.id} has no output URL yet. Run it first.",
                    {
                        "source_node_id": source_node.id,
                        "target_node_id": node.id,
                        "edge_id": edge.id,
                    },
                )
            )
    return resolved_inputs, errors


def build_graph(project: Project) -> Graph:
    node_index = {node.id: node for node in project.nodes}
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    edges: list[NormalizedEdge] = []
    incoming = {node_id: [] for node_id in node_index}
    outgoing = {node_id: [] for node_id in node_index}

    for index, raw_edge in enumerate(project.edges or []):
        normalized = normalize_edge(raw_edge, index)
        if not normalized.source_node_id:
            errors.append(error("invalid_edge_source", "Edge is missing a source node ID.", {"edge_id": normalized.id}))
            continue
        if not normalized.target_node_id:
            errors.append(error("invalid_edge_target", "Edge is missing a target node ID.", {"edge_id": normalized.id}))
            continue
        if normalized.source_node_id not in node_index:
            errors.append(
                error(
                    "invalid_edge_source",
                    f"Edge {normalized.id} references missing source node {normalized.source_node_id}.",
                    {"edge_id": normalized.id, "source_node_id": normalized.source_node_id},
                )
            )
            continue
        if normalized.target_node_id not in node_index:
            errors.append(
                error(
                    "invalid_edge_target",
                    f"Edge {normalized.id} references missing target node {normalized.target_node_id}.",
                    {"edge_id": normalized.id, "target_node_id": normalized.target_node_id},
                )
            )
            continue
        if normalized.target_input in {"", "input"}:
            normalized.target_input = default_target_input(node_index[normalized.target_node_id])

        edges.append(normalized)
        outgoing[normalized.source_node_id].append(normalized)
        incoming[normalized.target_node_id].append(normalized)

    return Graph(
        node_index=node_index,
        edges=edges,
        incoming=incoming,
        outgoing=outgoing,
        warnings=warnings,
        errors=errors,
    )


def normalize_edge(raw_edge: Any, index: int) -> NormalizedEdge:
    edge_id = value_from(raw_edge, "id") or f"edge_{index + 1}"
    source_node_id = value_from(raw_edge, "source_node_id", "source", "from", "from_node", "sourceNodeId", "source_node") or ""
    target_node_id = value_from(raw_edge, "target_node_id", "target", "to", "targetNodeId", "target_node") or ""
    source_output = value_from(raw_edge, "source_output", "source_handle", "sourceHandle") or "output"
    target_input = value_from(raw_edge, "target_input", "target_handle", "targetHandle") or "input"
    return NormalizedEdge(
        id=str(edge_id),
        source_node_id=str(source_node_id),
        target_node_id=str(target_node_id),
        source_output=str(source_output),
        target_input=str(target_input),
    )


def default_target_input(node: CanvasNode) -> str:
    if node.type.value in {"image_to_video", "image_to_image", "upscale_image", "remove_background", "remove_object"}:
        return "image"
    if node.type.value in {"start_end_to_video"}:
        return "image"
    if node.type.value in {"reference_to_image", "reference_to_video"}:
        return "reference_image"
    if node.type.value in {"video_extend", "video_effect"}:
        return "video"
    if node.type.value in {"speech_to_text", "lip_sync"}:
        return "audio"
    return "input"


def value_from(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            value = obj[name]
            if value not in (None, ""):
                return value
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value not in (None, ""):
                return value
    return None


def select_node_ids(graph: Graph, mode: str, node_id: str | None, project: Project) -> set[str]:
    if mode == "selected":
        return {node_id} if node_id else set()
    if mode == "from_node":
        return downstream_ids(graph, node_id) if node_id else set()
    return {node_id for node_id, node in graph.node_index.items() if is_runnable(node, project)}


def downstream_ids(graph: Graph, node_id: str) -> set[str]:
    selected = {node_id}
    queue: deque[str] = deque([node_id])
    while queue:
        current_id = queue.popleft()
        for edge in graph.outgoing.get(current_id, []):
            if edge.target_node_id not in selected:
                selected.add(edge.target_node_id)
                queue.append(edge.target_node_id)
    return selected


def topological_sort(graph: Graph) -> list[str]:
    indegree = {node_id: 0 for node_id in graph.node_index}
    for edge in graph.edges:
        indegree[edge.target_node_id] += 1

    queue: deque[str] = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    ordered: list[str] = []
    while queue:
        current_id = queue.popleft()
        ordered.append(current_id)
        for edge in graph.outgoing.get(current_id, []):
            indegree[edge.target_node_id] -= 1
            if indegree[edge.target_node_id] == 0:
                queue.append(edge.target_node_id)
    return ordered


def find_cycle(node_index: dict[str, CanvasNode], edges: list[NormalizedEdge]) -> list[str]:
    indegree = {node_id: 0 for node_id in node_index}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_index}
    for edge in edges:
        indegree[edge.target_node_id] += 1
        outgoing[edge.source_node_id].append(edge.target_node_id)

    queue: deque[str] = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        current_id = queue.popleft()
        visited += 1
        for target_id in outgoing[current_id]:
            indegree[target_id] -= 1
            if indegree[target_id] == 0:
                queue.append(target_id)

    if visited == len(node_index):
        return []
    return [node_id for node_id, degree in indegree.items() if degree > 0]


def build_step(
    index: int,
    node: CanvasNode,
    graph: Graph,
    project: Project,
    warnings: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    resolution = resolve_model_for_node(
        node_type=node.type,
        node_model_id=node.model_id,
        project_model_overrides=project.settings.model_overrides,
    )
    model = resolution.model
    incoming_edges = graph.incoming.get(node.id, [])
    outgoing_edges = graph.outgoing.get(node.id, [])
    resolved_inputs = dict(node.inputs or {})

    for edge in incoming_edges:
        source_node = graph.node_index[edge.source_node_id]
        resolved_output = resolve_source_output(source_node, project)
        if resolved_output:
            resolved_inputs[edge.target_input] = resolved_output
        else:
            errors.append(
                error(
                    "missing_upstream_output",
                    f"Source node {source_node.id} has no output URL yet. Run it first.",
                    {
                        "source_node_id": source_node.id,
                        "target_node_id": node.id,
                        "edge_id": edge.id,
                    },
                )
            )

    status = "ready"
    if resolution.error:
        status = "skipped"
        warnings.append(
            warning(
                "model_resolution_failed",
                resolution.error,
                {"node_id": node.id, "model_id": resolution.model_id, "model_source": resolution.source},
            )
        )
    elif not model.enabled:
        status = "skipped"
        warnings.append(
            warning(
                "disabled_model",
                model.enabled_reason or f"Node {node.id} uses a disabled model.",
                {"node_id": node.id, "model_id": resolution.model_id, "model_source": resolution.source},
            )
        )

    guard = evaluate_cost_guard(model.estimated_base_cost_usd if model else None, project.settings.cost_guard)
    output_kind = model.output_kind.value if model else None

    return {
        "index": index,
        "node_id": node.id,
        "node_type": node.type.value,
        "model_id": resolution.model_id,
        "effective_model_id": resolution.model_id,
        "node_model_id": node.model_id,
        "project_override_model_id": project.settings.model_overrides.get(node.type.value),
        "catalog_default_model_id": model.default_model_id if model else None,
        "model_source": resolution.source,
        "estimated_base_cost_usd": model.estimated_base_cost_usd if model else None,
        "cost_unit": model.cost_unit if model else None,
        "pricing_note": model.pricing_note if model else None,
        "output_kind": output_kind,
        "requires_confirmation": guard["requires_confirmation"],
        "blocked": guard["blocked"],
        "cost_guard_message": guard["cost_guard_message"],
        "cost_guard": {
            "status": guard["status"],
            "message": guard["message"],
            "limit_usd": guard["limit_usd"],
            "blocked": guard["blocked"],
            "requires_confirmation": guard["requires_confirmation"],
        },
        "display_name": model.label if model else node.title,
        "status": status,
        "resolved_inputs": resolved_inputs,
        "resolved_input_keys": list(resolved_inputs.keys()),
        "incoming_edges": [edge.id for edge in incoming_edges],
        "outgoing_edges": [edge.id for edge in outgoing_edges],
    }


def resolve_source_output(node: CanvasNode, project: Project) -> str | None:
    if node.output_urls:
        return node.output_urls[0]

    data = getattr(node, "data", None)
    if isinstance(data, dict):
        output_urls = data.get("output_urls")
        if output_urls:
            return output_urls[0]
        outputs = data.get("outputs")
        if isinstance(outputs, dict) and outputs.get("image"):
            return outputs["image"]

    outputs = getattr(node, "outputs", None)
    if isinstance(outputs, dict) and outputs.get("image"):
        return outputs["image"]

    if node.type.value == "upload_image" and node.inputs.get("image"):
        return node.inputs["image"]

    if node.output_asset_ids:
        asset = find_asset(project.assets, node.output_asset_ids[0])
        if asset:
            return asset.wavespeed_url or asset.public_url or asset.local_path

    return None


def find_asset(assets: list[Asset], asset_id: str) -> Asset | None:
    return next((asset for asset in assets if asset.id == asset_id), None)


def is_runnable(node: CanvasNode, project: Project) -> bool:
    resolution = resolve_model_for_node(
        node_type=node.type,
        node_model_id=node.model_id,
        project_model_overrides=project.settings.model_overrides,
    )
    return bool(resolution.model and resolution.model.enabled and not resolution.error)


def plan_response(
    project: Project,
    mode: str,
    node_ids: list[str],
    steps: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    cost_summary = workflow_cost_summary(steps, project)
    return {
        "ok": not errors,
        "project_id": project.id,
        "mode": mode,
        "node_ids": node_ids,
        **cost_summary,
        "steps": steps,
        "warnings": warnings,
        "errors": errors,
    }


def workflow_cost_summary(steps: list[dict[str, Any]], project: Project) -> dict[str, Any]:
    runnable_steps = [step for step in steps if step.get("status") == "ready"]
    known_cost = 0.0
    has_unknown_cost = False

    for step in runnable_steps:
        estimate = step.get("estimated_base_cost_usd")
        if estimate is None:
            has_unknown_cost = True
            continue
        known_cost += float(estimate)

    estimated_total_cost_usd = None if has_unknown_cost else round(known_cost, 6)
    guard = evaluate_workflow_cost_guard(
        estimated_total_cost_usd=estimated_total_cost_usd,
        has_unknown_cost=has_unknown_cost,
        cost_guard=project.settings.cost_guard,
    )
    return {
        "estimated_total_cost_usd": estimated_total_cost_usd,
        "estimated_known_cost_usd": round(known_cost, 6),
        "pricing_note": ESTIMATE_WARNING,
        "cost_guard": guard,
    }


def warning(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
    }


def error(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
    }
