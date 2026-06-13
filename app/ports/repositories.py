from __future__ import annotations

from typing import Any, Protocol

from app.schemas import Project, WorkflowRecipe, WorkflowTemplate, WorkflowTemplateCreate


class ProjectRepository(Protocol):
    async def list(self) -> list[Project]:
        ...

    async def load(self, project_id: str) -> Project:
        ...

    async def save(self, project: Project) -> Project:
        ...

    async def delete(self, project_id: str) -> None:
        ...


class TemplateRepository(Protocol):
    async def list(self, *, category: str | None = None, builtin: bool | None = None) -> list[WorkflowTemplate]:
        ...

    async def get(self, template_id: str) -> WorkflowTemplate:
        ...

    async def create(self, payload: WorkflowTemplateCreate) -> WorkflowTemplate:
        ...

    async def update(self, template_id: str, updates: dict[str, Any]) -> WorkflowTemplate:
        ...

    async def delete(self, template_id: str) -> None:
        ...


class RecipeRepository(Protocol):
    def list(self) -> list[WorkflowRecipe]:
        ...

    def get(self, recipe_id: str) -> WorkflowRecipe:
        ...

    async def create_project(self, recipe_id: str, name: str | None = None, description: str = "") -> Project:
        ...

    async def apply_to_project(self, project: Project, recipe_id: str) -> Project:
        ...


class ModelCatalog(Protocol):
    def list_models(self, include_excluded: bool = False) -> list[Any]:
        ...

    def get_model(self, model_id: str) -> Any | None:
        ...


class CatalogRepository(Protocol):
    def summary(self, include_excluded: bool = False) -> dict[str, Any]:
        ...

    def list(self, include_excluded: bool = False) -> list[Any]:
        ...

    def get(self, model_id: str) -> Any | None:
        ...

    def schema(self, model_id: str) -> list[Any]:
        ...

    def capabilities(self) -> list[dict[str, Any]]:
        ...

    def cheapest(self) -> list[dict[str, Any]]:
        ...

    def excluded(self) -> list[Any]:
        ...
