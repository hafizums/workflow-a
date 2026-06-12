from fastapi import APIRouter

from app.schemas import CategorySpec, ModelSpec
from app.services.registry import CATEGORIES, MODELS
from app.services.utility_tools import UTILITY_TOOLS

router = APIRouter(prefix="/api", tags=["models"])


@router.get("/categories", response_model=list[CategorySpec])
def list_categories():
    utility_category = CategorySpec(
        id="utility",
        label="Utility",
        description="Local orchestration nodes for prompts, assets, comparison, variants, and export.",
        recommended_for_mvp=True,
        node_types=[tool.node_type for tool in UTILITY_TOOLS],
        node_type=UTILITY_TOOLS[0].node_type,
    )
    return [*CATEGORIES, utility_category]


@router.get("/models", response_model=list[ModelSpec])
def list_models(enabled_only: bool = False):
    models = [*MODELS, *UTILITY_TOOLS]
    if enabled_only:
        return [model for model in models if model.enabled]
    return models


@router.get("/tools", response_model=list[ModelSpec])
def list_tools():
    return UTILITY_TOOLS
