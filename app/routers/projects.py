from fastapi import APIRouter, HTTPException

from app.schemas import Project, ProjectCreate, ProjectUpdate
from app.services import project_store

router = APIRouter(prefix="/api/projects", tags=["projects"])


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


@router.get("", response_model=list[Project])
async def list_projects():
    return await project_store.list_projects()


@router.post("", response_model=Project)
async def create_project(payload: ProjectCreate):
    project = Project(name=payload.name, description=payload.description)
    return await project_store.save_project(project)


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    try:
        return await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: str, payload: ProjectUpdate):
    try:
        project = await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc

    for key in payload.model_fields_set:
        setattr(project, key, getattr(payload, key))
    return await project_store.save_project(project)


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    try:
        await project_store.delete_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    return {"ok": True}
