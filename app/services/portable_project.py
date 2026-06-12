from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas import NodeStatus, Project, ProjectSettings, new_id, utc_now
from app.services import project_store
from app.services.project_validation import ProjectValidationError, validate_edges_reference_nodes, validate_project_settings

EXPORT_SCHEMA = "wavespeed_canvas_project_export"
EXPORT_VERSION = 1
APP_NAME = "WaveSpeed Canvas MVP"

MAX_NODES = 100
MAX_EDGES = 200
MAX_ASSETS = 200
MAX_RUNS = 100


class PortableProjectError(ValueError):
    """Raised when a project cannot be imported, exported, or duplicated safely."""


def safe_export_filename(project: Project) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", project.name.strip().lower()).strip("-")
    return f"wavespeed-workflow-{name or 'untitled'}-{project.id}.json"


def export_project(
    project: Project,
    *,
    include_outputs: bool = True,
    include_settings: bool = True,
    include_run_history: bool = False,
) -> dict[str, Any]:
    project_copy, warnings = sanitized_project_copy(
        project,
        include_outputs=include_outputs,
        include_settings=include_settings,
        include_run_history=include_run_history,
        reset_runtime=not include_outputs,
        preserve_ids=True,
    )
    return {
        "schema": EXPORT_SCHEMA,
        "version": EXPORT_VERSION,
        "exported_at": utc_now().isoformat(),
        "app": APP_NAME,
        "project": project_copy.model_dump(mode="json"),
        "warnings": warnings,
    }


