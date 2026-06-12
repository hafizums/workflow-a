from __future__ import annotations

from dataclasses import dataclass

from app.schemas import AssetKind, CategorySpec, CostMetadata, ModelField, ModelSpec, NodeType
from app.services.model_catalog import list_catalog_entries

# Only enable model IDs after verifying the WaveSpeed model page and request fields.
# Verified for MVP execution:
# - wavespeed-ai/z-image/turbo
# - wavespeed-ai/z-image-turbo/image-to-image

CATEGORY_ORDER = ["image", "video", "audio", "avatar", "3d"]

CATEGORY_METADATA: dict[str, dict[str, object]] = {
    "image": {
        "label": "Image",
        "description": "Generate, remix, and transform still images.",
        "recommended_for_mvp": True,
    },
    "video": {
        "label": "Video",
        "description": "Create, extend, and transform video clips.",
        "recommended_for_mvp": False,
    },
    "audio": {
        "label": "Audio",
        "description": "Generate or transcribe speech, audio, and sound.",
        "recommended_for_mvp": False,
    },
    "avatar": {
        "label": "Avatar",
        "description": "Create talking avatar and portrait-driven media.",
        "recommended_for_mvp": False,
    },
    "3d": {
        "label": "3D",
        "description": "Generate 3D assets from text or images.",
        "recommended_for_mvp": False,
    },
}

VERIFIED_FIELDS_BY_NODE_TYPE: dict[NodeType, list[ModelField]] = {
    NodeType.text_to_image: [
        ModelField(name="prompt", type="string", required=True, description="Image prompt."),
        ModelField(
            name="size",
            type="string",
            required=False,
            default="1024*1024",
            description="Output size, for example 1024*1024.",
        ),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
        ModelField(name="output_format", type="string", required=False, default="jpeg", description="jpeg, png, or webp."),
    ],
    NodeType.image_to_image: [
        ModelField(name="prompt", type="string", required=True, description="Transformation prompt."),
        ModelField(name="image", type="string", required=True, description="Public URL or WaveSpeed uploaded URL."),
        ModelField(name="size", type="string", required=False, default="1024*1024", description="Output size."),
        ModelField(
            name="strength",
            type="number",
            required=False,
            default=0.6,
            description="0.0 preserves more, 1.0 changes more.",
        ),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
        ModelField(name="output_format", type="string", required=False, default="jpeg", description="jpeg, png, or webp."),
    ],
    NodeType.upscale_image: [
        ModelField(name="image", type="asset_url", required=True, description="Source image asset, public URL, or WaveSpeed URL."),
        ModelField(
            name="target_resolution",
            type="string",
            required=False,
            default="4k",
            description="Target resolution verified by WaveSpeed docs, for example 2k or 4k.",
        ),
        ModelField(name="output_format", type="string", required=False, default="jpeg", description="jpeg, png, or webp."),
    ],
    NodeType.remove_background: [
        ModelField(name="image", type="asset_url", required=True, description="Source image asset, public URL, or WaveSpeed URL."),
    ],
    NodeType.image_to_video: [
        ModelField(name="image", type="asset_url", required=True, description="Source image asset, public URL, or WaveSpeed URL."),
        ModelField(name="prompt", type="string", required=True, description="Motion prompt."),
        ModelField(name="negative_prompt", type="string", required=False, default="", description="Optional negative prompt."),
        ModelField(name="duration", type="integer", required=False, default=5, description="Video duration in seconds."),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
        ModelField(name="last_image", type="asset_url", required=False, default="", description="Optional final image for start-end motion."),
    ],
    NodeType.text_to_speech: [
        ModelField(name="text", type="textarea", required=True, description="Text to speak."),
        ModelField(name="language", type="string", required=False, default="auto", description="Language code or auto."),
        ModelField(name="voice", type="string", required=False, default="Vivian", description="Voice name."),
        ModelField(name="style_instruction", type="string", required=False, default="", description="Optional speaking style instruction."),
    ],
}


def _exposed_catalog_entries():
    return [
        entry
        for entry in list_catalog_entries()
        if entry.category in CATEGORY_METADATA and entry.node_type != NodeType.generic_wavespeed.value
    ]


