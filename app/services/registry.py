from __future__ import annotations

from dataclasses import dataclass

from app.schemas import AssetKind, CategorySpec, CostMetadata, ModelField, ModelSpec, NodeType, WaveSpeedCatalogField, WaveSpeedCatalogModel
from app.services import catalog_repository
from app.services.model_catalog import list_catalog_entries

# Only enable model IDs after verifying the WaveSpeed model page, request fields,
# and matching node-runner preparer.

CATEGORY_ORDER = ["input", "image", "video", "audio", "avatar", "3d", "llm", "training", "moderation", "other"]

CATEGORY_METADATA: dict[str, dict[str, object]] = {
    "input": {
        "label": "Input",
        "description": "Upload or select local project assets.",
        "recommended_for_mvp": True,
    },
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
    "llm": {
        "label": "LLM",
        "description": "Generate text and image-aware text responses with WaveSpeed LLM models.",
        "recommended_for_mvp": True,
    },
    "training": {
        "label": "Training",
        "description": "WaveSpeed training and fine-tuning catalog models.",
        "recommended_for_mvp": False,
    },
    "moderation": {
        "label": "Moderation",
        "description": "WaveSpeed moderation and safety catalog models.",
        "recommended_for_mvp": False,
    },
    "other": {
        "label": "Other",
        "description": "Additional WaveSpeed catalog models.",
        "recommended_for_mvp": False,
    },
}

