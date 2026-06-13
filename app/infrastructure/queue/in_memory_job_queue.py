from __future__ import annotations

from typing import Any

from app.services.run_manager import run_manager


class InMemoryJobQueue:
    """Job queue adapter that delegates to the existing in-memory run manager."""

    def __init__(self, manager: Any | None = None):
        self.manager = manager or run_manager

    async def list_jobs(self, project_id: str | None = None, status: str | None = None, limit: int = 50):
        return await self.manager.list_jobs(project_id=project_id, status=status, limit=limit)

    async def get_job(self, job_id: str):
        return await self.manager.get_job(job_id)

    async def queue_node_run(self, project_id: str, node_id: str, save_to_project: bool = True):
        return await self.manager.queue_node_run(project_id=project_id, node_id=node_id, save_to_project=save_to_project)

    async def queue_workflow_run(self, project_id: str, mode: str, node_id: str | None = None):
        return await self.manager.queue_workflow_run(project_id=project_id, mode=mode, node_id=node_id)

    async def cancel_job(self, job_id: str):
        return await self.manager.cancel_job(job_id)

    async def retry_job(self, job_id: str):
        return await self.manager.retry_job(job_id)

    async def clear_completed(self):
        return await self.manager.clear_completed()