def _node_type(value: str) -> NodeType:
    return NodeType(value)


def _output_kind(value: str) -> AssetKind:
    return AssetKind(value)


def _registry_model_id(node_type: NodeType, category: str, default_model_id: str | None, enabled: bool) -> str:
    if enabled and default_model_id:
        return default_model_id
    return f"planned/{category}/{node_type.value}"


def _catalog_entry_to_model(entry) -> ModelSpec:
    node_type = _node_type(entry.node_type)
    cost = CostMetadata(
        estimated_base_cost_usd=entry.estimated_base_cost_usd,
        cost_unit=entry.cost_unit,
        pricing_note=entry.pricing_note,
    )
    return ModelSpec(
        id=_registry_model_id(node_type, entry.category, entry.default_model_id, entry.enabled),
        label=entry.display_name,
        node_type=node_type,
        category=entry.category,
        output_kind=_output_kind(entry.output_kind),
        enabled=entry.enabled,
        description=entry.description or "",
        fields=VERIFIED_FIELDS_BY_NODE_TYPE.get(node_type, []) if entry.enabled else [],
        default_model_id=entry.default_model_id,
        display_name=entry.display_name,
        estimated_base_cost_usd=entry.estimated_base_cost_usd,
        cost_unit=entry.cost_unit,
        pricing_note=entry.pricing_note,
        cost=cost,
        docs_url=entry.docs_url,
        verification_status=entry.verification_status,
        enabled_reason=entry.enabled_reason,
    )


def _build_categories() -> list[CategorySpec]:
    entries = _exposed_catalog_entries()
    categories: list[CategorySpec] = []
    for category_id in CATEGORY_ORDER:
        node_types = [_node_type(entry.node_type) for entry in entries if entry.category == category_id]
        if not node_types:
            continue
        metadata = CATEGORY_METADATA[category_id]
        categories.append(
            CategorySpec(
                id=category_id,
                label=str(metadata["label"]),
                description=str(metadata["description"]),
                recommended_for_mvp=bool(metadata["recommended_for_mvp"]),
                node_types=node_types,
                node_type=node_types[0],
            )
        )
    return categories


CATEGORIES: list[CategorySpec] = _build_categories()
MODELS: list[ModelSpec] = [_catalog_entry_to_model(entry) for entry in _exposed_catalog_entries()]


@dataclass(frozen=True)
class ModelResolution:
    model: ModelSpec | None
    model_id: str | None
    source: str
    error: str | None = None


def get_model(model_id: str) -> ModelSpec | None:
    return next((model for model in MODELS if model.id == model_id), None)


def get_model_for_node(node_type: NodeType, model_id: str) -> ModelSpec | None:
    return next(
        (
            model
            for model in MODELS
            if model.node_type == node_type and model_id in {model.id, model.default_model_id}
        ),
        None,
    )


def default_model_for_node_type(node_type: NodeType) -> ModelSpec | None:
    return next((model for model in MODELS if model.node_type == node_type), None)


def resolve_model_for_node(
    node_type: NodeType,
    node_model_id: str | None = None,
    project_model_overrides: dict[str, str] | None = None,
) -> ModelResolution:
    model_overrides = project_model_overrides or {}
    override_model_id = model_overrides.get(node_type.value)

    if node_model_id:
        model_id = node_model_id
        source = "node"
    elif override_model_id:
        model_id = override_model_id
        source = "project"
    else:
        default_model = default_model_for_node_type(node_type)
        if default_model is None:
            return ModelResolution(
                model=None,
                model_id=None,
                source="catalog",
                error=f"No catalog default model is registered for node type {node_type.value}.",
            )
        model_id = default_model.default_model_id or default_model.id
        source = "catalog"

    if model_id.startswith("TODO_"):
        return ModelResolution(
            model=None,
            model_id=model_id,
            source=source,
            error="Replace the placeholder model_id with a verified WaveSpeed model ID.",
        )

    model = get_model_for_node(node_type, model_id)
    if model is None:
        return ModelResolution(
            model=None,
            model_id=model_id,
            source=source,
            error=f"Model {model_id} is not registered for node type {node_type.value}.",
        )

    return ModelResolution(model=model, model_id=model.default_model_id or model.id, source=source)
