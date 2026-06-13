from __future__ import annotations

from app.core.config import Settings
from app.schemas import Project, WorkflowTemplateCreate
from app.services import template_store


class JsonTemplateRepository:
    """Local JSON template repository preserving template_store behavior."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings

    async def list(self, *, category: str | None = None, builtin: bool | None = None):
        return await template_store.list_templates(category=category, builtin=builtin, settings=self.settings)

    async def get(self, template_id: str):
        return await template_store.get_template(template_id, self.settings)

    async def create(self, payload: WorkflowTemplateCreate):
        return await template_store.create_template(payload, self.settings)

    async def update(self, template_id: str, updates: dict):
        return await template_store.update_template(template_id, updates, self.settings)

    async def delete(self, template_id: str) -> None:
        await template_store.delete_template(template_id, self.settings)

    async def create_from_project(
        self,
        project: Project,
        *,
        name: str,
        description: str,
        category: str,
        tags: list[str],
        include_outputs: bool = False,
        include_settings: bool = True,
    ):
        return await template_store.create_template_from_project(
            project,
            name=name,
            description=description,
            category=category,
            tags=tags,
            include_outputs=include_outputs,
            include_settings=include_settings,
            settings=self.settings,
        )

    async def create_project_from_template(self, template_id: str, *, name: str | None, description: str):
        template = await self.get(template_id)
        return await template_store.create_project_from_template(template, name=name, description=description, settings=self.settings)

