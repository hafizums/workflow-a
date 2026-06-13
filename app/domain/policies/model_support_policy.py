from __future__ import annotations

from app.schemas import NodeType
from app.services.registry import ModelResolution, resolve_model_for_node


class ModelSupportPolicy:
    """Facade for model resolution and disabled-model guardrails."""

    def resolve(
        self,
        *,
        node_type: NodeType,
        node_model_id: str | None = None,
        project_model_overrides: dict[str, str] | None = None,
    ) -> ModelResolution:
        return resolve_model_for_node(
            node_type=node_type,
            node_model_id=node_model_id,
            project_model_overrides=project_model_overrides,
        )

