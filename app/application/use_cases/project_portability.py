from __future__ import annotations

from app.infrastructure.repositories.json_project_repository import JsonProjectRepository
from app.schemas import ProjectDuplicateRequest
from app.services import portable_project, project_store


class ProjectPortabilityUseCase:
    def __init__(self, projects: JsonProjectRepository | None = None):
        self.projects = projects or JsonProjectRepository()

    def export(self, project, *, include_outputs: bool, include_settings: bool, include_run_history: bool) -> dict:
        return portable_project.export_project(
            project,
            include_outputs=include_outputs,
            include_settings=include_settings,
            include_run_history=include_run_history,
        )

    async def import_project(self, payload):
        return await portable_project.import_project(
            payload.import_data,
            name=payload.name,
            include_outputs=payload.include_outputs,
            include_run_history=payload.include_run_history,
        )

    async def duplicate_project(self, project_id: str, payload: ProjectDuplicateRequest):
        project = await self.projects.load(project_id)
        return await portable_project.duplicate_project(
            project,
            name=payload.name,
            include_outputs=payload.include_outputs,
            include_run_history=payload.include_run_history,
        )

    async def load_project(self, project_id: str):
        return await self.projects.load(project_id)

    @staticmethod
    def project_error(exc: project_store.ProjectStoreError):
        if isinstance(exc, project_store.InvalidProjectIdError):
            from app.application.use_cases.errors import ApplicationError

            return ApplicationError(400, str(exc))
        if isinstance(exc, project_store.ProjectNotFoundError):
            from app.application.use_cases.errors import ApplicationError

            return ApplicationError(404, str(exc))
        from app.application.use_cases.errors import ApplicationError

        return ApplicationError(500, "Project storage error")
