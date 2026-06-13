from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.schemas import ArtifactRole, Asset, AssetKind, CanvasNode, ModelSpec, WaveSpeedCatalogModel

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
OTHER_SUFFIXES = {".glb", ".gltf", ".obj", ".fbx", ".stl", ".usdz", ".zip", ".txt", ".json", ".srt", ".vtt"}


def normalize_model_output(
    *,
    model: WaveSpeedCatalogModel | ModelSpec,
    model_id: str,
    raw_output: dict[str, Any],
    target_node: CanvasNode | None = None,
) -> tuple[list[str], list[Asset], str | None, dict[str, Any]]:
    output_urls = collect_urls(raw_output)
    text_output = extract_text_output(raw_output)
    structured_output = extract_structured_output(raw_output, output_urls, text_output)
    output_assets = [
        build_asset(
            model=model,
            model_id=model_id,
            output_url=url,
            output_index=index,
            raw_output=raw_output,
            target_node=target_node,
        )
        for index, url in enumerate(output_urls)
    ]
    return output_urls, output_assets, text_output, structured_output


def collect_urls(value: Any) -> list[str]:
    urls: list[str] = []

    def visit(current: Any, key: str = "") -> None:
        if isinstance(current, str):
            if is_output_url(current) and current not in urls:
                urls.append(current)
            return
        if isinstance(current, list):
            for item in current:
                visit(item, key)
            return
        if isinstance(current, dict):
            for preferred in ("outputs", "output", "url", "uri", "file", "image", "video", "audio"):
                if preferred in current:
                    visit(current[preferred], preferred)
            for nested_key, nested_value in current.items():
                if nested_key in {"outputs", "output", "url", "uri", "file", "image", "video", "audio"}:
                    continue
                visit(nested_value, nested_key)

    visit(value)
    return urls


def extract_text_output(raw_output: dict[str, Any]) -> str | None:
    choices = raw_output.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                text = content_to_text(message.get("content"))
                if text:
                    return text
            text = content_to_text(first.get("text"))
            if text:
                return text

    candidates = [
        raw_output.get("text"),
        raw_output.get("transcript"),
        raw_output.get("transcription"),
        raw_output.get("caption"),
    ]
    data = raw_output.get("data")
    if isinstance(data, dict):
        candidates.extend([data.get("text"), data.get("transcript"), data.get("transcription")])
    output = raw_output.get("output")
    if isinstance(output, dict):
        candidates.append(output.get("text"))
    elif isinstance(output, str) and not is_output_url(output):
        candidates.append(output)
    outputs = raw_output.get("outputs")
    if isinstance(outputs, list):
        for item in outputs:
            if isinstance(item, str) and not is_output_url(item):
                candidates.append(item)
            if isinstance(item, dict):
                candidates.extend([item.get("text"), item.get("transcript"), item.get("caption")])

    for candidate in candidates:
        text = content_to_text(candidate)
        if text:
            return text
    return None


def content_to_text(content: Any) -> str | None:
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if parts:
            return "\n".join(parts)
    return None


def extract_structured_output(raw_output: dict[str, Any], output_urls: list[str], text_output: str | None) -> dict[str, Any]:
    if output_urls or text_output:
        return {}
    return raw_output if isinstance(raw_output, dict) else {"value": raw_output}


def build_asset(
    *,
    model: WaveSpeedCatalogModel | ModelSpec,
    model_id: str,
    output_url: str,
    output_index: int,
    raw_output: dict[str, Any],
    target_node: CanvasNode | None,
) -> Asset:
    output_kind = getattr(model, "output_kind", AssetKind.other)
    if output_kind == AssetKind.other:
        output_kind = infer_kind_from_url(output_url)
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
    stem = model_id.split("/")[-1] or "output"
    return f"{stem}-{output_index + 1}{suffix}"


def infer_kind_from_url(url: str) -> AssetKind:
    suffix = url_suffix(url)
    if suffix in IMAGE_SUFFIXES:
        return AssetKind.image
    if suffix in VIDEO_SUFFIXES:
        return AssetKind.video
    if suffix in AUDIO_SUFFIXES:
        return AssetKind.audio
    return AssetKind.other


def url_suffix(url: str) -> str:
    clean_path = urlparse(url).path.lower()
    for suffix in (*IMAGE_SUFFIXES, *VIDEO_SUFFIXES, *AUDIO_SUFFIXES, *OTHER_SUFFIXES):
        if clean_path.endswith(suffix):
            return suffix
    return ""


def is_output_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))
