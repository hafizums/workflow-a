from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.schemas import ArtifactRole, Asset, AssetKind, CanvasNode, NodeStatus, NodeType, Project
from app.services import project_store
from app.services import catalog_repository
from app.services.model_input_resolver import prepare_model_inputs
from app.services.model_output_normalizer import normalize_model_output
from app.services.registry import get_model_by_id, get_model_for_node
from app.services.wavespeed_adapter import WaveSpeedAdapter

GENERATE_IMAGE_MODEL_ID = "wavespeed-ai/z-image/turbo"
REMIX_IMAGE_MODEL_ID = "wavespeed-ai/z-image-turbo/image-to-image"
UPSCALE_IMAGE_MODEL_ID = "wavespeed-ai/image-upscaler"
REMOVE_BACKGROUND_MODEL_ID = "wavespeed-ai/image-background-remover"
IMAGE_TO_VIDEO_MODEL_ID = "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast"
TEXT_TO_SPEECH_MODEL_ID = "wavespeed-ai/qwen3-tts/text-to-speech"
DEEPSEEK_V4_FLASH_MODEL_ID = "deepseek/deepseek-v4-flash"
GPT_5_NANO_MODEL_ID = "openai/gpt-5-nano"
PROMPT_OPTIMIZER_MODEL_ID = "wavespeed-ai/prompt-optimizer"
PROMPT_OPTIMIZER_INPUT_KEYS = {
    "use_prompt_optimizer",
    "prompt_optimizer_style",
    "prompt_optimizer_mode",
}

DENYLISTED_MODEL_IDS: dict[str, str] = {}
Preparer = Callable[[WaveSpeedAdapter, dict[str, Any], Project | None], Awaitable[dict[str, Any]]]


class NodeRunError(Exception):
    pass


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_wavespeed_node(
    adapter: WaveSpeedAdapter,
    model_id: str,
    node_type: NodeType,
    inputs: dict[str, Any],
    project: Project | None = None,
    target_node: CanvasNode | None = None,
) -> tuple[dict[str, Any], list[str], list[Asset]]:
    model_spec = get_model_for_node(node_type, model_id) or get_model_by_id(model_id)
    if model_spec is None:
        raise NodeRunError(f"Model {model_id} is not registered for node type {node_type.value}.")
    if not model_spec.enabled:
        raise NodeRunError(f"Model is disabled in the registry: {model_id}")
    denylist = current_denylist()
    if model_id in denylist:
        raise NodeRunError(f"Model is denylisted: {denylist[model_id]}")

    preparer = PREPARERS_BY_NODE_TYPE.get(node_type)
    use_generic_resolver = node_type == NodeType.generic_wavespeed or model_spec.source == "catalog" or preparer is None
    if use_generic_resolver:
        prepared_inputs = await prepare_model_inputs(
            adapter=adapter,
            model=model_spec,
            inputs=dict(inputs),
            project=project,
        )
    elif preparer is None:
        raise NodeRunError(f"No runner preparer is registered for node type {node_type.value}.")
    else:
        prepared_inputs = await preparer(adapter, dict(inputs), project)
    prepared_inputs, optimizer_metadata = await maybe_optimize_prompt(
        adapter=adapter,
        inputs=prepared_inputs,
        node_type=node_type,
    )

    if node_type in {NodeType.llm_text, NodeType.llm_vision}:
        raw_output = await adapter.run_llm_chat(model_id, prepared_inputs)
    else:
        raw_output = await adapter.run_model(model_id, prepared_inputs)
    if optimizer_metadata:
        raw_output = {**raw_output, "_prompt_optimizer": optimizer_metadata}
    output_urls, output_assets, text_output, structured_output = normalize_model_output(
        model=model_spec,
        model_id=model_id,
        raw_output=raw_output,
        target_node=target_node,
    )
    if not output_urls and not text_output and not structured_output:
        raise NodeRunError("WaveSpeed response did not include output URLs, text output, or structured output.")

    if target_node:
        if text_output:
            target_node.last_run = {**target_node.last_run, "text_output": text_output}
        if structured_output:
            target_node.last_run = {**target_node.last_run, "structured_output": structured_output}
    return raw_output, output_urls, output_assets


