from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
        return await template_store.list_templates(category=category, builtin=builtin)
    except Exception as exc:
        raise template_error(exc) from exc


@router.post("", response_model=WorkflowTemplate)
async def create_template(payload: WorkflowTemplateCreate):
    try:
        return await template_store.create_template(payload)
    except Exception as exc:
        raise template_error(exc) from exc


@router.post("/from-project/{project_id}", response_model=WorkflowTemplate)
async def create_template_from_project(project_id: str, payload: TemplateFromProjectRequest):
    try:
        project = await project_store.load_project(project_id)
        return await template_store.create_template_from_project(
            project,
            name=payload.name,
            description=payload.description,
            category=payload.category,
            tags=payload.tags,
            include_outputs=payload.include_outputs,
            include_settings=payload.include_settings,
        )
    except project_store.ProjectStoreError as exc:
        raise HTTPException(status_code=404 if isinstance(exc, project_store.ProjectNotFoundError) else 400, detail=str(exc)) from exc
    except Exception as exc:
        raise template_error(exc) from exc


@router.get("/{template_id}", response_model=WorkflowTemplate)
async def get_template(template_id: str):
    try:
        return await template_store.get_template(template_id)
    except Exception as exc:
        raise template_error(exc) from exc


@router.put("/{template_id}", response_model=WorkflowTemplate)
async def update_template(template_id: str, payload: WorkflowTemplateUpdate):
    try:
        return await template_store.update_template(template_id, payload.model_dump(exclude_unset=True))
    except Exception as exc:
        raise template_error(exc) from exc


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    try:
        await template_store.delete_template(template_id)
    except Exception as exc:
        raise template_error(exc) from exc
    return {"ok": True}


@router.post("/{template_id}/create-project", response_model=Project)
async def create_project_from_template(template_id: str, payload: CreateProjectFromTemplateRequest):
    try:
        template = await template_store.get_template(template_id)
        return await template_store.create_project_from_template(
            template,
            name=payload.name,
            description=payload.description,
        )
    except Exception as exc:
        raise template_error(exc) from exc
