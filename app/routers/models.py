from fastapi import APIRouter

from app.schemas import CategorySpec, ModelSpec
from app.services.registry import CATEGORIES, MODELS

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/categories", response_model=list[CategorySpec])
def list_categories():
    return CATEGORIES


@router.get("/models", response_model=list[ModelSpec])
def list_models(enabled_only: bool = False):
    if enabled_only:
        return [model for model in MODELS if model.enabled]
    return MODELS