def current_denylist() -> dict[str, str]:
    denylist = dict(DENYLISTED_MODEL_IDS)
    for model_id, item in catalog_repository.load_exclusions().items():
        if item.get("excluded", True):
            denylist[model_id] = str(item.get("reason") or "Excluded by model_exclusions.json")
    return denylist


def build_output_asset(
    model_id: str,
    output_kind,
    output_url: str,
    output_index: int,
    raw_output: dict[str, Any],
    target_node: CanvasNode | None = None,
) -> Asset:
    return Asset(
        kind=output_kind,
        filename=output_filename(model_id, output_url, output_index),
        public_url=output_url,
        lineage={
            "source_project_id": None,
            "source_node_id": target_node.id if target_node else None,
            "source_run_id": None,
            "source_job_id": None,
            "source_model_id": model_id,
            "source_artifact_ids": list(target_node.output_asset_ids or []) if target_node else [],
            "source_input_keys": dict(target_node.inputs or {}) if target_node else {},
            "created_by": "wavespeed",
        },
        view={"role": ArtifactRole.output.value},
        metadata={
            "source_model_id": model_id,
            "source_node_id": target_node.id if target_node else None,
            "raw_output": raw_output,
        },
    )


def output_filename(model_id: str, output_url: str, output_index: int) -> str:
    suffix = url_suffix(output_url)
    stem = model_id.split("/")[-1]
    return f"{stem}-{output_index + 1}{suffix}"


def url_suffix(url: str) -> str:
    clean_url = urlparse(url).path.lower()
    for suffix in (
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".mp4",
        ".mov",
        ".webm",
        ".mkv",
        ".mp3",
        ".wav",
        ".m4a",
        ".ogg",
        ".flac",
        ".glb",
        ".gltf",
        ".obj",
        ".fbx",
        ".stl",
        ".usdz",
        ".zip",
        ".txt",
        ".json",
        ".srt",
        ".vtt",
    ):
        if clean_url.endswith(suffix):
            return suffix
    return ""


def resolve_asset_kind_from_url(url: str) -> AssetKind:
    suffix = url_suffix(url)
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return AssetKind.image
    if suffix in {".mp4", ".mov", ".webm", ".mkv"}:
        return AssetKind.video
    if suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        return AssetKind.audio
    return AssetKind.other


async def prepare_inputs(
    adapter: WaveSpeedAdapter,
    model_id: str,
    node_type_or_inputs: NodeType | dict[str, Any],
    inputs_or_project: dict[str, Any] | Project | None = None,
    project: Project | None = None,
) -> dict[str, Any]:
    if isinstance(node_type_or_inputs, dict):
        node_type = node_type_for_model_id(model_id)
        inputs = node_type_or_inputs
        project = inputs_or_project if isinstance(inputs_or_project, Project) or inputs_or_project is None else project
    else:
        node_type = node_type_or_inputs
        inputs = inputs_or_project if isinstance(inputs_or_project, dict) else {}

    preparer = PREPARERS_BY_NODE_TYPE.get(node_type)
    model = get_model_by_id(model_id)
    if preparer is None or node_type == NodeType.generic_wavespeed or (model and model.source == "catalog"):
        if model is None:
            raise NodeRunError(f"Model {model_id} is not registered.")
        return await prepare_model_inputs(adapter=adapter, model=model, inputs=inputs, project=project)
    return await preparer(adapter, inputs, project)


