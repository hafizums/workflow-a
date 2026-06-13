from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas import CanvasNode, NodeType, Project


@dataclass(slots=True)
class NodeRunContext:
    project: Project | None
    node: CanvasNode | None
    node_type: NodeType
    effective_model_id: str | None
    resolved_inputs: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    request_metadata: dict[str, Any] = field(default_factory=dict)

