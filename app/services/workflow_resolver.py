from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from app.schemas import Asset, CanvasNode, Project
from app.services.cost_estimator import ESTIMATE_WARNING, evaluate_cost_guard, evaluate_workflow_cost_guard
from app.services.registry import resolve_model_for_node
from app.services.utility_tools import UTILITY_NODE_TYPES, get_utility_tool

PROMPT_CARD_ONLY_INPUTS = {"prompt", "text"}


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
    plan_ids = [current_id for current_id in ordered_ids if current_id in selected_ids and is_runnable(graph.node_index[current_id], project)]

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

    selected_ids = select_node_ids(graph, mode, node_id, project)
    ordered_ids = topological_sort(graph)
    return graph, [current_id for current_id in ordered_ids if current_id in selected_ids and is_runnable(graph.node_index[current_id], project)], warnings, errors


def resolve_inputs_for_node(
    node: CanvasNode,
    graph: Graph,
    project: Project,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    resolved_inputs = dict(node.inputs or {})
    list_inputs = list_input_names_for_node(node, project)
    list_entries: dict[str, list[dict[str, Any]]] = {
        input_name: [
            {"key": list_input_order_key(value), "value": value}
            for value in as_list(resolved_inputs.get(input_name))
        ]
        for input_name in list_inputs
    }
    for edge in graph.incoming.get(node.id, []):
        source_node = graph.node_index[edge.source_node_id]
        resolved_output = resolve_source_output(source_node, project, target_input=edge.target_input)
        if resolved_output:
            if edge.target_input in list_inputs:
                list_entries.setdefault(edge.target_input, []).append(
                    {"key": f"edge:{edge.id}", "value": resolved_output}
                )
            else:
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
    for input_name, entries in list_entries.items():
        resolved_inputs[input_name] = ordered_list_values(entries, as_list(resolved_inputs.get(f"{input_name}_order")))
    return resolved_inputs, errors


def list_input_names_for_node(node: CanvasNode, project: Project) -> set[str]:
    if node.type in UTILITY_NODE_TYPES:
        utility = get_utility_tool(node.type)
        fields = utility.fields if utility else []
    else:
        resolution = resolve_model_for_node(
            node_type=node.type,
            node_model_id=node.model_id,
            project_model_overrides=project.settings.model_overrides,
        )
        fields = resolution.model.fields if resolution.model else []
    return {field.name for field in fields if is_list_input_field(field)}


def is_list_input_field(field: Any) -> bool:
    if getattr(field, "type", None) == "asset_url_list":
        return True
    name = str(getattr(field, "name", "")).lower()
    if name in {
        "images",
        "image_urls",
        "source_images",
        "target_images",
        "reference_images",
        "reference_urls",
        "refer_images",
        "mask_images",
        "clothes_images",
        "videos",
        "video_urls",
        "reference_videos",
        "ref_videos",
        "audios",
        "audio_urls",
        "reference_audios",
    }:
        return True
    if name.endswith(("_images", "_videos", "_audios")):
        return True
    description = str(getattr(field, "description", "") or "").lower()
    return name == "reference" and "reference image" in description


def as_list(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    return [value]


def list_input_order_key(value: Any) -> str:
    return f"asset:{value}" if isinstance(value, str) else str(value)


def ordered_list_values(entries: list[dict[str, Any]], order: list[Any]) -> list[Any]:
    if not order:
        return [entry["value"] for entry in entries]

    order_index = {str(key): index for index, key in enumerate(order)}
    fallback = len(order_index)
    return [
        entry["value"]
        for _index, entry in sorted(
            enumerate(entries),
            key=lambda pair: (order_index.get(pair[1]["key"], fallback + pair[0]), pair[0]),
        )
    ]


PROMPT_SOURCE_NODE_TYPES = {"prompt_card", "llm_text", "llm_vision", "speech_to_text"}


def validate_prompt_card_inputs(node: CanvasNode, graph: Graph) -> list[dict[str, Any]]:
    required_inputs = prompt_card_only_inputs_for_node(node)
    if not required_inputs:
        return []
    incoming = graph.incoming.get(node.id, [])
    errors: list[dict[str, Any]] = []
    for input_name in required_inputs:
        matching_edges = [edge for edge in incoming if edge.target_input == input_name]
        if not matching_edges:
            errors.append(
                error(
                    "prompt_card_required",
                    f"{node.type.value}.{input_name} must come from a connected Prompt Card, LLM text, or transcript node.",
                    {"node_id": node.id, "input": input_name},
                )
            )
            continue
        if not any(graph.node_index[edge.source_node_id].type.value in PROMPT_SOURCE_NODE_TYPES for edge in matching_edges):
            errors.append(
                error(
                    "prompt_card_required",
                    f"{node.type.value}.{input_name} is connected, but it must come from a Prompt Card, LLM text, or transcript node.",
                    {"node_id": node.id, "input": input_name},
                )
            )
    return errors


def prompt_card_only_inputs_for_node(node: CanvasNode) -> set[str]:
    if node.type in UTILITY_NODE_TYPES:
        return set()
    if node.type.value in {"text_to_image", "image_to_image", "reference_to_image", "remove_object", "image_to_video", "start_end_to_video", "text_to_video", "reference_to_video", "talking_avatar", "text_to_3d"}:
        return {"prompt"}
    if node.type.value in {"text_to_speech", "text_to_audio", "generate_voice", "llm_text", "llm_vision"}:
        return {"text"}
    return set()


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
    if node.type.value in {"text_to_image", "text_to_video", "text_to_3d"}:
        return "prompt"
    if node.type.value in {"text_to_speech", "text_to_audio", "generate_voice", "llm_text", "llm_vision"}:
        return "text"
    if node.type.value in {"image_to_3d"}:
        return "front_image_url"
    if node.type.value in {"image_to_video", "image_to_image", "upscale_image", "remove_background", "remove_object", "portrait_transfer"}:
        return "image"
    if node.type.value in {"start_end_to_video"}:
        return "image"
    if node.type.value in {"reference_to_image", "reference_to_video"}:
        return "reference_image"
    if node.type.value in {"video_extend"}:
        return "video"
    if node.type.value in {"video_effect"}:
        return "image"
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
    utility_model = get_utility_tool(node.type)
    resolution = None
    if utility_model is None:
        resolution = resolve_model_for_node(
            node_type=node.type,
            node_model_id=node.model_id,
            project_model_overrides=project.settings.model_overrides,
        )
    model = utility_model or resolution.model
    incoming_edges = graph.incoming.get(node.id, [])
    outgoing_edges = graph.outgoing.get(node.id, [])
    resolved_inputs = dict(node.inputs or {})

    for edge in incoming_edges:
        source_node = graph.node_index[edge.source_node_id]
        resolved_output = resolve_source_output(source_node, project, target_input=edge.target_input)
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
    prompt_errors = validate_prompt_card_inputs(node, graph)
    if prompt_errors:
        status = "skipped"
        errors.extend(prompt_errors)
    elif node.type in UTILITY_NODE_TYPES:
        status = "utility"
    elif resolution and resolution.error:
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
        "model_id": resolution.model_id if resolution else None,
        "effective_model_id": resolution.model_id if resolution else None,
        "node_model_id": node.model_id,
        "project_override_model_id": project.settings.model_overrides.get(node.type.value),
        "catalog_default_model_id": model.default_model_id if model else None,
        "model_source": resolution.source if resolution else "utility",
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


def resolve_source_output(node: CanvasNode, project: Project, target_input: str | None = None) -> str | None:
    utility_output = resolve_utility_output(node, project, target_input=target_input)
    if utility_output:
        return utility_output

    if node.output_urls:
        return node.output_urls[0]

    text_output = node.last_run.get("text_output") if isinstance(node.last_run, dict) else None
    if isinstance(text_output, str) and text_output.strip():
        return text_output.strip()

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

    if node.type.value == "upload_image":
        for input_name in ("asset_url", "image", "audio", "video"):
            if node.inputs.get(input_name):
                return node.inputs[input_name]

    if node.output_asset_ids:
        asset = find_asset(project.assets, node.output_asset_ids[0])
        if asset:
            return asset.wavespeed_url or asset.public_url or asset.local_path

    return None


def resolve_utility_output(node: CanvasNode, project: Project, target_input: str | None = None) -> str | None:
    if node.type.value == "prompt_card":
        if target_input == "negative_prompt":
            return str(node.inputs.get("negative_prompt") or "").strip() or None
        return str(node.inputs.get("text") or "").strip() or None
    if node.type.value == "style_card":
        parts = [
            node.inputs.get("visual_style"),
            node.inputs.get("camera"),
            node.inputs.get("lighting"),
            node.inputs.get("color_palette"),
            node.inputs.get("mood"),
            node.inputs.get("quality_rules"),
        ]
        return ", ".join(str(part).strip() for part in parts if str(part or "").strip()) or None
    if node.type.value == "character_card":
        parts = [
            node.inputs.get("name"),
            node.inputs.get("description"),
            node.inputs.get("appearance"),
            node.inputs.get("consistency_notes"),
        ]
        return ". ".join(str(part).strip() for part in parts if str(part or "").strip()) or None
    if node.type.value == "asset_input":
        asset_id = str(node.inputs.get("asset_id") or "").strip()
        asset = find_asset(project.assets, asset_id) if asset_id else None
        if asset:
            return asset.id
        return asset_id or None
    if node.type.value == "asset_selector":
        return str(node.inputs.get("selected_asset_id") or "").strip() or None
    if node.type.value == "reroute":
        for key in ("value", "image", "video", "audio", "prompt", "asset_id"):
            if node.inputs.get(key):
                return str(node.inputs[key])
    if node.type.value in {"compare_board", "export_package"} and node.inputs.get("selected_asset_id"):
        return str(node.inputs["selected_asset_id"])
    return None


def find_asset(assets: list[Asset], asset_id: str) -> Asset | None:
    return next((asset for asset in assets if asset.id == asset_id), None)


def is_runnable(node: CanvasNode, project: Project) -> bool:
    if node.type in UTILITY_NODE_TYPES:
        return False
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
