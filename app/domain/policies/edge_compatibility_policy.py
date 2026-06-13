from __future__ import annotations

from app.schemas import Project
from app.services.workflow_resolver import build_graph


class EdgeCompatibilityPolicy:
    """Facade for graph edge validation and compatibility checks."""

    def build_graph(self, project: Project):
        return build_graph(project)

    def validate(self, project: Project) -> list[dict]:
        graph = build_graph(project)
        return list(graph.errors)

