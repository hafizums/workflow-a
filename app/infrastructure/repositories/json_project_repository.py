from __future__ import annotations

from app.core.config import Settings
from app.schemas import Project
from app.services import project_store


class JsonProjectRepository:
    """Local JSON project repository preserving the existing project_store behavior."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings

    async def list(self) -> list[Project]:
        return await project_store.list_projects(self.settings)

    async def load(self, project_id: str) -> Project:
        return await project_store.load_project(project_id, self.settings)

    async def save(self, project: Project) -> Project:
        return await project_store.save_project(project, self.settings)

    async def delete(self, project_id: str) -> None:
        await project_store.delete_project(project_id, self.settings)

