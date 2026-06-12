from __future__ import annotations

from dataclasses import dataclass

from app.schemas import AssetKind, CategorySpec, CostMetadata, ModelField, ModelSpec, NodeType
from app.services.model_catalog import list_catalog_entries

# Only enable model IDs after verifying the WaveSpeed model page, request fields,
# and matching node-runner preparer.

CATEGORY_ORDER = ["input", "image", "video", "audio", "avatar", "3d", "llm"]

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
}

VERIFIED_FIELDS_BY_NODE_TYPE: dict[NodeType, list[ModelField]] = {
    NodeType.text_to_image: [
        ModelField(name="prompt", type="textarea", required=True, description="Image prompt."),
        ModelField(
            name="size",
            type="string",
            required=False,
            default="1024*1024",
            description="Output size, for example 1024*1024.",
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
            options=["2k", "4k"],
            description="Target resolution verified by WaveSpeed docs, for example 2k or 4k.",
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
        ModelField(name="size", type="select", required=False, default="1280*720", options=["1280*720", "720*1280"], description="Output size."),
        ModelField(name="duration", type="select", required=False, default=5, options=[5, 10], description="Video duration in seconds."),
        ModelField(name="shot_type", type="select", required=False, default="simple", options=["simple", "complex"], description="Shot complexity."),
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
        ModelField(name="duration", type="integer", required=False, default=5, min_value=1, max_value=7, step=1, description="Extension duration in seconds."),
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
