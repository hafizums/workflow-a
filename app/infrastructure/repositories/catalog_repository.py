from __future__ import annotations

from app.services import catalog_repository


class CatalogRepository:
    """Catalog repository adapter backed by the existing catalog service."""

    def summary(self, include_excluded: bool = False):
        models = catalog_repository.list_catalog_models(include_excluded=include_excluded)
        return {
            "model_count": len(models),
            "capabilities": catalog_repository.list_capabilities(),
            "cheapest_by_capability": catalog_repository.list_cheapest_by_capability(),
        }

    def list(self, include_excluded: bool = False):
        return catalog_repository.list_catalog_models(include_excluded=include_excluded)

    def get(self, model_id: str):
        return catalog_repository.get_catalog_model(model_id)

    def schema(self, model_id: str):
        return catalog_repository.get_model_fields(model_id)

    def capabilities(self):
        return catalog_repository.list_capabilities()

    def cheapest(self):
        return catalog_repository.list_cheapest_by_capability()

    def excluded(self):
        return [model for model in catalog_repository.list_catalog_models(include_excluded=True) if model.excluded]

