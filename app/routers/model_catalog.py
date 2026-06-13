from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas import CatalogModelSpec, WaveSpeedCatalogField, WaveSpeedCatalogModel
from app.services import catalog_repository
from app.services.model_catalog import CHEAPEST_MODEL_BY_NODE_TYPE, get_catalog_entry, list_catalog_entries

router = APIRouter(prefix="/api/model-catalog", tags=["model catalog"])


@router.get("", response_model=list[WaveSpeedCatalogModel])
def list_model_catalog(
    include_excluded: bool = False,
    category: str | None = None,
    capability: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    models = catalog_repository.list_catalog_models(include_excluded=include_excluded)
    if category:
        models = [model for model in models if model.category == category]
    if capability:
        models = [
            model
            for model in models
            if capability == model.primary_capability or capability in model.capability_tags
        ]
    if q:
        needle = q.lower()
        models = [
            model
            for model in models
            if needle in model.model_id.lower()
            or needle in model.display_name.lower()
            or needle in (model.provider or "").lower()
            or needle in (model.raw_type or "").lower()
            or needle in model.primary_capability.lower()
            or any(needle in tag.lower() for tag in model.capability_tags)
        ]
    return models[offset : offset + limit]


@router.get("/summary")
def catalog_summary():
    return catalog_repository.summary()


@router.get("/capabilities")
def list_capabilities():
    return catalog_repository.list_capabilities()


@router.get("/capabilities/{capability}", response_model=list[WaveSpeedCatalogModel])
def list_capability_models(capability: str, include_excluded: bool = False):
    return catalog_repository.list_models_by_capability(capability, include_excluded=include_excluded)


@router.get("/models/{model_id:path}/schema", response_model=list[WaveSpeedCatalogField])
def get_catalog_model_schema(model_id: str):
    model = catalog_repository.get_catalog_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown WaveSpeed catalog model: {model_id}")
    return model.fields


@router.get("/models/{model_id:path}", response_model=WaveSpeedCatalogModel)
def get_catalog_model(model_id: str):
    model = catalog_repository.get_catalog_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown WaveSpeed catalog model: {model_id}")
    return model


@router.get("/categories/{category}", response_model=list[WaveSpeedCatalogModel])
def list_category_models(category: str, include_excluded: bool = False):
    return catalog_repository.list_models_by_category(category, include_excluded=include_excluded)


@router.get("/cheapest-by-capability")
def cheapest_by_capability():
    return {"models": catalog_repository.list_cheapest_by_capability()}


@router.get("/excluded", response_model=list[WaveSpeedCatalogModel])
def excluded_models():
    return [model for model in catalog_repository.list_catalog_models(include_excluded=True) if model.excluded]


@router.get("/cheapest")
def cheapest_model_catalog():
    catalog_by_node_type = {entry.node_type: entry for entry in list_catalog_entries()}
    cheapest_by_capability = {
        row.get("capability"): row
        for row in catalog_repository.list_cheapest_by_capability()
        if row.get("rank_in_capability") == 1
    }
    return {
        "models": {
            node_type: cheapest_model_entry(node_type, model_id, catalog_by_node_type.get(node_type))
            for node_type, model_id in CHEAPEST_MODEL_BY_NODE_TYPE.items()
        },
        "cheapest_by_capability": cheapest_by_capability,
    }


def cheapest_model_entry(node_type: str, model_id: str, entry: CatalogModelSpec | None):
    if entry is None:
        return {
            "node_type": node_type,
            "model_id": model_id,
            "estimated_base_cost_usd": None,
            "cost_unit": None,
            "pricing_note": None,
            "verification_status": "disabled",
            "enabled": False,
            "enabled_reason": "Catalog entry not found.",
        }
    return {
        "node_type": node_type,
        "model_id": model_id,
        "estimated_base_cost_usd": entry.estimated_base_cost_usd,
        "cost_unit": entry.cost_unit,
        "pricing_note": entry.pricing_note,
        "verification_status": entry.verification_status,
        "enabled": entry.enabled,
        "enabled_reason": entry.enabled_reason,
    }


@router.get("/{node_type}", response_model=CatalogModelSpec)
def get_model_catalog_entry(node_type: str):
    entry = get_catalog_entry(node_type)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown model catalog node type: {node_type}")
    return entry