VERIFIED_FIELDS_BY_NODE_TYPE: dict[NodeType, list[ModelField]] = {
    NodeType.text_to_image: [
        ModelField(name="prompt", type="textarea", required=True, description="Image prompt."),
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=False,
            default="",
            accept="image/*",
            description="Optional source image supported by wavespeed-ai/z-image/turbo.",
        ),
        ModelField(
            name="size",
            type="string",
            required=False,
            default="1024*1024",
            description="Output size, for example 1024*1024.",
        ),
        ModelField(
            name="strength",
            type="number",
            required=False,
            default=0.6,
            min_value=0,
            max_value=1,
            step=0.05,
            description="Optional source-image transformation strength.",
        ),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
        ModelField(
            name="output_format",
            type="select",
            required=False,
            default="jpeg",
            options=["jpeg", "png", "webp"],
            description="Output format.",
        ),
    ],
    NodeType.image_to_image: [
        ModelField(name="prompt", type="textarea", required=True, description="Transformation prompt."),
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Source image asset, public URL, or WaveSpeed URL.",
        ),
        ModelField(name="size", type="string", required=False, default="1024*1024", description="Output size."),
        ModelField(
            name="strength",
            type="number",
            required=False,
            default=0.6,
            min_value=0,
            max_value=1,
            step=0.05,
            description="0.0 preserves more, 1.0 changes more.",
        ),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
        ModelField(
            name="output_format",
            type="select",
            required=False,
            default="jpeg",
            options=["jpeg", "png", "webp"],
            description="Output format.",
        ),
    ],
    NodeType.reference_to_image: [
        ModelField(
            name="reference_image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Reference image.",
        ),
        ModelField(name="prompt", type="textarea", required=True, description="Prompt guided by the reference image."),
        ModelField(name="size", type="string", required=False, default="1024*1024", description="Output size."),
        ModelField(
            name="strength",
            type="number",
            required=False,
            default=0.6,
            min_value=0,
            max_value=1,
            step=0.05,
            description="How strongly to transform the reference.",
        ),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
        ModelField(
            name="output_format",
            type="select",
            required=False,
            default="jpeg",
            options=["jpeg", "png", "webp"],
            description="Output format.",
        ),
    ],
    NodeType.upscale_image: [
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Source image asset, public URL, or WaveSpeed URL.",
        ),
        ModelField(
            name="target_resolution",
            type="select",
            required=False,
            default="4k",
            options=["2k", "4k", "8k"],
            description="Target resolution verified by the WaveSpeed model catalog.",
        ),
        ModelField(
            name="output_format",
            type="select",
            required=False,
            default="jpeg",
            options=["jpeg", "png", "webp"],
            description="Output format.",
        ),
    ],
    NodeType.remove_background: [
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Source image asset, public URL, or WaveSpeed URL.",
        ),
    ],
    NodeType.remove_object: [
        ModelField(name="prompt", type="textarea", required=True, description="Describe what to remove, repair, or replace."),
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Source image.",
        ),
        ModelField(
            name="mask_image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Mask image where white/marked area is edited.",
        ),
        ModelField(name="size", type="string", required=False, default="1024*1024", description="Output size if supported."),
    ],
    NodeType.image_to_video: [
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Source image asset, public URL, or WaveSpeed URL.",
        ),
        ModelField(name="prompt", type="textarea", required=True, description="Motion prompt."),
        ModelField(name="negative_prompt", type="textarea", required=False, default="", description="Optional negative prompt."),
        ModelField(name="duration", type="select", required=False, default=5, options=[5, 8], description="Video duration in seconds."),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
        ModelField(
            name="last_image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=False,
            default="",
            accept="image/*",
            description="Optional final image for start-end motion.",
        ),
    ],
    NodeType.start_end_to_video: [
        ModelField(name="image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Start frame image."),
        ModelField(name="last_image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="End frame image."),
        ModelField(name="prompt", type="textarea", required=True, description="Motion prompt."),
        ModelField(name="negative_prompt", type="textarea", required=False, default="", description="Things to avoid."),
        ModelField(name="duration", type="select", required=False, default=5, options=[5, 8], description="Duration in seconds."),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
    ],
    NodeType.text_to_video: [
        ModelField(name="prompt", type="textarea", required=True, description="Video prompt."),
        ModelField(name="negative_prompt", type="textarea", required=False, default="", description="Things to avoid."),
        ModelField(
            name="size",
            type="select",
            required=False,
            default="832*480",
            options=["832*480", "480*832"],
            description="Video size.",
        ),
        ModelField(name="duration", type="select", required=False, default=5, options=[5, 8], description="Duration in seconds."),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
    ],
    NodeType.reference_to_video: [
        ModelField(
            name="reference_image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Reference image used as visual context. The runner sends this as reference_urls.",
        ),
        ModelField(name="prompt", type="textarea", required=True, description="Video prompt."),
        ModelField(name="audio", type="asset_url", asset_kind=AssetKind.audio, required=False, default="", accept="audio/*", description="Optional reference audio."),
        ModelField(name="negative_prompt", type="textarea", required=False, default="", description="Things to avoid."),
        ModelField(
            name="size",
            type="select",
            required=False,
            default="1280*720",
            options=["1280*720", "720*1280", "1920*1080", "1080*1920"],
            description="Output size.",
        ),
        ModelField(name="duration", type="select", required=False, default=5, options=[5, 10], description="Video duration in seconds."),
        ModelField(name="shot_type", type="select", required=False, default="single", options=["single", "multi"], description="Shot type."),
        ModelField(name="enable_audio", type="boolean", required=False, default=True, description="Enable generated audio."),
        ModelField(name="enable_prompt_expansion", type="boolean", required=False, default=False, description="Allow WaveSpeed prompt expansion."),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
    ],
    NodeType.video_extend: [
        ModelField(
            name="video",
            type="asset_url",
            asset_kind=AssetKind.video,
            required=True,
            accept="video/*",
            description="Source video to extend. WaveSpeed requires 4 seconds to 1 minute.",
        ),
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=False,
            default="",
            accept="image/*",
            description="Optional end-frame guidance image.",
        ),
        ModelField(name="prompt", type="textarea", required=False, default="", description="Optional text direction for the extension."),
        ModelField(name="duration", type="number", required=False, default=5, min_value=1, max_value=7, step=1, description="Extension duration in seconds."),
        ModelField(name="resolution", type="select", required=False, default="720p", options=["540p", "720p", "1080p"], description="Output resolution."),
    ],
    NodeType.video_effect: [
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=True,
            accept="image/*",
            description="Portrait or subject image for the template effect.",
        ),
        ModelField(
            name="template",
            type="select",
            required=True,
            default="tim_burton",
            options=[
                "tim_burton",
                "broomstick_fly",
                "witchy_pet",
                "pumpkin_head",
                "sexy_devil",
                "dance_with_ghost",
                "crow_arrival",
                "clown_makeup",
                "shadow_of_terror_video",
                "not_look_back_video",
                "turn_into_zombie",
                "head_to_balloon",
                "covered_liquid_metal",
                "wednesdays_vibe",
            ],
            description="Halloween style preset.",
        ),
        ModelField(name="bgm", type="boolean", required=False, default=True, description="Add background music."),
        ModelField(name="seed", type="integer", required=False, default=0, description="Seed for repeatable variants."),
    ],
    NodeType.text_to_speech: [
        ModelField(name="text", type="textarea", required=True, description="Text to speak."),
        ModelField(
            name="language",
            type="select",
            required=False,
            default="auto",
            options=["auto", "Chinese", "English", "German", "Italian", "Portuguese", "Spanish", "Japanese", "Korean", "French", "Russian"],
            description="Language.",
        ),
        ModelField(name="voice", type="string", required=False, default="Vivian", description="Voice name."),
        ModelField(name="style_instruction", type="textarea", required=False, default="", description="Optional speaking style instruction."),
    ],
    NodeType.text_to_audio: [
        ModelField(name="text", type="textarea", required=True, description="Text to generate as speech audio."),
        ModelField(
            name="language",
            type="select",
            required=False,
            default="auto",
            options=["auto", "Chinese", "English", "German", "Italian", "Portuguese", "Spanish", "Japanese", "Korean", "French", "Russian"],
            description="Language.",
        ),
        ModelField(name="voice", type="string", required=False, default="Vivian", description="Voice name."),
        ModelField(name="style_instruction", type="textarea", required=False, default="", description="Optional speaking style instruction."),
    ],
    NodeType.speech_to_text: [
        ModelField(name="audio", type="asset_url", asset_kind=AssetKind.audio, required=True, accept="audio/*", description="Audio file or public URL."),
        ModelField(name="language", type="string", required=False, default="auto", description="Language code or auto."),
        ModelField(
            name="task",
            type="select",
            required=False,
            default="transcribe",
            options=["transcribe", "translate"],
            description="Transcribe original language or translate to English.",
        ),
        ModelField(name="enable_timestamps", type="boolean", required=False, default=False, description="Generate word-level timestamps when supported."),
        ModelField(name="prompt", type="textarea", required=False, default="", description="Optional transcription guidance."),
        ModelField(name="enable_sync_mode", type="boolean", required=False, default=False, description="Use sync mode only if supported by API."),
    ],
    NodeType.generate_voice: [
        ModelField(name="text", type="textarea", required=True, description="Text to speak."),
        ModelField(name="voice_description", type="textarea", required=True, description="Natural-language voice description."),
        ModelField(
            name="language",
            type="select",
            required=False,
            default="auto",
            options=["auto", "Chinese", "English", "German", "Italian", "Portuguese", "Spanish", "Japanese", "Korean", "French", "Russian"],
            description="Language.",
        ),
    ],
    NodeType.lip_sync: [
        ModelField(name="video", type="asset_url", asset_kind=AssetKind.video, required=True, accept="video/*", description="Source talking-head video."),
        ModelField(name="audio", type="asset_url", asset_kind=AssetKind.audio, required=True, accept="audio/*", description="Speech audio."),
    ],
    NodeType.portrait_transfer: [
        ModelField(name="image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Face image."),
        ModelField(name="body_image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Target body image."),
    ],
    NodeType.talking_avatar: [
        ModelField(name="image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Person image to animate."),
        ModelField(name="audio", type="asset_url", asset_kind=AssetKind.audio, required=True, accept="audio/*", description="Speech or singing audio."),
        ModelField(name="mask_image", type="asset_url", asset_kind=AssetKind.image, required=False, accept="image/*", description="Optional mask image."),
        ModelField(name="prompt", type="textarea", required=False, default="", description="Optional expression, style, or pose guidance."),
        ModelField(name="resolution", type="select", required=False, default="480p", options=["480p", "720p"], description="Output resolution."),
        ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
    ],
    NodeType.image_to_3d: [
        ModelField(name="front_image_url", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Front view image."),
        ModelField(name="back_image_url", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Back view image."),
        ModelField(name="left_image_url", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Left view image."),
        ModelField(name="seed", type="integer", required=False, default=0, description="Seed for repeatable outputs."),
        ModelField(name="num_inference_steps", type="integer", required=False, default=50, min_value=1, step=1, description="Quality/speed trade-off."),
        ModelField(name="guidance_scale", type="number", required=False, default=7.5, step=0.1, description="Generation guidance strength."),
        ModelField(name="octree_resolution", type="select", required=False, default=256, options=[128, 256, 384, 512], description="Mesh detail level."),
        ModelField(name="textured_mesh", type="boolean", required=False, default=False, description="Generate textured mesh; costs more than white mesh."),
    ],
    NodeType.text_to_3d: [
        ModelField(name="prompt", type="textarea", required=True, description="Text description of the 3D asset."),
    ],
    NodeType.llm_text: [
        ModelField(name="text", type="textarea", required=True, description="Text prompt for the LLM."),
    ],
    NodeType.llm_vision: [
        ModelField(name="text", type="textarea", required=True, description="Text prompt for the LLM."),
        ModelField(
            name="image",
            type="asset_url",
            asset_kind=AssetKind.image,
            required=False,
            accept="image/*",
            description="Optional image context for vision-capable LLM requests.",
        ),
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
    if enabled and category == "input":
        return f"local/input/{node_type.value}"
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
        model_id=entry.default_model_id,
        primary_capability=node_type.value,
        capability_tags=[node_type.value],
        source="curated",
    )


CURATED_MODELS: list[ModelSpec] = [_catalog_entry_to_model(entry) for entry in _exposed_catalog_entries()]


def _field_from_catalog(field: WaveSpeedCatalogField) -> ModelField:
    field_type = field.type
    if field_type in {"asset_url", "file_url"} and _is_media_list_field(field.name, field.description):
        field_type = "asset_url_list"
    return ModelField(
        name=field.name,
        type=field_type,
        required=field.required,
        default=field.default,
        description=field.description,
        options=field.options,
        asset_kind=field.asset_kind,
        accept=field.accept,
        min_value=field.min_value,
        max_value=field.max_value,
    )


def _is_media_list_field(name: str, description: str | None = None) -> bool:
    value = name.lower()
    description_value = (description or "").lower()
    explicit = {
        "images",
        "image_urls",
        "source_images",
        "target_images",
        "reference_images",
        "reference_urls",
        "refer_images",
        "mask_images",
        "clothes_images",
        "videos",
        "video_urls",
        "reference_videos",
        "ref_videos",
        "audios",
        "audio_urls",
        "reference_audios",
    }
    if value in explicit:
        return True
    if value.endswith(("_images", "_videos", "_audios")):
        return True
    if value == "reference" and "reference image" in description_value:
        return True
    return False


CURATED_MODEL_IDS = {
    model_id
    for model in CURATED_MODELS
    for model_id in {model.id, model.default_model_id, model.model_id}
    if model_id
}


def _catalog_model_to_spec(model: WaveSpeedCatalogModel) -> ModelSpec:
    return ModelSpec(
        id=model.model_id,
        model_id=model.model_id,
        label=model.display_name,
        node_type=NodeType.generic_wavespeed,
        category=model.category,
        output_kind=model.output_kind,
        enabled=model.enabled and not model.excluded,
        description=model.raw_schema.get("models_full", {}).get("description") or "",
        fields=[_field_from_catalog(field) for field in model.fields if not field.disabled],
        default_model_id=model.model_id,
        display_name=model.display_name,
        estimated_base_cost_usd=model.base_price,
        cost_unit=model.pricing_basis_guess,
        pricing_note=model.pricing_text_from_description,
        cost=CostMetadata(
            estimated_base_cost_usd=model.base_price,
            cost_unit=model.pricing_basis_guess,
            pricing_note=model.pricing_text_from_description,
        ),
        docs_url=model.docs_url,
        verification_status="catalog",
        enabled_reason=model.enabled_reason,
        primary_capability=model.primary_capability,
        capability_tags=model.capability_tags,
        raw_type=model.raw_type,
        source="catalog",
        pricing_basis_guess=model.pricing_basis_guess,
        pricing_formula_raw=model.pricing_formula_raw,
        pricing_text_from_description=model.pricing_text_from_description,
        excluded=model.excluded,
        exclusion_reason=model.exclusion_reason,
    )


def _build_catalog_models() -> list[ModelSpec]:
    models: list[ModelSpec] = []
    for catalog_model in catalog_repository.list_catalog_models(include_excluded=False):
        if catalog_model.model_id in CURATED_MODEL_IDS:
            continue
        models.append(_catalog_model_to_spec(catalog_model))
    return models


CATALOG_MODELS: list[ModelSpec] = _build_catalog_models()


def _build_categories(models: list[ModelSpec]) -> list[CategorySpec]:
    categories: list[CategorySpec] = []
    for category_id in CATEGORY_ORDER:
        node_types = sorted({model.node_type for model in models if model.category == category_id}, key=lambda item: item.value)
        if not node_types:
            continue
        metadata = CATEGORY_METADATA.get(category_id, CATEGORY_METADATA["other"])
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


MODELS: list[ModelSpec] = [*CURATED_MODELS, *CATALOG_MODELS]
CATEGORIES: list[CategorySpec] = _build_categories(MODELS)


@dataclass(frozen=True)
class ModelResolution:
    model: ModelSpec | None
    model_id: str | None
    source: str
    error: str | None = None


def get_model(model_id: str) -> ModelSpec | None:
    return next((model for model in MODELS if model.id == model_id), None)


def get_model_by_id(model_id: str) -> ModelSpec | None:
    return next(
        (
            model
            for model in MODELS
            if model_id in {model.id, model.default_model_id, model.model_id}
        ),
        None,
    )


def get_model_for_node(node_type: NodeType, model_id: str) -> ModelSpec | None:
    exact = get_model_by_id(model_id)
    if exact and (exact.node_type == node_type or node_type == NodeType.generic_wavespeed or exact.source == "catalog"):
        return exact
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


def get_models_for_capability(capability: str) -> list[ModelSpec]:
    return [
        model
        for model in MODELS
        if model.enabled and (model.primary_capability == capability or capability in model.capability_tags)
    ]


def get_compatible_models(
    model_or_node,
    output_kind: AssetKind | None = None,
    capability: str | None = None,
) -> list[ModelSpec]:
    if isinstance(model_or_node, ModelSpec):
        base_output = output_kind or model_or_node.output_kind
        base_capability = capability or model_or_node.primary_capability
    else:
        base_model = default_model_for_node_type(model_or_node.type)
        base_output = output_kind or (base_model.output_kind if base_model else None)
        base_capability = capability or (base_model.primary_capability if base_model else None)
    return [
        model
        for model in MODELS
        if model.enabled
        and (base_output is None or model.output_kind == base_output)
        and (base_capability is None or model.primary_capability == base_capability or base_capability in model.capability_tags)
    ]


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
        if node_type == NodeType.generic_wavespeed:
            return ModelResolution(
                model=None,
                model_id=None,
                source="catalog",
                error="generic_wavespeed nodes require an explicit WaveSpeed model_id.",
            )
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

    return ModelResolution(model=model, model_id=model.model_id or model.default_model_id or model.id, source=source)
