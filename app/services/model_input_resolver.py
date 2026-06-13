from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas import Asset, AssetKind, ModelSpec, Project, WaveSpeedCatalogField, WaveSpeedCatalogModel
from app.services.input_safety import InputSafetyError, is_url_private_or_local, require_upload_contained_path
from app.services.wavespeed_adapter import WaveSpeedAdapter


class ModelInputResolverError(ValueError):
    pass


async def prepare_model_inputs(
    *,
    adapter: WaveSpeedAdapter,
    model: WaveSpeedCatalogModel | ModelSpec,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    fields = model.fields
    prepared: dict[str, Any] = {}
    known_fields = {field.name: field for field in fields}

    for field in fields:
        value = inputs.get(field.name, field.default)
        if is_empty(value):
            if field.required:
                raise ModelInputResolverError(f"{field.name} is required for {model_label(model)}.")
            continue
        prepared[field.name] = await coerce_field_value(adapter, field, value, project)

    for key, value in inputs.items():
        if key in known_fields or is_empty(value):
            continue
        prepared[key] = str(value) if not isinstance(value, (dict, list, bool, int, float)) else value

    prepared.setdefault("enable_base64_output", False)
    prepared.setdefault("enable_sync_mode", False)
    return {key: value for key, value in prepared.items() if not is_empty(value)}


async def coerce_field_value(
    adapter: WaveSpeedAdapter,
    field: WaveSpeedCatalogField,
    value: Any,
    project: Project | None,
) -> Any:
    if is_asset_list_field(field):
        values = split_list(value)
        min_items = getattr(field, "min_items", None)
        max_items = getattr(field, "max_items", None)
        if min_items is not None and len(values) < min_items:
            raise ModelInputResolverError(f"{field.name} requires at least {min_items} item(s).")
        if max_items is not None and len(values) > max_items:
            raise ModelInputResolverError(f"{field.name} allows at most {max_items} item(s).")
        return [await resolve_asset_value(adapter, item, project, field) for item in values]
    if field.type in {"asset_url", "file_url"}:
        return await resolve_asset_value(adapter, value, project, field)
    if field.type == "boolean":
        return to_bool(value)
    if field.type == "integer":
        return to_int(value, field.name)
    if field.type == "number":
        return to_float(value, field.name)
    if field.type == "select":
        if field.options and value not in field.options and str(value) not in {str(option) for option in field.options}:
            raise ModelInputResolverError(f"{field.name} must be one of: {', '.join(map(str, field.options))}.")
        return value
    if field.type == "json":
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(str(value))
        except json.JSONDecodeError as exc:
            raise ModelInputResolverError(f"{field.name} must be valid JSON.") from exc
    if field.type in {"string", "textarea", "unknown"}:
        return str(value).strip()
    if field.required:
        raise ModelInputResolverError(f"{field.name} has unsupported required field type {field.type}.")
    return str(value)


async def resolve_asset_value(
    adapter: WaveSpeedAdapter,
    value: Any,
    project: Project | None,
    field: WaveSpeedCatalogField,
) -> str:
    asset_ref = str(value or "").strip()
    if not asset_ref:
        raise ModelInputResolverError(f"{field.name} is required.")
    asset = find_asset(project, asset_ref)
    if asset:
        enforce_asset_kind(asset, field)
        if asset.wavespeed_url:
            return asset.wavespeed_url
        if asset.local_path:
            asset.wavespeed_url = await adapter.upload_file(safe_project_asset_path(asset.local_path, field.name))
            return asset.wavespeed_url
        if asset.public_url:
            if is_private_url(asset.public_url):
                raise ModelInputResolverError(f"{field.name} uses a localhost/private URL that WaveSpeed cannot fetch.")
            return asset.public_url
        raise ModelInputResolverError(f"Selected asset for {field.name} has no usable URL or local path.")

    if is_http_url(asset_ref):
        if is_private_url(asset_ref):
            raise ModelInputResolverError(f"{field.name} uses a localhost/private URL that WaveSpeed cannot fetch.")
        return asset_ref

    raise ModelInputResolverError(f"{field.name} must be a project asset ID or public URL.")


def find_asset(project: Project | None, ref: str) -> Asset | None:
    if project is None:
        return None
    return next((asset for asset in project.assets if ref in {asset.id, asset.public_url, asset.wavespeed_url, asset.local_path}), None)


def enforce_asset_kind(asset: Asset, field: WaveSpeedCatalogField) -> None:
    if field.asset_kind is None or field.asset_kind == AssetKind.other or asset.kind == field.asset_kind:
        return
    raise ModelInputResolverError(f"Expected {field.asset_kind.value} asset for {field.name}, got {asset.kind.value}.")


def is_asset_list_field(field: WaveSpeedCatalogField) -> bool:
    if field.type == "asset_url_list":
        return True
    if field.type not in {"asset_url", "file_url"}:
        return False
    name = field.name.lower()
    if name in {
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
    }:
        return True
    if name.endswith(("_images", "_videos", "_audios")):
        return True
    description = (field.description or "").lower()
    return name == "reference" and "reference image" in description


def split_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [item for item in value if not is_empty(item)]
    text = str(value or "")
    parts = []
    for line in text.replace(",", "\n").splitlines():
        item = line.strip()
        if item:
            parts.append(item)
    return parts


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def to_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ModelInputResolverError(f"{field_name} must be an integer.") from exc


def to_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ModelInputResolverError(f"{field_name} must be a number.") from exc


def is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def is_private_url(value: str) -> bool:
    return is_url_private_or_local(value)


def safe_project_asset_path(value: str, field_name: str) -> Path:
    try:
        path = require_upload_contained_path(Path(value))
    except (OSError, InputSafetyError) as exc:
        raise ModelInputResolverError(f"Selected asset for {field_name} has an unsafe local file path.") from exc
    if not path.exists():
        raise ModelInputResolverError(f"Selected asset for {field_name} local file does not exist.")
    return path


def model_label(model: WaveSpeedCatalogModel | ModelSpec) -> str:
    return getattr(model, "display_name", None) or getattr(model, "label", None) or getattr(model, "model_id", "model")
