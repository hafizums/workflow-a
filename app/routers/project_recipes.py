from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import Project
from app.services import project_store
from app.services.recipe_store import RecipeError, apply_recipe_to_project

router = APIRouter(prefix="/api/projects/{project_id}", tags=["recipes"])


@router.post("/apply-recipe/{recipe_id}", response_model=Project)
async def apply_recipe(project_id: str, recipe_id: str):
    try:
        project = await project_store.load_project(project_id)
        return await apply_recipe_to_project(project, recipe_id)
    except project_store.ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except project_store.ProjectStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RecipeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
