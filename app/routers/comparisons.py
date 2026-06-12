from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import ArtifactRole, ComparisonSet, ModelCompareRequest
from app.services import project_store
from app.services.artifact_service import ArtifactError, set_artifact_role
from app.services.model_compare import CompareError, queue_model_comparison

router = APIRouter(prefix="/api/projects/{project_id}", tags=["comparisons"])


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


@router.post("/nodes/{node_id}/compare-models", response_model=ComparisonSet)
async def compare_models(project_id: str, node_id: str, payload: ModelCompareRequest):
    try:
        project = await project_store.load_project(project_id)
        request = payload.model_copy(update={"project_id": project_id, "source_node_id": node_id})
        return await queue_model_comparison(project, request)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    except CompareError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/comparisons", response_model=list[ComparisonSet])
async def list_comparisons(project_id: str):
    try:
        project = await project_store.load_project(project_id)
        return project.comparison_sets
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc


@router.get("/comparisons/{comparison_id}", response_model=ComparisonSet)
async def get_comparison(project_id: str, comparison_id: str):
    try:
        project = await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    comparison = next((item for item in project.comparison_sets if item.id == comparison_id), None)
    if comparison is None:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return comparison


@router.post("/comparisons/{comparison_id}/winner/{asset_id}", response_model=ComparisonSet)
async def choose_comparison_winner(project_id: str, comparison_id: str, asset_id: str):
    try:
        project = await project_store.load_project(project_id)
        comparison = next((item for item in project.comparison_sets if item.id == comparison_id), None)
        if comparison is None:
            raise HTTPException(status_code=404, detail="Comparison not found")
        if asset_id not in comparison.artifact_ids:
            raise HTTPException(status_code=400, detail="Artifact is not part of this comparison")
        set_artifact_role(project, asset_id, ArtifactRole.winner)
        comparison.winner_asset_id = asset_id
        await project_store.save_project(project)
        return comparison
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    except ArtifactError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
