from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas import ExportPackageManifest
from app.services import project_store
from app.services.export_package import ExportPackageError, create_export_package, get_export_package

router = APIRouter(prefix="/api/projects/{project_id}", tags=["export-packages"])


class ExportPackageRequest(BaseModel):
    asset_ids: list[str] = Field(default_factory=list)


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


@router.post("/export-package", response_model=ExportPackageManifest)
async def create_package(project_id: str, payload: ExportPackageRequest | None = None):
    try:
        project = await project_store.load_project(project_id)
        manifest = create_export_package(project, asset_ids=(payload.asset_ids if payload else None))
        await project_store.save_project(project)
        return manifest
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    except ExportPackageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/export-package/{package_id}", response_model=ExportPackageManifest)
async def read_package(project_id: str, package_id: str):
    try:
        project = await project_store.load_project(project_id)
        return get_export_package(project, package_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    except ExportPackageError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
