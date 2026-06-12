from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas import Asset, CanvasNode, NodeStatus, NodeType, Project
from app.services.registry import get_model_for_node
from app.services.wavespeed_adapter import WaveSpeedAdapter

GENERATE_IMAGE_MODEL_ID = "wavespeed-ai/z-image/turbo"
REMIX_IMAGE_MODEL_ID = "wavespeed-ai/z-image-turbo/image-to-image"
UPSCALE_IMAGE_MODEL_ID = "wavespeed-ai/image-upscaler"
REMOVE_BACKGROUND_MODEL_ID = "wavespeed-ai/image-background-remover"
IMAGE_TO_VIDEO_MODEL_ID = "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast"
TEXT_TO_SPEECH_MODEL_ID = "wavespeed-ai/qwen3-tts/text-to-speech"
SUPPORTED_MODEL_IDS = {
    GENERATE_IMAGE_MODEL_ID,
    REMIX_IMAGE_MODEL_ID,
    UPSCALE_IMAGE_MODEL_ID,
    REMOVE_BACKGROUND_MODEL_ID,
    IMAGE_TO_VIDEO_MODEL_ID,
    TEXT_TO_SPEECH_MODEL_ID,
}


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
    if model_id not in SUPPORTED_MODEL_IDS:
        raise NodeRunError(f"Model is not runnable in this MVP phase: {model_id}")

    model_spec = get_model_for_node(node_type, model_id)
    if model_spec is None:
        raise NodeRunError(f"Model {model_id} is not registered for node type {node_type.value}.")
    if not model_spec.enabled:
        raise NodeRunError(f"Model is disabled in the registry: {model_id}")

    prepared_inputs = await prepare_inputs(adapter, model_id, inputs, project)
    if target_node:
        target_node.inputs = prepared_inputs

    raw_output = await adapter.run_model(model_id, prepared_inputs)
    output_urls = adapter.extract_output_urls(raw_output)
    if not output_urls:
        raise NodeRunError("WaveSpeed response did not include any output URLs.")

    output_assets = [
        build_output_asset(
            model_id=model_id,
            output_kind=model_spec.output_kind,
            output_url=url,
            output_index=index,
            raw_output=raw_output,
            target_node=target_node,
        )
        for index, url in enumerate(output_urls)
    ]
    return raw_output, output_urls, output_assets


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
    clean_url = url.split("?", 1)[0].lower()
    for suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".webm", ".mp3", ".wav", ".m4a", ".ogg"):
        if clean_url.endswith(suffix):
            return suffix
    return ""


async def prepare_inputs(
    adapter: WaveSpeedAdapter,
    model_id: str,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    if model_id == GENERATE_IMAGE_MODEL_ID:
        return await prepare_text_to_image_inputs(adapter, inputs, project)

    if model_id == REMIX_IMAGE_MODEL_ID:
        return await prepare_image_to_image_inputs(adapter, inputs, project)

    if model_id == REMOVE_BACKGROUND_MODEL_ID:
        return await prepare_remove_background_inputs(adapter, inputs, project)

    if model_id == UPSCALE_IMAGE_MODEL_ID:
        return await prepare_upscale_image_inputs(adapter, inputs, project)

    if model_id == IMAGE_TO_VIDEO_MODEL_ID:
        return await prepare_image_to_video_inputs(adapter, inputs, project)

    if model_id == TEXT_TO_SPEECH_MODEL_ID:
        return await prepare_text_to_speech_inputs(adapter, inputs, project)

    raise NodeRunError(f"Model is not runnable in this MVP phase: {model_id}")


async def prepare_text_to_image_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    del adapter, project
    return prepare_prompt_inputs(dict(inputs))


async def prepare_image_to_image_inputs(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    prepared = prepare_prompt_inputs(dict(inputs))
    prepared["image"] = await resolve_image_input(adapter, prepared, project)
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
        prepared["last_image"] = await resolve_named_image_input(adapter, prepared, project, "last_image")
    prepared["duration"] = int_or_default(prepared.get("duration"), 5, "duration")
    prepared["seed"] = int_or_default(prepared.get("seed"), -1, "seed")
    prepared.setdefault("negative_prompt", "")
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


def prepare_prompt_inputs(prepared: dict[str, Any]) -> dict[str, Any]:
    prompt = str(prepared.get("prompt") or "").strip()
    if not prompt:
        raise NodeRunError("Prompt is required.")
    prepared["prompt"] = prompt
    return clean_inputs(prepared)


def clean_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in inputs.items() if value not in (None, "")}


def int_or_default(value: Any, default: int, field_name: str = "value") -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise NodeRunError(f"Expected an integer for {field_name}, got {value!r}.") from exc


async def resolve_image_input(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
) -> str:
    return await resolve_named_image_input(adapter, inputs, project, "image")


async def resolve_named_image_input(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
    field_name: str,
) -> str:
    fallback_asset_id = inputs.get("asset_id") if field_name == "image" else None
    image_ref = str(inputs.get(field_name) or fallback_asset_id or "").strip()
    if not image_ref:
        raise NodeRunError(f"{field_name} is required.")

    asset = find_asset(project, image_ref)
    if asset:
        if asset.wavespeed_url:
            return asset.wavespeed_url
        if asset.local_path:
            asset.wavespeed_url = await adapter.upload_file(Path(asset.local_path))
            return asset.wavespeed_url
        if asset.public_url and not is_local_url(asset.public_url):
            return asset.public_url
        raise NodeRunError("Selected asset has no WaveSpeed URL or uploadable local file path.")

    if is_http_url(image_ref):
        if is_local_url(image_ref):
            raise NodeRunError("Localhost image URLs are not reachable by WaveSpeed. Upload the asset to WaveSpeed first or select the uploaded asset.")
        return image_ref

    path = Path(image_ref)
    if path.exists():
        return await adapter.upload_file(path)

    raise NodeRunError("Source image must be a public URL, project asset, or existing local file path.")


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
    return value.startswith(("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1"))


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