def node_type_for_model_id(model_id: str) -> NodeType:
    model_ids = {
        GENERATE_IMAGE_MODEL_ID: NodeType.text_to_image,
        REMIX_IMAGE_MODEL_ID: NodeType.image_to_image,
        UPSCALE_IMAGE_MODEL_ID: NodeType.upscale_image,
        REMOVE_BACKGROUND_MODEL_ID: NodeType.remove_background,
        IMAGE_TO_VIDEO_MODEL_ID: NodeType.image_to_video,
        TEXT_TO_SPEECH_MODEL_ID: NodeType.text_to_speech,
        "wavespeed-ai/wan-2.2/t2v-480p-ultra-fast": NodeType.text_to_video,
        "alibaba/wan-2.6/reference-to-video-flash": NodeType.reference_to_video,
        "vidu/q2-turbo/extend-video": NodeType.video_extend,
        "vidu/template/halloween": NodeType.video_effect,
        "wavespeed-ai/openai-whisper": NodeType.speech_to_text,
        "wavespeed-ai/qwen3-tts/voice-design": NodeType.generate_voice,
        "wavespeed-ai/latentsync": NodeType.lip_sync,
        "wavespeed-ai/infinitetalk": NodeType.talking_avatar,
        "wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid": NodeType.text_to_3d,
        "wavespeed-ai/hunyuan3d-v2-multi-view": NodeType.image_to_3d,
        "wavespeed-ai/image-body-swap": NodeType.portrait_transfer,
        "wavespeed-ai/z-image/turbo-inpaint": NodeType.remove_object,
        DEEPSEEK_V4_FLASH_MODEL_ID: NodeType.llm_text,
        GPT_5_NANO_MODEL_ID: NodeType.llm_vision,
    }
    node_type = model_ids.get(model_id)
    if node_type is None:
        model = get_model_by_id(model_id)
        if model:
            return model.node_type
        raise NodeRunError(f"Model is not registered: {model_id}")
    return node_type


async def prepare_text_to_image_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = prepare_prompt_inputs(dict(inputs))
    if prepared.get("image"):
        prepared["image"] = await resolve_asset_input(adapter, prepared, project, "image", {AssetKind.image})
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    if prepared.get("strength") not in (None, ""):
        prepared["strength"] = float_or_default(prepared.get("strength"), 0.6, "strength")
    return clean_inputs(prepared)


async def prepare_image_to_image_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = prepare_prompt_inputs(dict(inputs))
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    return clean_inputs(prepared)


async def prepare_reference_to_image_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = prepare_prompt_inputs(dict(inputs))
    prepared["image"] = await resolve_asset_input(adapter, prepared, project, "reference_image", {AssetKind.image})
    prepared.pop("reference_image", None)
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    return clean_inputs(prepared)


async def prepare_remove_background_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    prepared.setdefault("enable_base64_output", False)
    prepared.setdefault("enable_sync_mode", False)
    return clean_inputs(prepared)


async def prepare_inpaint_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = prepare_prompt_inputs(dict(inputs))
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    prepared["mask_image"] = await resolve_asset_input(adapter, prepared, project, "mask_image", {AssetKind.image})
    prepared.setdefault("size", "1024*1024")
    return clean_inputs(prepared)


async def prepare_upscale_image_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    prepared.setdefault("target_resolution", "4k")
    prepared.setdefault("output_format", "jpeg")
    prepared.setdefault("enable_base64_output", False)
    prepared.setdefault("enable_sync_mode", False)
    return clean_inputs(prepared)


async def prepare_image_to_video_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = prepare_prompt_inputs(dict(inputs))
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    if prepared.get("last_image"):
        prepared["last_image"] = await resolve_asset_input(adapter, prepared, project, "last_image", {AssetKind.image})
    prepared["duration"] = int_or_default(prepared.get("duration"), 5, "duration")
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    prepared.setdefault("negative_prompt", "")
    return clean_inputs(prepared)


async def prepare_start_end_to_video_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = prepare_prompt_inputs(dict(inputs))
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    prepared["last_image"] = await resolve_asset_input(adapter, prepared, project, "last_image", {AssetKind.image})
    prepared["duration"] = int_or_default(prepared.get("duration"), 5, "duration")
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    prepared.setdefault("negative_prompt", "")
    return clean_inputs(prepared)


async def prepare_text_to_video_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    del adapter, project
    prepared = prepare_prompt_inputs(dict(inputs))
    prepared.setdefault("negative_prompt", "")
    prepared.setdefault("size", "832*480")
    prepared["duration"] = int_or_default(prepared.get("duration"), 5, "duration")
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    return clean_inputs(prepared)


