from __future__ import annotations

from typing import Any

from app.schemas import CanvasNode
from app.services.workflow_resolver import validate_prompt_card_inputs


class PromptSourcePolicy:
    """Facade for prompt/text source validation."""

    def validate(self, node: CanvasNode, graph: Any) -> list[dict]:
        return validate_prompt_card_inputs(node, graph)
