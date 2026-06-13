from app.services import catalog_repository


def test_repository_loads_models_capabilities_and_fields():
    models = catalog_repository.list_catalog_models()
    assert len(models) >= 900
    model = catalog_repository.get_catalog_model("wavespeed-ai/z-image/turbo")
    assert model is not None
    assert model.primary_capability
    assert model.category
    assert model.output_kind
    assert model.fields
    assert "prompt" in {field.name for field in model.fields}
    assert len(catalog_repository.list_capabilities()) >= 50


def test_repository_cheapest_by_capability():
    model = catalog_repository.get_cheapest_model_for_capability("text_to_image")
    assert model is not None
    assert "text_to_image" in {model.primary_capability, *model.capability_tags}
