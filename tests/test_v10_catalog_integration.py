from app.schemas import CanvasNode, NodeType, VariantRunRequest
from app.services.registry import MODELS, get_model_by_id
from app.services.tool_compatibility import can_compare_models, compatible_models_for_node
from app.services.variant_runner import build_variant_payloads


def test_comparison_finds_catalog_models_by_capability():
    node = CanvasNode(
        type=NodeType.generic_wavespeed,
        title="Catalog T2V",
        model_id="alibaba/happyhorse-1.0/text-to-video",
        inputs={"prompt": "product reveal", "duration": 5, "resolution": "720p"},
    )
    compatible = compatible_models_for_node(node, MODELS)
    assert len(compatible) >= 2
    ok, message = can_compare_models(compatible[:2])
    assert ok, message


def test_variants_clone_generic_catalog_node_inputs():
    node = CanvasNode(
        type=NodeType.generic_wavespeed,
        title="Catalog T2V",
        model_id="alibaba/happyhorse-1.0/text-to-video",
        inputs={"prompt": "product reveal", "seed": 1},
    )
    payloads = build_variant_payloads(node, VariantRunRequest(project_id="project_abc123abc123", node_id=node.id, variant_count=3))
    assert [payload["seed"] for payload in payloads] == [1, 2, 3]
    assert get_model_by_id(node.model_id).source == "catalog"
