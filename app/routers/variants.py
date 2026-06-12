from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import ArtifactRole, VariantRunRequest, VariantSet
from app.services import project_store
from app.services.artifact_service import ArtifactError, set_artifact_role
from app.services.run_manager import RunManagerError, run_manager
from app.services.variant_runner import VariantError, queue_variant_set

router = APIRouter(prefix="/api/projects/{project_id}", tags=["variants"])


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


@router.post("/nodes/{node_id}/variants", response_model=VariantSet)
async def create_variants(project_id: str, node_id: str, payload: VariantRunRequest):
    try:
        project = await project_store.load_project(project_id)
        request = payload.model_copy(update={"project_id": project_id, "node_id": node_id})
        return await queue_variant_set(project, request)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    except VariantError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/variants", response_model=list[VariantSet])
async def list_variants(project_id: str):
    try:
        project = await project_store.load_project(project_id)
        return project.variant_sets
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc


@router.get("/variants/{variant_set_id}", response_model=VariantSet)
async def get_variant_set(project_id: str, variant_set_id: str):
    try:
        project = await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    variant_set = next((item for item in project.variant_sets if item.id == variant_set_id), None)
    if variant_set is None:
        raise HTTPException(status_code=404, detail="Variant set not found")
    return variant_set


@router.post("/variants/{variant_set_id}/promote/{asset_id}", response_model=VariantSet)
async def promote_variant(project_id: str, variant_set_id: str, asset_id: str):
    try:
        project = await project_store.load_project(project_id)
        variant_set = next((item for item in project.variant_sets if item.id == variant_set_id), None)
        if variant_set is None:
            raise HTTPException(status_code=404, detail="Variant set not found")
        if asset_id not in variant_set.artifact_ids:
            raise HTTPException(status_code=400, detail="Artifact is not part of this variant set")
        set_artifact_role(project, asset_id, ArtifactRole.winner)
        await project_store.save_project(project)
        return variant_set
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    except ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/variants/{variant_set_id}/cancel", response_model=VariantSet)
async def cancel_variant_set(project_id: str, variant_set_id: str):
    try:
        project = await project_store.load_project(project_id)
        variant_set = next((item for item in project.variant_sets if item.id == variant_set_id), None)
        if variant_set is None:
            raise HTTPException(status_code=404, detail="Variant set not found")
        for job_id in variant_set.job_ids:
            try:
                await run_manager.cancel_job(job_id)
            except RunManagerError as exc:
                variant_set.errors.append({"job_id": job_id, "message": str(exc)})
        variant_set.status = "cancel_requested"
        await project_store.save_project(project)
        return variant_set
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
