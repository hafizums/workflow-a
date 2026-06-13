from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.application.use_cases.errors import ApplicationError
from app.application.use_cases.workflow import PlanWorkflowUseCase, RunWorkflowUseCase

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class RunSelectedRequest(BaseModel):
    node_id: str


def application_error(exc: ApplicationError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/{project_id}/plan")
async def get_workflow_plan(project_id: str, mode: str = "whole_graph", node_id: str | None = None):
    try:
        return await PlanWorkflowUseCase().plan(project_id, mode=mode, node_id=node_id)
    except ApplicationError as exc:
        raise application_error(exc) from exc


@router.post("/{project_id}/run-selected")
async def run_selected_node(project_id: str, payload: RunSelectedRequest):
    try:
        return await RunWorkflowUseCase().run_selected(project_id, payload.node_id)
    except ApplicationError as exc:
        raise application_error(exc) from exc


@router.post("/{project_id}/run-from-node/{node_id}")
async def run_from_node(project_id: str, node_id: str):
    try:
        return await RunWorkflowUseCase().run_from_node(project_id, node_id)
    except ApplicationError as exc:
        raise application_error(exc) from exc


@router.post("/{project_id}/run-all")
async def run_all(project_id: str):
    try:
        return await RunWorkflowUseCase().run_all(project_id)
    except ApplicationError as exc:
        raise application_error(exc) from exc


@router.get("/{project_id}/runs")
async def list_workflow_runs(project_id: str):
    try:
        return await RunWorkflowUseCase().list_runs(project_id)
    except ApplicationError as exc:
        raise application_error(exc) from exc

