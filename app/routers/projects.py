import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.schemas import (
    CostGuardSettings,
    Project,
    ProjectCreate,
    ProjectDuplicateRequest,
    ProjectImportRequest,
    ProjectImportResponse,
    ProjectSettings,
    ProjectSettingsUpdate,
    ProjectUpdate,
)
from app.services import project_store
from app.services import portable_project
from app.services.project_validation import ProjectValidationError, validate_project_settings

router = APIRouter(prefix="/api/projects", tags=["projects"])


def project_error(exc: project_store.ProjectStoreError) -> HTTPException:
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Project storage error")


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
    try:
        return validate_project_settings(ProjectSettings.model_validate(data))
    except ProjectValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[Project])
async def list_projects():
    return await project_store.list_projects()


@router.post("", response_model=Project)
async def create_project(payload: ProjectCreate):
    project = Project(name=payload.name, description=payload.description)
    return await project_store.save_project(project)


@router.post("/import", response_model=ProjectImportResponse)
async def import_project(request: Request):
    try:
        payload = await read_import_payload(request)
        return await portable_project.import_project(
            payload.import_data,
            name=payload.name,
            include_outputs=payload.include_outputs,
            include_run_history=payload.include_run_history,
        )
    except portable_project.PortableProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Import file must contain valid JSON.") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc


async def read_import_payload(request: Request) -> ProjectImportRequest:
    content_type = request.headers.get("content-type", "")
    max_bytes = portable_project.json_size_limit_bytes()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "read"):
            raise portable_project.PortableProjectError("Multipart import requires a file field.")
        raw = await upload.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise portable_project.PortableProjectError("Import JSON exceeds the size limit.")
        data = json.loads(raw.decode("utf-8"))
        return ProjectImportRequest(
            import_data=data,
            name=form.get("name") or None,
            include_outputs=parse_bool(form.get("include_outputs"), True),
            include_run_history=parse_bool(form.get("include_run_history"), False),
        )

    raw = await request.body()
    if len(raw) > max_bytes:
        raise portable_project.PortableProjectError("Import JSON exceeds the size limit.")
    body = json.loads(raw.decode("utf-8")) if raw else {}
    if "import_data" in body:
        return ProjectImportRequest.model_validate(body)
    return ProjectImportRequest(import_data=body)


def parse_bool(value, default: bool) -> bool:
    if value is None or value == "":
        return default
    return str(value).lower() in {"1", "true", "yes", "on"}


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    try:
        return await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc


@router.get("/{project_id}/export")
async def export_project(
    project_id: str,
    include_outputs: bool = True,
    include_settings: bool = True,
    include_run_history: bool = False,
):
    try:
        project = await project_store.load_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc

    data = portable_project.export_project(
        project,
        include_outputs=include_outputs,
        include_settings=include_settings,
        include_run_history=include_run_history,
    )
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f'attachment; filename="{portable_project.safe_export_filename(project)}"'},
    )


@router.post("/{project_id}/duplicate", response_model=ProjectImportResponse)
async def duplicate_project(project_id: str, payload: ProjectDuplicateRequest | None = None):
    payload = payload or ProjectDuplicateRequest()
    try:
        project = await project_store.load_project(project_id)
        return await portable_project.duplicate_project(
            project,
            name=payload.name,
            include_outputs=payload.include_outputs,
            include_run_history=payload.include_run_history,
        )
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    except portable_project.PortableProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
            try:
                value = validate_project_settings(value)
            except ProjectValidationError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        setattr(project, key, value)
    return await project_store.save_project(project)


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    try:
        await project_store.delete_project(project_id)
    except project_store.ProjectStoreError as exc:
        raise project_error(exc) from exc
    return {"ok": True}
