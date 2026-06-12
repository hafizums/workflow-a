from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import CanvasNode, RunJob
from app.services import project_store
from app.services.run_manager import RunManagerError, run_manager

router = APIRouter(prefix="/api/projects/{project_id}/runs", tags=["run-snapshots"])


def _find_run(project, run_id: str) -> dict:
    run = next((item for item in project.runs if item.get("id") == run_id or item.get("run_id") == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail="Run snapshot not found")
    return run


@router.post("/{run_id}/rerun", response_model=RunJob)
async def rerun_snapshot(project_id: str, run_id: str):
    try:
        project = await project_store.load_project(project_id)
        run = _find_run(project, run_id)
        node_id = run.get("node_id") or (run.get("node_ids") or [None])[0]
        if not node_id:
            raise HTTPException(status_code=400, detail="Run snapshot does not reference a node to rerun")
        return await run_manager.queue_node_run(project_id, node_id, save_to_project=True)
    except project_store.ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except project_store.ProjectStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RunManagerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/clone-node", response_model=CanvasNode)
async def clone_run_node(project_id: str, run_id: str):
    try:
        project = await project_store.load_project(project_id)
        run = _find_run(project, run_id)
        node_id = run.get("node_id") or (run.get("node_ids") or [None])[0]
        node = next((item for item in project.nodes if item.id == node_id), None)
        if node is None:
            raise HTTPException(status_code=404, detail="Run source node not found")
        clone = node.model_copy(deep=True)
        clone.id = f"{node.id}_clone_{len(project.nodes) + 1}"
        clone.title = f"{node.title} Clone"
        clone.x = node.x + 340
        clone.y = node.y + 40
        clone.output_asset_ids = []
        clone.output_urls = []
        clone.last_run = {"cloned_from_run_id": run_id}
        clone.status = "idle"
        clone.error_message = None
        project.nodes.append(clone)
        await project_store.save_project(project)
        return clone
    except project_store.ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except project_store.ProjectStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