async def prepare_reference_to_video_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = prepare_prompt_inputs(dict(inputs))
    reference_url = await resolve_asset_input(adapter, prepared, project, "reference_image", {AssetKind.image})
    prepared["reference_urls"] = [reference_url]
    prepared.pop("reference_image", None)
    if prepared.get("audio"):
        prepared["audio"] = await resolve_asset_input(adapter, prepared, project, "audio", {AssetKind.audio})
    prepared.setdefault("negative_prompt", "")
    prepared.setdefault("size", "1280*720")
    prepared["duration"] = int_or_default(prepared.get("duration"), 5, "duration")
    prepared.setdefault("shot_type", "single")
    prepared.setdefault("enable_audio", True)
    prepared.setdefault("enable_prompt_expansion", False)
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    return clean_inputs(prepared)


async def prepare_video_extend_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["video"] = await resolve_video_input(adapter, prepared, project)
    if prepared.get("image"):
        prepared["image"] = await resolve_asset_input(adapter, prepared, project, "image", {AssetKind.image})
    if prepared.get("prompt"):
        prepared["prompt"] = str(prepared["prompt"]).strip()
    prepared["duration"] = float_or_default(prepared.get("duration"), 5, "duration")
    if prepared["duration"] < 1 or prepared["duration"] > 7:
        raise NodeRunError("duration must be between 1 and 7 seconds.")
    prepared.setdefault("resolution", "720p")
    if prepared["resolution"] not in {"540p", "720p", "1080p"}:
        raise NodeRunError("resolution must be one of 540p, 720p, or 1080p.")
    return clean_inputs(prepared)


async def prepare_video_effect_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    prepared.setdefault("template", "tim_burton")
    if prepared["template"] not in {
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
    }:
        raise NodeRunError("template is not supported by vidu/template/halloween.")
    prepared.setdefault("bgm", True)
    prepared["seed"] = int_or_default(prepared.get("seed"), 0, "seed")
    return clean_inputs(prepared)


async def prepare_text_to_speech_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    del adapter, project
    prepared = dict(inputs)
    text = str(prepared.get("text") or "").strip()
    if not text:
        raise NodeRunError("Text is required for text_to_speech.")
    prepared["text"] = text
    prepared.setdefault("language", "auto")
    prepared.setdefault("voice", "Vivian")
    prepared.setdefault("style_instruction", "")
    return clean_inputs(prepared)


async def prepare_voice_design_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    del adapter, project
    prepared = dict(inputs)
    text = str(prepared.get("text") or "").strip()
    voice_description = str(prepared.get("voice_description") or "").strip()
    if not text:
        raise NodeRunError("text is required.")
    if not voice_description:
        raise NodeRunError("voice_description is required.")
    prepared["text"] = text
    prepared["voice_description"] = voice_description
    prepared.setdefault("language", "auto")
    return clean_inputs(prepared)


async def prepare_speech_to_text_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["audio"] = await resolve_audio_input(adapter, prepared, project)
    prepared.setdefault("language", "auto")
    prepared.setdefault("task", "transcribe")
    prepared.setdefault("enable_timestamps", False)
    prepared.setdefault("prompt", "")
    prepared.setdefault("enable_sync_mode", False)
    return clean_inputs(prepared)


async def prepare_lip_sync_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["video"] = await resolve_video_input(adapter, prepared, project)
    prepared["audio"] = await resolve_audio_input(adapter, prepared, project)
    return clean_inputs(prepared)


async def prepare_portrait_transfer_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    prepared["body_image"] = await resolve_asset_input(adapter, prepared, project, "body_image", {AssetKind.image})
    return clean_inputs(prepared)


async def prepare_talking_avatar_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
    prepared["audio"] = await resolve_audio_input(adapter, prepared, project)
    if prepared.get("mask_image"):
        prepared["mask_image"] = await resolve_asset_input(adapter, prepared, project, "mask_image", {AssetKind.image})
    prepared.setdefault("prompt", "")
    prepared.setdefault("resolution", "480p")
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    return clean_inputs(prepared)


