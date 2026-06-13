from __future__ import annotations

from app.infrastructure.queue.in_memory_job_queue import InMemoryJobQueue


class QueueNodeJobUseCase:
    def __init__(self, queue: InMemoryJobQueue | None = None):
        self._queue = queue or InMemoryJobQueue()

    async def queue(self, *, project_id: str, node_id: str, save_to_project: bool = True):
        return await self._queue.queue_node_run(project_id=project_id, node_id=node_id, save_to_project=save_to_project)


class QueueWorkflowJobUseCase:
    def __init__(self, queue: InMemoryJobQueue | None = None):
        self._queue = queue or InMemoryJobQueue()

    async def queue(self, *, project_id: str, mode: str, node_id: str | None = None):
        return await self._queue.queue_workflow_run(project_id=project_id, mode=mode, node_id=node_id)


class JobManagementUseCase:
    def __init__(self, queue: InMemoryJobQueue | None = None):
        self._queue = queue or InMemoryJobQueue()

    async def list_jobs(self, project_id: str | None = None, status: str | None = None, limit: int = 50):
        return await self._queue.list_jobs(project_id=project_id, status=status, limit=limit)

    async def get_job(self, job_id: str):
        return await self._queue.get_job(job_id)

    async def cancel(self, job_id: str):
        return await self._queue.cancel_job(job_id)

    async def retry(self, job_id: str):
        return await self._queue.retry_job(job_id)

    async def clear_completed(self):
        return await self._queue.clear_completed()
