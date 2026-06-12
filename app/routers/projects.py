from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.schemas import CostGuardSettings, NodeType, Project, ProjectCreate, ProjectSettings, ProjectSettingsUpdate, ProjectUpdate
from app.services import project_store
from app.services.registry import get_model_for_node

router = APIRouter(prefix="/api/projects", tags=["projects"])


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


def validate_project_settings(settings: ProjectSettings) -> ProjectSettings:
    for node_type_value, model_id in settings.model_overrides.items():
        try:
            node_type = NodeType(node_type_value)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown node type for model override: {node_type_value}",
            ) from exc

        model = get_model_for_node(node_type, model_id)
        if model is None:
            raise HTTPException(
                status_code=400,
                detail=f"Model {model_id} is not registered for node type {node_type.value}.",
            )
        if not model.enabled:
            raise HTTPException(
                status_code=400,
                detail=model.enabled_reason or f"Model {model_id} is disabled for node type {node_type.value}.",
            )

    return settings


def merge_settings(current: ProjectSettings, payload: ProjectSettingsUpdate) -> ProjectSettings:
    data = current.model_dump()
    if payload.model_overrides is not None:
        data["model_overrides"] = payload.model_overrides
    if payload.cost_guard is not None:
        cost_guard_data = current.cost_guard.model_dump()
        cost_guard_data.update(payload.cost_guard.model_dump(exclude_unset=True))
        try:
            data["cost_guard"] = CostGuardSettings.model_validate(cost_guard_data)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
    return validate_project_settings(ProjectSettings.model_validate(data))


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


@router.get("/{project_id}/settings", response_model=ProjectSettings)
async def get_project_settings(project_id: str):
    try:
        project = await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    return project.settings


@router.put("/{project_id}/settings", response_model=ProjectSettings)
async def update_project_settings(project_id: str, payload: ProjectSettingsUpdate):
    try:
        project = await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc

    project.settings = merge_settings(project.settings, payload)
    await project_store.save_project(project)
    return project.settings


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: str, payload: ProjectUpdate):
    try:
        project = await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc

    for key in payload.model_fields_set:
        value = getattr(payload, key)
        if key == "settings" and value is not None:
            value = validate_project_settings(value)
        setattr(project, key, value)
    return await project_store.save_project(project)


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    try:
        await project_store.delete_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    return {"ok": True}