async def import_project(
    import_data: dict[str, Any],
    *,
    name: str | None = None,
    include_outputs: bool = True,
    include_run_history: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    source_project, warnings = project_from_import_data(import_data)
    source_project.name = name or source_project.name or "Imported Workflow"
    imported, id_map, clone_warnings = clone_project(
        source_project,
        name=source_project.name,
        include_outputs=include_outputs,
        include_run_history=include_run_history,
        preserve_settings=True,
        reset_runtime=True,
    )
    warnings.extend(clone_warnings)
    saved = await project_store.save_project(imported, settings)
    return {"ok": True, "project": saved, "warnings": warnings, "id_map": id_map}


async def duplicate_project(
    project: Project,
    *,
    name: str | None = None,
    include_outputs: bool = True,
    include_run_history: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    duplicate, id_map, warnings = clone_project(
        project,
        name=name or f"Copy of {project.name}",
        include_outputs=include_outputs,
        include_run_history=include_run_history,
        preserve_settings=True,
        reset_runtime=not include_outputs,
    )
    saved = await project_store.save_project(duplicate, settings)
    return {"ok": True, "project": saved, "warnings": warnings, "id_map": id_map}


def project_from_import_data(import_data: dict[str, Any]) -> tuple[Project, list[str]]:
    if not isinstance(import_data, dict):
        raise PortableProjectError("Import data must be a JSON object.")

    warnings: list[str] = []
    raw_project = import_data
    if "project" in import_data:
        schema = import_data.get("schema")
        if schema != EXPORT_SCHEMA:
            raise PortableProjectError("Unsupported export schema.")
        version = import_data.get("version", EXPORT_VERSION)
        if version != EXPORT_VERSION:
            warnings.append(f"Export version {version} is not the current version {EXPORT_VERSION}; importing best effort.")
        raw_project = import_data.get("project") or {}

    if not isinstance(raw_project, dict):
        raise PortableProjectError("Imported project must be a JSON object.")

    validate_project_limits(raw_project)
    raw_project = sanitize_import_project_dict(raw_project, warnings)

    try:
        project = Project.model_validate(raw_project)
        validate_project_settings(project.settings)
        validate_edges_reference_nodes(project.edges, {node.id for node in project.nodes})
    except (ValidationError, ProjectValidationError) as exc:
        raise PortableProjectError(str(exc)) from exc
    return project, warnings


def validate_project_limits(data: dict[str, Any]) -> None:
    if len(data.get("nodes") or []) > MAX_NODES:
        raise PortableProjectError(f"Imported project exceeds the {MAX_NODES} node limit.")
    if len(data.get("edges") or []) > MAX_EDGES:
        raise PortableProjectError(f"Imported project exceeds the {MAX_EDGES} edge limit.")
    if len(data.get("assets") or []) > MAX_ASSETS:
        raise PortableProjectError(f"Imported project exceeds the {MAX_ASSETS} asset limit.")
    if len(data.get("runs") or []) > MAX_RUNS:
        raise PortableProjectError(f"Imported project exceeds the {MAX_RUNS} run history limit.")


def sanitized_project_copy(
    project: Project,
    *,
    include_outputs: bool,
    include_settings: bool,
    include_run_history: bool,
    reset_runtime: bool,
    preserve_ids: bool,
) -> tuple[Project, list[str]]:
    warnings: list[str] = []
    data = project.model_dump(mode="json")
    if not include_settings:
        data["settings"] = ProjectSettings().model_dump(mode="json")
    if not include_run_history:
        data["runs"] = []
    if not include_outputs:
        data["assets"] = []
        for node in data.get("nodes", []):
            node["output_asset_ids"] = []
            node["output_urls"] = []
            node["last_run"] = {}
    if reset_runtime:
        for node in data.get("nodes", []):
            node["status"] = NodeStatus.idle.value
            node["error_message"] = None
            node["last_run"] = {} if not include_outputs else node.get("last_run") or {}

    sanitize_asset_dicts(data.get("assets", []), warnings)
    sanitize_node_dicts(data.get("nodes", []), warnings)
    copied = Project.model_validate(data)
    if not preserve_ids:
        copied, id_map, remap_warnings = remap_project_ids(copied, include_outputs=include_outputs)
        warnings.extend(remap_warnings)
    return copied, warnings


def sanitize_import_project_dict(data: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    clean = deepcopy(data)
    clean["id"] = new_id("project")
    clean["created_at"] = utc_now().isoformat()
    clean["updated_at"] = utc_now().isoformat()
    sanitize_asset_dicts(clean.get("assets") or [], warnings)
    sanitize_node_dicts(clean.get("nodes") or [], warnings)
    return clean


def sanitize_asset_dicts(assets: list[dict[str, Any]], warnings: list[str]) -> None:
    for asset in assets:
        if asset.get("local_path"):
            warnings.append(f"Stripped local path from asset {asset.get('id') or asset.get('filename') or 'unknown'}.")
            asset["local_path"] = None
        public_url = asset.get("public_url")
        if public_url and is_local_url(public_url):
            metadata = asset.setdefault("metadata", {})
            metadata["non_portable_public_url"] = public_url
            asset["public_url"] = None
            warnings.append(f"Asset {asset.get('id') or asset.get('filename') or 'unknown'} had a localhost URL; it was marked non-portable.")
        for key in ("public_url", "wavespeed_url"):
            value = asset.get(key)
            if isinstance(value, str) and is_local_path(value):
                warnings.append(f"Removed local path value from asset {asset.get('id') or 'unknown'} field {key}.")
                asset[key] = None


def sanitize_node_dicts(nodes: list[dict[str, Any]], warnings: list[str]) -> None:
    for node in nodes:
        node["status"] = NodeStatus.idle.value
        node["error_message"] = None
        node["last_run"] = node.get("last_run") or {}
        inputs = node.get("inputs")
        if isinstance(inputs, dict):
            node["inputs"] = sanitize_value(inputs, warnings, f"node {node.get('id') or node.get('title') or 'unknown'} inputs")
        output_urls = []
        for url in node.get("output_urls") or []:
            if isinstance(url, str) and (is_local_url(url) or is_local_path(url)):
                warnings.append(f"Removed non-portable output URL from node {node.get('id') or node.get('title') or 'unknown'}.")
                continue
            output_urls.append(url)
        node["output_urls"] = output_urls


def sanitize_value(value: Any, warnings: list[str], context: str) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_value(item, warnings, f"{context}.{key}") for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item, warnings, context) for item in value]
    if isinstance(value, str) and is_local_path(value):
        warnings.append(f"Removed local path from {context}.")
        return ""
    return value


def clone_project(
    project: Project,
    *,
    name: str,
    include_outputs: bool,
    include_run_history: bool,
    preserve_settings: bool,
    reset_runtime: bool,
) -> tuple[Project, dict[str, dict[str, str]], list[str]]:
    project_copy, warnings = sanitized_project_copy(
        project,
        include_outputs=include_outputs,
        include_settings=preserve_settings,
        include_run_history=include_run_history,
        reset_runtime=reset_runtime,
        preserve_ids=True,
    )
    project_copy, id_map, remap_warnings = remap_project_ids(project_copy, include_outputs=include_outputs)
    warnings.extend(remap_warnings)
    project_copy.name = name
    project_copy.id = new_id("project")
    project_copy.created_at = datetime.now(timezone.utc)
    project_copy.updated_at = datetime.now(timezone.utc)
    return project_copy, id_map, warnings


def remap_project_ids(project: Project, *, include_outputs: bool) -> tuple[Project, dict[str, dict[str, str]], list[str]]:
    warnings: list[str] = []
    node_map = {node.id: new_id("node") for node in project.nodes}
    edge_map = {edge.id: new_id("edge") for edge in project.edges}
    asset_map = {asset.id: new_id("asset") for asset in project.assets}

    for node in project.nodes:
        old_id = node.id
        node.id = node_map[old_id]
        node.status = NodeStatus.idle
        node.error_message = None
        if include_outputs:
            node.output_asset_ids = [asset_map[asset_id] for asset_id in node.output_asset_ids if asset_id in asset_map]
            if len(node.output_asset_ids) != len(set(node.output_asset_ids)):
                warnings.append(f"Node {old_id} had duplicate output asset references.")
        else:
            node.output_asset_ids = []
            node.output_urls = []
            node.last_run = {}

    for edge in project.edges:
        edge.id = edge_map[edge.id]
        edge.source_node_id = node_map.get(edge.source_node_id, edge.source_node_id)
        edge.target_node_id = node_map.get(edge.target_node_id, edge.target_node_id)
        edge.source = None
        edge.target = None
        edge.source_node = None
        edge.target_node = None
        edge.sourceNodeId = None
        edge.targetNodeId = None
        edge.from_node = None
        edge.to = None

    for asset in project.assets:
        old_id = asset.id
        asset.id = asset_map[old_id]
        if isinstance(asset.metadata, dict):
            source_node_id = asset.metadata.get("source_node_id")
            if source_node_id in node_map:
                asset.metadata["source_node_id"] = node_map[source_node_id]

    if not include_outputs:
        project.assets = []
    project.runs = remap_runs(project.runs, node_map, asset_map) if project.runs else []

    return project, {"nodes": node_map, "edges": edge_map, "assets": asset_map}, warnings


def remap_runs(runs: list[dict[str, Any]], node_map: dict[str, str], asset_map: dict[str, str]) -> list[dict[str, Any]]:
    remapped: list[dict[str, Any]] = []
    for run in runs:
        item = deepcopy(run)
        if item.get("id"):
            item["id"] = new_id("run")
        if isinstance(item.get("node_id"), str) and item["node_id"] in node_map:
            item["node_id"] = node_map[item["node_id"]]
        if isinstance(item.get("node_ids"), list):
            item["node_ids"] = [node_map.get(node_id, node_id) for node_id in item["node_ids"]]
        if isinstance(item.get("asset_ids"), list):
            item["asset_ids"] = [asset_map.get(asset_id, asset_id) for asset_id in item["asset_ids"]]
        if isinstance(item.get("steps"), list):
            for step in item["steps"]:
                if isinstance(step, dict) and isinstance(step.get("node_id"), str):
                    step["node_id"] = node_map.get(step["node_id"], step["node_id"])
        remapped.append(item)
    return remapped


def is_local_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def is_local_path(value: str) -> bool:
    if not value or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        return False
    return PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()


def json_size_limit_bytes(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    return settings.max_import_json_mb * 1024 * 1024
