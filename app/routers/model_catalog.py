from fastapi import APIRouter, HTTPException

from app.schemas import CatalogModelSpec
from app.services.model_catalog import (
    CHEAPEST_MODEL_BY_NODE_TYPE,
    get_catalog_entry,
    list_catalog_entries,
)

router = APIRouter(prefix="/api/model-catalog", tags=["model catalog"])


@router.get("", response_model=list[CatalogModelSpec])
def list_model_catalog():
    return list_catalog_entries()


@router.get("/cheapest")
def cheapest_model_catalog():
    catalog_by_node_type = {entry.node_type: entry for entry in list_catalog_entries()}
    return {
        "models": {
            node_type: cheapest_model_entry(node_type, model_id, catalog_by_node_type.get(node_type))
            for node_type, model_id in CHEAPEST_MODEL_BY_NODE_TYPE.items()
        }
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