async def prepare_text_to_3d_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    del adapter, project
    return prepare_prompt_inputs(dict(inputs))


async def prepare_image_to_3d_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = dict(inputs)
    prepared["front_image_url"] = await resolve_asset_input(adapter, prepared, project, "front_image_url", {AssetKind.image})
    prepared["back_image_url"] = await resolve_asset_input(adapter, prepared, project, "back_image_url", {AssetKind.image})
    prepared["left_image_url"] = await resolve_asset_input(adapter, prepared, project, "left_image_url", {AssetKind.image})
    prepared["seed"] = int_or_default(prepared.get("seed"), 0, "seed")
    prepared["num_inference_steps"] = int_or_default(prepared.get("num_inference_steps"), 50, "num_inference_steps")
    prepared["guidance_scale"] = float_or_default(prepared.get("guidance_scale"), 7.5, "guidance_scale")
    prepared["octree_resolution"] = int_or_default(prepared.get("octree_resolution"), 256, "octree_resolution")
    prepared.setdefault("textured_mesh", False)
    return clean_inputs(prepared)


async def prepare_llm_text_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    del adapter, project
    prepared = dict(inputs)
    text = str(prepared.get("text") or "").strip()
    if not text:
        raise NodeRunError("text is required.")
    return clean_inputs({"text": text})


async def prepare_llm_vision_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = await prepare_llm_text_inputs(adapter, inputs, project)
    image = str(inputs.get("image") or "").strip()
    if image:
        prepared["image"] = await resolve_image_input(adapter, inputs, project)
    return clean_inputs(prepared)


def prepare_prompt_inputs(prepared: dict[str, Any]) -> dict[str, Any]:
    prompt = str(prepared.get("prompt") or "").strip()
    if not prompt:
        raise NodeRunError("Prompt is required.")
    prepared["prompt"] = prompt
    return clean_inputs(prepared)


async def maybe_optimize_prompt(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    node_type: NodeType,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    prepared = dict(inputs)
    use_optimizer = bool(prepared.get("use_prompt_optimizer"))
    if not use_optimizer:
        return strip_prompt_optimizer_inputs(prepared), None

    prompt = str(prepared.get("prompt") or "").strip()
    if not prompt:
        return strip_prompt_optimizer_inputs(prepared), None

    optimizer_inputs: dict[str, Any] = {
        "text": prompt,
        "style": str(prepared.get("prompt_optimizer_style") or "default"),
        "mode": str(prepared.get("prompt_optimizer_mode") or default_prompt_optimizer_mode(node_type)),
        "enable_sync_mode": True,
    }
    if prepared.get("image"):
        optimizer_inputs["image"] = prepared["image"]

    raw_optimizer_output = await adapter.run_model(PROMPT_OPTIMIZER_MODEL_ID, clean_inputs(optimizer_inputs))
    optimized_prompt = extract_prompt_optimizer_text(raw_optimizer_output)
    if not optimized_prompt:
        raise NodeRunError("Prompt optimizer did not return optimized text.")

    prepared["prompt"] = optimized_prompt
    metadata = {
        "model_id": PROMPT_OPTIMIZER_MODEL_ID,
        "original_prompt": prompt,
        "optimized_prompt": optimized_prompt,
        "request": optimizer_inputs,
        "raw_output": raw_optimizer_output,
    }
    return strip_prompt_optimizer_inputs(prepared), metadata


def strip_prompt_optimizer_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in inputs.items() if key not in PROMPT_OPTIMIZER_INPUT_KEYS}


def default_prompt_optimizer_mode(node_type: NodeType) -> str:
    if node_type in {NodeType.image_to_video, NodeType.start_end_to_video, NodeType.text_to_video}:
        return "video"
    return "image"


