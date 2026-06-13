from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from app.infrastructure.repositories.json_project_repository import JsonProjectRepository
from app.schemas import Project
from app.services.project_validation import validate_edges_reference_nodes, validate_project_settings

T = TypeVar("T")


class ProjectTransaction:
    """Unit-of-work-lite for one load, in-memory mutation, validation, and save."""

    def __init__(self, projects: JsonProjectRepository | None = None):
        self.projects = projects or JsonProjectRepository()

    async def mutate(self, project_id: str, mutator: Callable[[Project], T]) -> tuple[Project, T]:
        project = await self.projects.load(project_id)
        result = mutator(project)
        self.validate(project)
        await self.projects.save(project)
        return project, result

    @staticmethod
    def validate(project: Project) -> None:
        validate_project_settings(project.settings)
        validate_edges_reference_nodes(project.edges, {node.id for node in project.nodes})

