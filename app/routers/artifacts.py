from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import ArtifactRatingUpdate, ArtifactRole, ArtifactRoleUpdate, AssetKind, BranchArtifactRequest
from app.services import artifact_service, project_store
from app.services.branching import BranchError, create_branch_from_artifact

router = APIRouter(prefix="/api/projects/{project_id}/artifacts", tags=["artifacts"])


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


async def load_project_or_404(project_id: str):
    try:
        return await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc


@router.get("")
async def list_artifacts(project_id: str, kind: AssetKind | None = None, role: ArtifactRole | None = None):
    project = await load_project_or_404(project_id)
    return artifact_service.list_artifacts(project, kind=kind, role=role)


@router.get("/{asset_id}")
async def get_artifact(project_id: str, asset_id: str):
    project = await load_project_or_404(project_id)
    try:
        return artifact_service.get_artifact(project, asset_id)
    except artifact_service.ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{asset_id}/lineage")
async def get_lineage(project_id: str, asset_id: str):
    project = await load_project_or_404(project_id)
    try:
        return artifact_service.artifact_lineage_tree(project, asset_id)
    except artifact_service.ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{asset_id}/pin")
async def pin_artifact(project_id: str, asset_id: str):
    project = await load_project_or_404(project_id)
    try:
        artifact = artifact_service.pin_artifact(project, asset_id, True)
    except artifact_service.ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await project_store.save_project(project)
    return artifact


@router.post("/{asset_id}/unpin")
async def unpin_artifact(project_id: str, asset_id: str):
    project = await load_project_or_404(project_id)
    try:
        artifact = artifact_service.pin_artifact(project, asset_id, False)
    except artifact_service.ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await project_store.save_project(project)
    return artifact


@router.post("/{asset_id}/reject")
async def reject_artifact(project_id: str, asset_id: str):
    project = await load_project_or_404(project_id)
    try:
        artifact = artifact_service.reject_artifact(project, asset_id, True)
    except artifact_service.ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await project_store.save_project(project)
    return artifact


@router.post("/{asset_id}/restore")
async def restore_artifact(project_id: str, asset_id: str):
    project = await load_project_or_404(project_id)
    try:
        artifact = artifact_service.reject_artifact(project, asset_id, False)
    except artifact_service.ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await project_store.save_project(project)
    return artifact


@router.post("/{asset_id}/role")
async def set_role(project_id: str, asset_id: str, payload: ArtifactRoleUpdate):
    project = await load_project_or_404(project_id)
    try:
        artifact = artifact_service.set_artifact_role(project, asset_id, payload.role)
    except artifact_service.ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await project_store.save_project(project)
    return artifact


@router.post("/{asset_id}/rating")
async def set_rating(project_id: str, asset_id: str, payload: ArtifactRatingUpdate):
    project = await load_project_or_404(project_id)
    try:
        artifact = artifact_service.rate_artifact(project, asset_id, payload.rating)
    except artifact_service.ArtifactError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await project_store.save_project(project)
    return artifact


@router.post("/{asset_id}/branch")
async def branch_artifact(project_id: str, asset_id: str, payload: BranchArtifactRequest):
    project = await load_project_or_404(project_id)
    try:
        node, edge = create_branch_from_artifact(
            project,
            artifact_id=asset_id,
            target_node_type=payload.target_node_type,
            target_input_name=payload.target_input_name,
            title=payload.title,
        )
    except (artifact_service.ArtifactError, BranchError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await project_store.save_project(project)
    return {"node": node, "edge": edge}
