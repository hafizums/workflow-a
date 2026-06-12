from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import QueueNodeRunRequest, QueueWorkflowRunRequest, RunJob
from app.services import project_store
from app.services.run_manager import JobNotFoundError, RunManagerError, run_manager

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def job_error(exc: Exception) -> HTTPException:
    if isinstance(exc, JobNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, project_store.ProjectNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, project_store.InvalidProjectIdError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, (RunManagerError, project_store.ProjectStoreError)):
        detail = exc.args[0] if exc.args else str(exc)
        return HTTPException(status_code=400, detail=detail)
    return HTTPException(status_code=500, detail="Run manager error")


@router.get("", response_model=list[RunJob])
async def list_jobs(project_id: str | None = None, status: str | None = None, limit: int = 50):
    return await run_manager.list_jobs(project_id=project_id, status=status, limit=limit)


@router.get("/{job_id}", response_model=RunJob)
async def get_job(job_id: str):
    try:
        return await run_manager.get_job(job_id)
    except Exception as exc:
        raise job_error(exc) from exc


@router.post("/{job_id}/cancel", response_model=RunJob)
async def cancel_job(job_id: str):
    try:
        return await run_manager.cancel_job(job_id)
    except Exception as exc:
        raise job_error(exc) from exc


@router.post("/{job_id}/retry", response_model=RunJob)
async def retry_job(job_id: str):
    try:
        return await run_manager.retry_job(job_id)
    except Exception as exc:
        raise job_error(exc) from exc


@router.delete("/completed")
async def clear_completed_jobs():
    return await run_manager.clear_completed()


@router.post("/node", response_model=RunJob)
async def queue_node_run(payload: QueueNodeRunRequest):
    try:
        return await run_manager.queue_node_run(
            project_id=payload.project_id,
            node_id=payload.node_id,
            save_to_project=payload.save_to_project,
        )
    except Exception as exc:
        raise job_error(exc) from exc


@router.post("/workflow/selected", response_model=RunJob)
async def queue_selected_workflow(payload: QueueWorkflowRunRequest):
    try:
        return await run_manager.queue_workflow_run(
            project_id=payload.project_id,
            mode="selected",
            node_id=payload.node_id,
        )
    except Exception as exc:
        raise job_error(exc) from exc


@router.post("/workflow/from-node/{node_id}", response_model=RunJob)
async def queue_from_node_workflow(node_id: str, payload: QueueWorkflowRunRequest):
    try:
        return await run_manager.queue_workflow_run(
            project_id=payload.project_id,
            mode="from_node",
            node_id=node_id,
        )
    except Exception as exc:
        raise job_error(exc) from exc


@router.post("/workflow/all", response_model=RunJob)
async def queue_all_workflow(payload: QueueWorkflowRunRequest):
    try:
        return await run_manager.queue_workflow_run(project_id=payload.project_id, mode="whole_graph")
    except Exception as exc:
        raise job_error(exc) from exc
