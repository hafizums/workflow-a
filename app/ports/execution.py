from __future__ import annotations

from typing import Protocol

from app.application.dto.node_run_context import NodeRunContext
from app.domain.results.node_run_result import NodeRunResult


class NodeExecutor(Protocol):
    def supports(self, context: NodeRunContext) -> bool:
        ...

    async def run(self, context: NodeRunContext) -> NodeRunResult:
        ...

