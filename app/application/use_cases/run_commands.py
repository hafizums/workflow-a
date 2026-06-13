from __future__ import annotations

from app.application.use_cases.queue_jobs import JobManagementUseCase, QueueNodeJobUseCase, QueueWorkflowJobUseCase


class QueueNodeRunCommand(QueueNodeJobUseCase):
    pass


class QueueWorkflowRunCommand(QueueWorkflowJobUseCase):
    pass


class CancelJobCommand:
    def __init__(self, jobs: JobManagementUseCase | None = None):
        self.jobs = jobs or JobManagementUseCase()

    async def execute(self, job_id: str):
        return await self.jobs.cancel(job_id)


class RetryJobCommand:
    def __init__(self, jobs: JobManagementUseCase | None = None):
        self.jobs = jobs or JobManagementUseCase()

    async def execute(self, job_id: str):
        return await self.jobs.retry(job_id)


class ClearCompletedJobsCommand:
    def __init__(self, jobs: JobManagementUseCase | None = None):
        self.jobs = jobs or JobManagementUseCase()

    async def execute(self):
        return await self.jobs.clear_completed()


class WriteRunHistoryCommand:
    """Marker command for run-history writes that still happen in run_manager today."""

    async def execute(self, project, run_entry: dict):
        project.runs = [run_entry, *(project.runs or [])][:100]
        return project

