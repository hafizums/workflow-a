from __future__ import annotations

from pydantic import ValidationError

from app.application.use_cases.errors import ApplicationError
from app.infrastructure.repositories.json_project_repository import JsonProjectRepository
from app.schemas import CostGuardSettings, ProjectSettings, ProjectSettingsUpdate
from app.services import project_store
from app.services.project_validation import ProjectValidationError, validate_project_settings


class ProjectSettingsUseCase:
    def __init__(self, projects: JsonProjectRepository | None = None):
        self.projects = projects or JsonProjectRepository()

    async def get(self, project_id: str) -> ProjectSettings:
        try:
            project = await self.projects.load(project_id)
        except project_store.ProjectStoreError as exc:
            raise self.project_error(exc) from exc
        return project.settings

    async def update(self, project_id: str, payload: ProjectSettingsUpdate) -> ProjectSettings:
        try:
            project = await self.projects.load(project_id)
        except project_store.ProjectStoreError as exc:
            raise self.project_error(exc) from exc
        project.settings = self.merge(project.settings, payload)
        await self.projects.save(project)
        return project.settings

    @staticmethod
    def merge(current: ProjectSettings, payload: ProjectSettingsUpdate) -> ProjectSettings:
        data = current.model_dump()
        if payload.model_overrides is not None:
            data["model_overrides"] = payload.model_overrides
        if payload.cost_guard is not None:
            cost_guard_data = current.cost_guard.model_dump()
            cost_guard_data.update(payload.cost_guard.model_dump(exclude_unset=True))
            try:
                data["cost_guard"] = CostGuardSettings.model_validate(cost_guard_data)
            except ValidationError as exc:
                raise ApplicationError(422, exc.errors()) from exc
        try:
            return validate_project_settings(ProjectSettings.model_validate(data))
        except ProjectValidationError as exc:
            raise ApplicationError(400, str(exc)) from exc

    @staticmethod
    def project_error(exc: project_store.ProjectStoreError) -> ApplicationError:
        if isinstance(exc, project_store.InvalidProjectIdError):
            return ApplicationError(400, str(exc))
        if isinstance(exc, project_store.ProjectNotFoundError):
            return ApplicationError(404, str(exc))
        if isinstance(exc, project_store.ProjectStorageSchemaError):
            return ApplicationError(500, str(exc))
        return ApplicationError(500, "Project storage error")