def extract_prompt_optimizer_text(raw_output: dict[str, Any]) -> str | None:
    key_priority = ("outputs", "optimized_prompt", "prompt", "text", "result", "output", "content")
    ignored_text_keys = {"id", "model", "status", "message", "created_at", "error"}

    def from_value(value: Any) -> str | None:
        if isinstance(value, str):
            value = value.strip()
            if value and not is_http_url(value):
                return value
            return None
        if isinstance(value, list):
            for item in value:
                found = from_value(item)
                if found:
                    return found
            return None
        if isinstance(value, dict):
            for key in key_priority:
                if key in value:
                    found = from_value(value[key])
                    if found:
                        return found
            for key, nested_value in value.items():
                if key in ignored_text_keys:
                    continue
                found = from_value(nested_value)
                if found:
                    return found
        return None

    return from_value(raw_output)


def clean_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in inputs.items() if value not in (None, "")}


def int_or_default(value: Any, default: int, field_name: str = "value") -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NodeRunError(f"Expected an integer for {field_name}, got {value!r}.") from exc


def float_or_default(value: Any, default: float, field_name: str = "value") -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise NodeRunError(f"Expected a number for {field_name}, got {value!r}.") from exc


async def resolve_image_input(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> str:
    return await resolve_asset_input(adapter, inputs, project, "image", {AssetKind.image})


async def resolve_audio_input(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> str:
    return await resolve_asset_input(adapter, inputs, project, "audio", {AssetKind.audio})


async def resolve_video_input(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> str:
    return await resolve_asset_input(adapter, inputs, project, "video", {AssetKind.video})


async def resolve_asset_input(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
    field_name: str,
    expected_kinds: set[AssetKind] | None = None,
) -> str:
    fallback_asset_id = inputs.get("asset_id") if field_name in {"image", "audio", "video"} else None
    asset_ref = str(inputs.get(field_name) or fallback_asset_id or "").strip()
    if not asset_ref:
        raise NodeRunError(f"{field_name} is required.")

    asset = find_asset(project, asset_ref)
    if asset:
        enforce_asset_kind(asset.kind, expected_kinds, field_name)
        if asset.wavespeed_url:
            return asset.wavespeed_url
        if asset.local_path:
            asset.wavespeed_url = await adapter.upload_file(Path(asset.local_path))
            await persist_project_best_effort(project)
            return asset.wavespeed_url
        if asset.public_url:
            if is_local_url(asset.public_url):
                raise NodeRunError(
                    f"Localhost {asset.kind.value} URLs are not reachable by WaveSpeed. Upload the asset first."
                )
            return asset.public_url
        raise NodeRunError(f"Selected {field_name} asset has no URL or uploadable local file path.")

    if is_http_url(asset_ref):
        if is_local_url(asset_ref):
            kind = kind_label(expected_kinds) if expected_kinds else "asset"
            raise NodeRunError(f"Localhost {kind} URLs are not reachable by WaveSpeed. Upload the asset first.")
        inferred_kind = resolve_asset_kind_from_url(asset_ref)
        if inferred_kind is not AssetKind.other:
            enforce_asset_kind(inferred_kind, expected_kinds, field_name)
        return asset_ref

    path = Path(asset_ref)
    if path.exists():
        inferred_kind = resolve_asset_kind_from_url(path.as_uri())
        if inferred_kind is not AssetKind.other:
            enforce_asset_kind(inferred_kind, expected_kinds, field_name)
        return await adapter.upload_file(path)

    expected = f" {kind_label(expected_kinds)}" if expected_kinds else ""
    raise NodeRunError(f"{field_name} must be a public URL, project{expected} asset, or existing local file path.")


async def persist_project_best_effort(project: Project | None) -> None:
    if project is None:
        return
    try:
        await project_store.save_project(project)
    except Exception:
        pass


def enforce_asset_kind(kind: AssetKind, expected_kinds: set[AssetKind] | None, field_name: str) -> None:
    if not expected_kinds or kind in expected_kinds:
        return
    raise NodeRunError(f"Expected {kind_label(expected_kinds)} asset for {field_name}, got {kind.value}.")


def kind_label(kinds: set[AssetKind] | None) -> str:
    if not kinds:
        return "asset"
    return "/".join(sorted(kind.value for kind in kinds))


def find_asset(project: Project | None, ref: str) -> Asset | None:
    if not project:
        return None
    for asset in project.assets:
        if ref in {asset.id, asset.public_url, asset.wavespeed_url, asset.local_path}:
            return asset
    return None


def is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def is_local_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"} or host.startswith("192.168.") or host.startswith("10.")


def extract_text_output(raw_output: dict[str, Any]) -> str | None:
    choices = raw_output.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                extracted = extract_content_text(content)
                if extracted:
                    return extracted
            extracted = extract_content_text(first_choice.get("text"))
            if extracted:
                return extracted

    candidates = [
        raw_output.get("text"),
        raw_output.get("transcript"),
        raw_output.get("transcription"),
        raw_output.get("output", {}).get("text") if isinstance(raw_output.get("output"), dict) else None,
        raw_output.get("data", {}).get("text") if isinstance(raw_output.get("data"), dict) else None,
    ]
    outputs = raw_output.get("outputs")
    if isinstance(outputs, list) and outputs and isinstance(outputs[0], dict):
        candidates.append(outputs[0].get("text"))

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def extract_content_text(content: Any) -> str | None:
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n".join(parts)
    return None


def mark_node_running(node: CanvasNode) -> None:
    node.status = NodeStatus.running
    node.error_message = None
    node.updated_at = datetime.now(timezone.utc)
    node.last_run = {
        "started_at": utc_iso(),
    }


def mark_node_success(
    node: CanvasNode,
    model_id: str,
    raw_output: dict[str, Any],
    output_urls: list[str],
    asset_ids: list[str],
) -> None:
    node.status = NodeStatus.success
    node.error_message = None
    node.updated_at = datetime.now(timezone.utc)
    node.output_urls = output_urls
    node.output_asset_ids = asset_ids
    node.last_run = {
        "ok": True,
        "model_id": model_id,
        "completed_at": utc_iso(),
        "output_urls": output_urls,
        "asset_ids": asset_ids,
        "raw_output": raw_output,
    }
    text_output = extract_text_output(raw_output)
    if text_output:
        node.last_run["text_output"] = text_output
    if not output_urls and not text_output:
        node.last_run["structured_output"] = raw_output


def mark_node_error(node: CanvasNode, error: str) -> None:
    node.status = NodeStatus.error
    node.error_message = error
    node.updated_at = datetime.now(timezone.utc)
    node.last_run = {
        **node.last_run,
        "ok": False,
        "completed_at": utc_iso(),
        "error": error,
    }


PREPARERS_BY_NODE_TYPE: dict[NodeType, Preparer] = {
    NodeType.text_to_image: prepare_text_to_image_inputs,
    NodeType.image_to_image: prepare_image_to_image_inputs,
    NodeType.reference_to_image: prepare_reference_to_image_inputs,
    NodeType.upscale_image: prepare_upscale_image_inputs,
    NodeType.remove_background: prepare_remove_background_inputs,
    NodeType.remove_object: prepare_inpaint_inputs,
    NodeType.image_to_video: prepare_image_to_video_inputs,
    NodeType.start_end_to_video: prepare_start_end_to_video_inputs,
    NodeType.text_to_video: prepare_text_to_video_inputs,
    NodeType.reference_to_video: prepare_reference_to_video_inputs,
    NodeType.video_extend: prepare_video_extend_inputs,
    NodeType.video_effect: prepare_video_effect_inputs,
    NodeType.text_to_speech: prepare_text_to_speech_inputs,
    NodeType.text_to_audio: prepare_text_to_speech_inputs,
    NodeType.generate_voice: prepare_voice_design_inputs,
    NodeType.speech_to_text: prepare_speech_to_text_inputs,
    NodeType.lip_sync: prepare_lip_sync_inputs,
    NodeType.portrait_transfer: prepare_portrait_transfer_inputs,
    NodeType.talking_avatar: prepare_talking_avatar_inputs,
    NodeType.image_to_3d: prepare_image_to_3d_inputs,
    NodeType.text_to_3d: prepare_text_to_3d_inputs,
    NodeType.llm_text: prepare_llm_text_inputs,
    NodeType.llm_vision: prepare_llm_vision_inputs,
}
