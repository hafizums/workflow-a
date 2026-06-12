from __future__ import annotations

from app.schemas import CanvasEdge, NodeType, ProjectSettings
from app.services.registry import get_model_for_node


class ProjectValidationError(ValueError):
    """Raised when imported or updated project data is incompatible."""


def validate_project_settings(settings: ProjectSettings) -> ProjectSettings:
    for node_type_value, model_id in settings.model_overrides.items():
        try:
            node_type = NodeType(node_type_value)
        except ValueError as exc:
            raise ProjectValidationError(f"Unknown node type for model override: {node_type_value}") from exc

        model = get_model_for_node(node_type, model_id)
        if model is None:
            raise ProjectValidationError(f"Model {model_id} is not registered for node type {node_type.value}.")
        if not model.enabled:
            raise ProjectValidationError(
                model.enabled_reason or f"Model {model_id} is disabled for node type {node_type.value}."
            )

    return settings


def validate_edges_reference_nodes(edges: list[CanvasEdge], node_ids: set[str]) -> None:
    for edge in edges:
        source = edge.source_node_id or edge.source or edge.source_node or edge.sourceNodeId or edge.from_node or ""
        target = edge.target_node_id or edge.target or edge.target_node or edge.targetNodeId or edge.to or ""
        if source not in node_ids or target not in node_ids:
            raise ProjectValidationError(f"Edge {edge.id} references a missing node.")
        edge.source_node_id = source
        edge.target_node_id = target
