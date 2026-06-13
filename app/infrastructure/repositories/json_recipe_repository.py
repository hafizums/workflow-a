from __future__ import annotations

from app.schemas import Project
from app.services import recipe_store


class JsonRecipeRepository:
    """Recipe repository backed by the existing built-in recipe store."""

    def list(self):
        return recipe_store.list_recipes()

    def get(self, recipe_id: str):
        return recipe_store.get_recipe(recipe_id)

    async def create_project(self, recipe_id: str, name: str | None = None, description: str = ""):
        return await recipe_store.create_project_from_recipe(recipe_id, name=name, description=description)

    async def apply_to_project(self, project: Project, recipe_id: str):
        return await recipe_store.apply_recipe_to_project(project, recipe_id)

