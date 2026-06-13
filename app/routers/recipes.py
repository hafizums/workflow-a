from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.application.use_cases.recipes import RecipeUseCase
from app.schemas import CreateProjectFromRecipeRequest, Project, WorkflowRecipe
from app.services.recipe_store import RecipeError

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("", response_model=list[WorkflowRecipe])
async def recipes():
    return RecipeUseCase().list()


@router.get("/{recipe_id}", response_model=WorkflowRecipe)
async def recipe(recipe_id: str):
    try:
        return RecipeUseCase().get(recipe_id)
    except RecipeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{recipe_id}/create-project", response_model=Project)
async def create_project(recipe_id: str, payload: CreateProjectFromRecipeRequest | None = None):
    payload = payload or CreateProjectFromRecipeRequest()
    try:
        return await RecipeUseCase().create_project(recipe_id, payload)
    except RecipeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
