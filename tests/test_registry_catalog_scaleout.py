from app.schemas import NodeType
from app.services.registry import MODELS, get_model_by_id, get_models_for_capability, resolve_model_for_node


def test_registry_includes_catalog_and_curated_models():
    assert len(MODELS) >= 900
    curated = get_model_by_id("wavespeed-ai/z-image/turbo")
    generic = get_model_by_id("alibaba/happyhorse-1.0/text-to-video")
    assert curated is not None
    assert curated.source == "curated"
    assert generic is not None
    assert generic.source == "catalog"
    assert generic.node_type == NodeType.generic_wavespeed


def test_generic_model_resolves_by_exact_model_id():
    resolution = resolve_model_for_node(NodeType.generic_wavespeed, "alibaba/happyhorse-1.0/text-to-video")
    assert resolution.error is None
    assert resolution.model_id == "alibaba/happyhorse-1.0/text-to-video"
    assert resolution.model.source == "catalog"


def test_models_for_capability():
    models = get_models_for_capability("text_to_image")
    assert len(models) >= 100
    assert all(model.enabled for model in models)
