from __future__ import annotations

from app.infrastructure.repositories.json_project_repository import JsonProjectRepository
from app.infrastructure.repositories.json_template_repository import JsonTemplateRepository


class TemplateUseCase:
    def __init__(
        self,
        *,
        templates: JsonTemplateRepository | None = None,
        projects: JsonProjectRepository | None = None,
    ):
        self.templates = templates or JsonTemplateRepository()
        self.projects = projects or JsonProjectRepository()

    async def list(self, *, category: str | None = None, builtin: bool | None = None):
        return await self.templates.list(category=category, builtin=builtin)

    async def get(self, template_id: str):
        return await self.templates.get(template_id)

    async def create(self, payload):
        return await self.templates.create(payload)

    async def update(self, template_id: str, payload):
        return await self.templates.update(template_id, payload.model_dump(exclude_unset=True))

    async def delete(self, template_id: str) -> None:
        await self.templates.delete(template_id)

    async def create_from_project(self, project_id: str, payload):
        project = await self.projects.load(project_id)
        return await self.templates.create_from_project(
            project,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            tags=payload.tags,
            include_outputs=payload.include_outputs,
            include_settings=payload.include_settings,
        )

    async def create_project_from_template(self, template_id: str, payload):
        return await self.templates.create_project_from_template(
            template_id,
            name=payload.name,
            description=payload.description,
        )

