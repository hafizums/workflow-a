from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.application.use_cases.templates import TemplateUseCase
from app.schemas import (
    CreateProjectFromTemplateRequest,
    Project,
    TemplateFromProjectRequest,
    WorkflowTemplate,
    WorkflowTemplateCreate,
    WorkflowTemplateUpdate,
)
from app.services import project_store, template_store
from app.services.project_validation import ProjectValidationError

router = APIRouter(prefix="/api/templates", tags=["templates"])


def template_error(exc: Exception) -> HTTPException:
    if isinstance(exc, template_store.TemplateNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, template_store.BuiltinTemplateError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, (template_store.TemplateStoreError, ProjectValidationError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Template storage error")


@router.get("", response_model=list[WorkflowTemplate])
async def list_templates(category: str | None = None, builtin: bool | None = None):
    try:
        return await TemplateUseCase().list(category=category, builtin=builtin)
    except Exception as exc:
        raise template_error(exc) from exc


@router.post("", response_model=WorkflowTemplate)
async def create_template(payload: WorkflowTemplateCreate):
    try:
        return await TemplateUseCase().create(payload)
    except Exception as exc:
        raise template_error(exc) from exc


@router.post("/from-project/{project_id}", response_model=WorkflowTemplate)
async def create_template_from_project(project_id: str, payload: TemplateFromProjectRequest):
    try:
        return await TemplateUseCase().create_from_project(project_id, payload)
    except project_store.ProjectStoreError as exc:
        raise HTTPException(status_code=404 if isinstance(exc, project_store.ProjectNotFoundError) else 400, detail=str(exc)) from exc
    except Exception as exc:
        raise template_error(exc) from exc


@router.get("/{template_id}", response_model=WorkflowTemplate)
async def get_template(template_id: str):
    try:
        return await TemplateUseCase().get(template_id)
    except Exception as exc:
        raise template_error(exc) from exc


@router.put("/{template_id}", response_model=WorkflowTemplate)
async def update_template(template_id: str, payload: WorkflowTemplateUpdate):
    try:
        return await TemplateUseCase().update(template_id, payload)
    except Exception as exc:
        raise template_error(exc) from exc


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    try:
        await TemplateUseCase().delete(template_id)
    except Exception as exc:
        raise template_error(exc) from exc
    return {"ok": True}


@router.post("/{template_id}/create-project", response_model=Project)
async def create_project_from_template(template_id: str, payload: CreateProjectFromTemplateRequest):
    try:
        return await TemplateUseCase().create_project_from_template(template_id, payload)
    except Exception as exc:
        raise template_error(exc) from exc
