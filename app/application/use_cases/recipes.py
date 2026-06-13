from __future__ import annotations

from app.infrastructure.repositories.json_recipe_repository import JsonRecipeRepository


class RecipeUseCase:
    def __init__(self, recipes: JsonRecipeRepository | None = None):
        self.recipes = recipes or JsonRecipeRepository()

    def list(self):
        return self.recipes.list()

    def get(self, recipe_id: str):
        return self.recipes.get(recipe_id)

    async def create_project(self, recipe_id: str, payload):
        return await self.recipes.create_project(recipe_id, name=payload.name, description=payload.description)

