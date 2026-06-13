from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas import WaveSpeedCatalogField, WaveSpeedCatalogModel

ROOT_DIR = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT_DIR / "app" / "data" / "wavespeed_catalog.normalized.json"
EXCLUSIONS_PATH = ROOT_DIR / "app" / "data" / "model_exclusions.json"


@lru_cache(maxsize=1)
def load_catalog_payload() -> dict[str, Any]:
    if not CATALOG_PATH.exists():
        return {
            "schema_name": "wavespeed_catalog_normalized",
            "version": 1,
            "counts": {"models": 0, "schema_fields": 0, "capabilities": 0, "cheapest_by_capability": 0},
            "capabilities": [],
            "cheapest_by_capability": [],
            "models": [],
        }
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    exclusions = load_exclusions()
    models = []
    for raw_model in payload.get("models", []):
        model = dict(raw_model)
        exclusion = exclusions.get(model.get("model_id"))
        if exclusion:
            model["excluded"] = bool(exclusion.get("excluded", True))
            model["exclusion_reason"] = str(exclusion.get("reason") or model.get("exclusion_reason") or "")
            model["enabled"] = False
            model["enabled_reason"] = "Excluded from generic runtime"
        models.append(model)
    return {**payload, "models": models}


@lru_cache(maxsize=1)
def load_exclusions() -> dict[str, dict[str, Any]]:
    if not EXCLUSIONS_PATH.exists():
        return {}
    raw = json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8"))
    records = raw.get("models", []) if isinstance(raw, dict) else raw
    return {str(item.get("model_id")): item for item in records if isinstance(item, dict) and item.get("model_id")}


def clear_catalog_cache() -> None:
    load_catalog_payload.cache_clear()
    load_exclusions.cache_clear()


def list_catalog_models(include_excluded: bool = False) -> list[WaveSpeedCatalogModel]:
    models = [WaveSpeedCatalogModel.model_validate(item) for item in load_catalog_payload().get("models", [])]
    if include_excluded:
        return models
    return [model for model in models if not model.excluded]


def get_catalog_model(model_id: str) -> WaveSpeedCatalogModel | None:
    return next((model for model in list_catalog_models(include_excluded=True) if model.model_id == model_id), None)


def list_capabilities() -> list[dict[str, Any]]:
    return list(load_catalog_payload().get("capabilities", []))


def list_cheapest_by_capability() -> list[dict[str, Any]]:
    return list(load_catalog_payload().get("cheapest_by_capability", []))


def list_models_by_capability(capability: str, include_excluded: bool = False) -> list[WaveSpeedCatalogModel]:
    return [
        model
        for model in list_catalog_models(include_excluded=include_excluded)
        if capability == model.primary_capability or capability in model.capability_tags
    ]


def list_models_by_category(category: str, include_excluded: bool = False) -> list[WaveSpeedCatalogModel]:
    return [model for model in list_catalog_models(include_excluded=include_excluded) if model.category == category]


def get_default_model_for_capability(capability: str) -> WaveSpeedCatalogModel | None:
    models = list_models_by_capability(capability)
    if not models:
        return None
    return sorted(models, key=lambda model: (model.sort_order, model.base_price is None, model.base_price or 0, model.model_id))[0]


def get_cheapest_model_for_capability(capability: str) -> WaveSpeedCatalogModel | None:
    cheapest_rows = [row for row in list_cheapest_by_capability() if row.get("capability") == capability]
    for row in sorted(cheapest_rows, key=lambda item: item.get("rank_in_capability") or 999999):
        model = get_catalog_model(str(row.get("model_id") or ""))
        if model and not model.excluded:
            return model
    models = [model for model in list_models_by_capability(capability) if model.base_price is not None]
    if not models:
        return get_default_model_for_capability(capability)
    return sorted(models, key=lambda model: (model.base_price or 0, model.sort_order, model.model_id))[0]


def get_model_fields(model_id: str) -> list[WaveSpeedCatalogField]:
    model = get_catalog_model(model_id)
    return model.fields if model else []


def summary() -> dict[str, Any]:
    payload = load_catalog_payload()
    models = list_catalog_models(include_excluded=True)
    return {
        "counts": payload.get("counts", {}),
        "visible_model_count": len([model for model in models if not model.excluded]),
        "excluded_model_count": len([model for model in models if model.excluded]),
        "categories": sorted({model.category for model in models}),
        "capability_count": len(list_capabilities()),
    }
