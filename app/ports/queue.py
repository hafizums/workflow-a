from __future__ import annotations

from typing import Protocol

from app.schemas import RunJob


class JobQueue(Protocol):
    async def list_jobs(self, project_id: str | None = None, status: str | None = None, limit: int = 50) -> list[RunJob]:
        ...

    async def get_job(self, job_id: str) -> RunJob:
        ...

    async def queue_node_run(self, project_id: str, node_id: str, save_to_project: bool = True) -> RunJob:
        ...

    async def queue_workflow_run(self, project_id: str, mode: str, node_id: str | None = None) -> RunJob:
        ...

    async def cancel_job(self, job_id: str) -> RunJob:
        ...

    async def retry_job(self, job_id: str) -> RunJob:
        ...

    async def clear_completed(self) -> dict[str, int]:
        ...

