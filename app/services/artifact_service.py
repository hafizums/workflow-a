from __future__ import annotations

from typing import Any

from app.schemas import ArtifactRole, Asset, AssetKind, Project


class ArtifactError(ValueError):
    pass


def get_artifact(project: Project, asset_id: str) -> Asset:
    asset = next((item for item in project.assets if item.id == asset_id), None)
    if asset is None:
        raise ArtifactError("Artifact not found")
    return asset


def list_artifacts(
    project: Project,
    kind: AssetKind | None = None,
    role: ArtifactRole | None = None,
) -> list[Asset]:
    artifacts = list(project.assets)
    if kind is not None:
        artifacts = [asset for asset in artifacts if asset.kind == kind]
    if role is not None:
        artifacts = [asset for asset in artifacts if asset.view.role == role]
    return artifacts


def set_artifact_role(project: Project, asset_id: str, role: ArtifactRole) -> Asset:
    asset = get_artifact(project, asset_id)
    asset.view.role = role
    if role == ArtifactRole.winner:
        asset.view.favorite = True
        asset.view.rejected = False
    return asset


def pin_artifact(project: Project, asset_id: str, pinned: bool = True) -> Asset:
    asset = get_artifact(project, asset_id)
    asset.view.pinned = pinned
    return asset


def reject_artifact(project: Project, asset_id: str, rejected: bool = True) -> Asset:
    asset = get_artifact(project, asset_id)
    asset.view.rejected = rejected
    if rejected:
        asset.view.favorite = False
        if asset.view.role == ArtifactRole.winner:
            asset.view.role = ArtifactRole.intermediate
    return asset


def rate_artifact(project: Project, asset_id: str, rating: int | None) -> Asset:
    asset = get_artifact(project, asset_id)
    if rating is not None and not 1 <= rating <= 5:
        raise ArtifactError("Rating must be between 1 and 5.")
    asset.view.rating = rating
    return asset


def artifact_lineage_tree(project: Project, asset_id: str, visited: set[str] | None = None) -> dict[str, Any]:
    visited = visited or set()
    asset = get_artifact(project, asset_id)
    if asset.id in visited:
        return {
            "asset_id": asset.id,
            "filename": asset.filename,
            "kind": asset.kind.value,
            "role": asset.view.role.value,
            "cycle_detected": True,
            "upstream_assets": [],
        }
    visited.add(asset.id)
    source_node = next((node for node in project.nodes if node.id == asset.lineage.source_node_id), None)
    source_assets = [
        item
        for item in project.assets
        if item.id in set(asset.lineage.source_artifact_ids or [])
    ]
    upstream = [
        artifact_lineage_tree(project, item.id, set(visited))
        for item in source_assets
        if item.id != asset.id
    ]
    return {
        "asset_id": asset.id,
        "filename": asset.filename,
        "kind": asset.kind.value,
        "role": asset.view.role.value,
        "source_node_id": asset.lineage.source_node_id,
        "source_run_id": asset.lineage.source_run_id,
        "source_job_id": asset.lineage.source_job_id,
        "source_model_id": asset.lineage.source_model_id,
        "source_input_keys": asset.lineage.source_input_keys,
        "source_node": source_node.model_dump(mode="json") if source_node else None,
        "upstream_assets": upstream,
    }
