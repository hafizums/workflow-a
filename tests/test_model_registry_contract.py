from collections import Counter

import pytest

from app.schemas import NodeType
from app.services.model_catalog import list_catalog_entries
from app.services.node_runner import PREPARERS_BY_NODE_TYPE
from app.services.registry import MODELS, get_model_for_node


def catalog_audit() -> dict:
    entries = list_catalog_entries()
    enabled = [entry for entry in entries if entry.enabled]
    disabled = [entry for entry in entries if not entry.enabled]
    enabled_without_fields = [
        model
        for model in MODELS
        if model.enabled and model.node_type != NodeType.upload_image and not model.fields
    ]
    enabled_without_preparer = [
        model
        for model in MODELS
        if model.enabled
        and model.node_type != NodeType.upload_image
        and model.source != "catalog"
        and model.node_type not in PREPARERS_BY_NODE_TYPE
    ]
    return {
        "total": len(entries),
        "enabled": len(enabled),
        "disabled": len(disabled),
        "disabled_by_status": Counter(entry.verification_status for entry in disabled),
        "enabled_without_fields": enabled_without_fields,
        "enabled_without_preparer": enabled_without_preparer,
    }


def test_model_catalog_audit_prints_and_blocks_missing_contracts():
    audit = catalog_audit()
    print(
        {
            "total": audit["total"],
            "enabled": audit["enabled"],
            "disabled": audit["disabled"],
            "disabled_by_status": dict(audit["disabled_by_status"]),
            "enabled_without_fields": [model.id for model in audit["enabled_without_fields"]],
            "enabled_without_preparer": [model.id for model in audit["enabled_without_preparer"]],
        }
    )
    assert not audit["enabled_without_fields"]
    assert not audit["enabled_without_preparer"]


def test_enabled_wavespeed_models_have_metadata_fields_and_preparers():
    for model in MODELS:
        if not model.enabled or model.node_type == NodeType.upload_image:
            continue
        assert model.default_model_id, model.id
        assert model.docs_url, model.id
        assert model.verification_status in {"verified", "catalog"}, model.id
        assert model.enabled_reason, model.id
        assert model.estimated_base_cost_usd is not None or "unknown" in (model.enabled_reason or "").lower()
        assert model.fields, model.id
        assert model.source == "catalog" or model.node_type in PREPARERS_BY_NODE_TYPE, model.id
        for field in model.fields:
            if field.type == "asset_url":
                assert field.asset_kind is not None, f"{model.id}:{field.name}"
            if field.type == "select":
                assert field.options, f"{model.id}:{field.name}"


def test_every_catalog_default_model_resolves_through_registry():
    for entry in list_catalog_entries():
        if entry.node_type == NodeType.generic_wavespeed.value or not entry.default_model_id:
            continue
        resolved = get_model_for_node(NodeType(entry.node_type), entry.default_model_id)
        assert resolved is not None, entry.default_model_id


def test_priority_v9_models_are_enabled():
    enabled_node_types = {model.node_type for model in MODELS if model.enabled}
    for node_type in {
        NodeType.start_end_to_video,
        NodeType.text_to_video,
        NodeType.text_to_audio,
        NodeType.speech_to_text,
        NodeType.generate_voice,
        NodeType.lip_sync,
        NodeType.talking_avatar,
        NodeType.portrait_transfer,
        NodeType.image_to_3d,
        NodeType.text_to_3d,
        NodeType.remove_object,
        NodeType.reference_to_image,
        NodeType.reference_to_video,
        NodeType.video_extend,
        NodeType.video_effect,
    }:
        assert node_type in enabled_node_types


def test_no_user_facing_catalog_models_remain_disabled():
    disabled = [model for model in MODELS if not model.enabled]
    assert disabled == []
