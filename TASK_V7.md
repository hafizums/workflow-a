# TASK_V7.md — Local Run Manager: Queue, Retry, Best-Effort Cancel, and Run History Cleanup

## Status assumption

This task comes after `TASK_V2.md`, `TASK_V3.md`, `TASK_V4.md`, `TASK_V5.md`, and `TASK_V6.md`.

Assume the current project already has:

- FastAPI backend.
- Vanilla HTML/CSS/JS frontend.
- Local JSON project storage.
- Local upload storage.
- WaveSpeed execution behind `WaveSpeedAdapter`.
- Node execution inside `app/services/node_runner.py`.
- Workflow planning/execution inside `app/services/workflow_resolver.py`.
- Project settings, model overrides, and local cost guard.
- Model catalog and local cost estimates.
- Export/import/duplicate/templates.
- Manual visual connector editor from `TASK_V6`.
- Workflow run history stored on the project.

Before coding, Codex must verify these assumptions from the current repo.

If any assumption is wrong, do not rewrite the app. Report the mismatch and make the smallest compatible change.

---

## High-level goal

Build **Local Run Manager v1**.

The current app can run single nodes and workflows, but runs are still mostly synchronous from the user’s point of view. V7 should make runs feel safer and more manageable:

```text
User starts node/workflow run
  ↓
Job appears in local run queue
  ↓
UI shows queued/running/success/error/cancel-requested
  ↓
User can cancel queued jobs or request cancel for active jobs
  ↓
User can retry failed/cancelled jobs
  ↓
Project run history is easier to read
```

This is a **local MVP run manager**, not a production queue system.

---

## Why this is TASK V7

The project already has many major workflow features:

- V2: workflow planning/execution.
- V3: model catalog, expanded models, media previews, and cost estimates.
- V4: project settings, model overrides, and cost guard UX.
- V5: import/export, duplication, and templates.
- V6: manual visual connector editor.

The next useful product step is to make long-running WaveSpeed operations easier to supervise.

Current known limitation to solve:

```text
WaveSpeed calls are synchronous request/response polling through the SDK.
There is no job queue, retries, cancellation, or progress streaming.
```

V7 should solve this locally without adding external infrastructure.

---

## Important constraints

Do not add:

- React.
- React Flow.
- Next.js.
- Tailwind.
- SQLite/Postgres.
- Auth.
- Billing integration.
- Multi-user accounts.
- Redis.
- Celery.
- RQ.
- Dramatiq.
- External job workers.
- WebSockets unless absolutely necessary.
- SSE unless absolutely necessary.
- More WaveSpeed models.
- Professional editing tools.
- ZIP asset bundling.
- Real usage metering.

Do not:

- Hardcode secrets.
- Commit `.env` or `WAVESPEED_API_KEY`.
- Break existing project JSON files.
- Break existing synchronous endpoints.
- Break project import/export/template behavior.
- Remove existing run buttons without replacing them safely.
- Claim in-flight WaveSpeed jobs can truly be cancelled unless the SDK/API supports that directly.

Keep:

- FastAPI backend.
- Vanilla frontend.
- Local JSON storage.
- Existing V2/V3/V4/V5/V6 behavior.
- WaveSpeed SDK usage only behind `WaveSpeedAdapter`.
- Backward compatibility with current project JSON files.

---

## Scope decision for V7

V7 should implement **local in-process run management** only.

### In scope

- In-memory local job registry.
- Single local worker queue by default.
- Optional small concurrency setting if simple, default `1`.
- Queue single-node runs.
- Queue workflow runs:
  - selected node
  - from selected node
  - whole graph
- Job status API.
- Job list API.
- Best-effort cancel:
  - cancel queued jobs immediately
  - mark active job as `cancel_requested`
  - stop between workflow steps when possible
  - do not promise hard cancellation of an active WaveSpeed SDK call
- Retry failed/cancelled jobs.
- Better frontend run manager panel.
- Job polling from frontend.
- Link jobs to project run history.
- Cleaner run history UI.
- Tests.
- Documentation updates.

### Out of scope

- Production background workers.
- Redis/Celery/RQ.
- Database-backed queue.
- Multi-user job isolation.
- True distributed cancellation.
- Live token-by-token or frame-by-frame progress.
- Payment/billing ledger.
- WebSocket/SSE streaming unless polling is impossible.
- More model categories.
- React/React Flow migration.

---

## Read these files first

Read these files before making a plan:

- `FINAL_PROJECT_CONTEXT.md`
- `PROJECT_SUMMARY.md`
- `TASK_V2.md`
- `TASK_V3.md`
- `TASK_V4.md`
- `TASK_V5.md`
- `TASK_V6.md`
- `README.md`
- `requirements.md`
- `CODEX_TASKS.md`
- `AGENTS.md` if present
- `app/main.py`
- `app/schemas.py`
- `app/core/config.py`
- `app/services/project_store.py`
- `app/services/project_validation.py`
- `app/services/model_catalog.py`
- `app/services/cost_estimator.py`
- `app/services/registry.py`
- `app/services/node_runner.py`
- `app/services/workflow_resolver.py`
- `app/services/wavespeed_adapter.py`
- `app/routers/runs.py`
- `app/routers/workflows.py`
- `app/routers/projects.py`
- `web/index.html`
- `web/app.js`
- `web/style.css`
- files under `tests/`

Also inspect:

- Current single-node run behavior.
- Current workflow run behavior.
- Current cost guard preflight behavior.
- Current project `runs` shape.
- Current node status updates.
- Current frontend workflow buttons.
- Current run history UI.
- Current tests for V2/V3/V4/V5/V6.

---

## Target backend design

Create:

```text
app/services/run_manager.py
app/routers/jobs.py
```

Add tests:

```text
tests/test_v7.py
```

Update if needed:

```text
app/main.py
app/schemas.py
app/routers/runs.py
app/routers/workflows.py
app/services/node_runner.py
app/services/workflow_resolver.py
app/services/project_store.py
```

---

## Core concepts

### Job kinds

Support these job kinds:

```text
single_node
workflow_selected
workflow_from_node
workflow_whole_graph
```

### Job statuses

Use these statuses:

```text
queued
running
success
error
cancel_requested
cancelled
```

Optional:

```text
skipped
```

Do not use fake progress percentages.

Use real step counts:

```text
progress_current = completed steps
progress_total = total planned steps
```

For a single active WaveSpeed call, show:

```text
running current step
```

Do not claim exact model progress.

---

## Suggested schemas

Add or adapt Pydantic models in `app/schemas.py`.

### RunJob

```python
class RunJob(BaseModel):
    id: str
    project_id: str
    kind: Literal[
        "single_node",
        "workflow_selected",
        "workflow_from_node",
        "workflow_whole_graph",
    ]
    status: Literal[
        "queued",
        "running",
        "success",
        "error",
        "cancel_requested",
        "cancelled",
    ]
    node_id: str | None = None
    mode: str | None = None
    request: dict[str, Any] = Field(default_factory=dict)
    plan: dict[str, Any] | None = None
    progress_current: int = 0
    progress_total: int = 0
    current_node_id: str | None = None
    node_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)
    output_urls: list[str] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancelled_at: datetime | None = None
```

Use the current project’s existing run history shape if it already has similar fields. Do not create two incompatible run formats.

### Queue request models

Suggested request models:

```python
class QueueNodeRunRequest(BaseModel):
    project_id: str
    node_id: str
    save_to_project: bool = True

class QueueWorkflowRunRequest(BaseModel):
    node_id: str | None = None
    mode: Literal["selected", "from_node", "whole_graph"]
```

If equivalent request models already exist, reuse them.

---

## New API endpoints

Add:

```text
GET    /api/jobs
GET    /api/jobs/{job_id}
POST   /api/jobs/{job_id}/cancel
POST   /api/jobs/{job_id}/retry
DELETE /api/jobs/completed
```

Add queued run endpoints:

```text
POST /api/jobs/node
POST /api/jobs/workflow/selected
POST /api/jobs/workflow/from-node/{node_id}
POST /api/jobs/workflow/all
```

Alternative acceptable design:

```text
POST /api/runs/node?queued=true
POST /api/workflows/{project_id}/run-selected?queued=true
POST /api/workflows/{project_id}/run-from-node/{node_id}?queued=true
POST /api/workflows/{project_id}/run-all?queued=true
```

But prefer separate `/api/jobs/...` endpoints because they keep current synchronous endpoints backward-compatible.

---

## Endpoint behavior

### `POST /api/jobs/node`

Input:

```json
{
  "project_id": "project_abc",
  "node_id": "node_abc",
  "save_to_project": true
}
```

Behavior:

1. Load project.
2. Validate node exists.
3. Run local cost estimate / cost guard preflight.
4. If blocked, return a clear error and do not queue the job.
5. If confirmation would be required in frontend, return `requires_confirmation=true` from preflight or rely on existing frontend confirmation before calling this endpoint.
6. Create job with status `queued`.
7. Add job to local queue.
8. Return job object.

### `POST /api/jobs/workflow/all`

Behavior:

1. Load project.
2. Build workflow plan with `workflow_resolver.py`.
3. Apply existing cost guard preflight.
4. If plan has errors or blocked cost guard, return clear error and do not queue.
5. Store the plan snapshot on the job.
6. Queue the job.
7. Return job object.

### `GET /api/jobs`

Return current in-memory jobs.

Support optional filters if simple:

```text
project_id
status
limit
```

### `GET /api/jobs/{job_id}`

Return one job.

### `POST /api/jobs/{job_id}/cancel`

Cancellation semantics:

- If job is `queued`, remove from pending queue if possible and mark `cancelled`.
- If job is `running`, mark `cancel_requested`.
- Active WaveSpeed SDK call may not stop immediately.
- Workflow jobs must stop before the next node step if `cancel_requested`.
- Single-node active jobs may only finish after the current SDK call returns.

Return the updated job.

### `POST /api/jobs/{job_id}/retry`

Retry semantics:

- Allowed for `error` and `cancelled`.
- Optional for `success`, but default should reject unless `force=true` is added later.
- Create a new job with a new ID.
- Copy the original request shape.
- Do not reuse old outputs.
- Re-run cost guard preflight.
- Return the new queued job.

### `DELETE /api/jobs/completed`

Clear completed in-memory jobs only:

```text
success
error
cancelled
```

Do not delete project-level persistent run history unless a separate explicit endpoint exists.

---

## Run manager service behavior

`app/services/run_manager.py` should provide a simple in-process manager.

Suggested responsibilities:

- Create job IDs.
- Store job objects in memory.
- Queue jobs.
- Start a worker task on FastAPI startup.
- Stop worker cleanly on FastAPI shutdown if possible.
- Execute one job at a time by default.
- Update job status and progress.
- Persist meaningful job result into project run history.
- Respect cancellation between workflow steps.
- Provide list/get/cancel/retry/clear helpers.

Suggested class:

```python
class LocalRunManager:
    def __init__(self):
        self.jobs: dict[str, RunJob] = {}
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.worker_task: asyncio.Task | None = None

    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def queue_node_run(...) -> RunJob: ...
    async def queue_workflow_run(...) -> RunJob: ...
    async def cancel_job(job_id: str) -> RunJob: ...
    async def retry_job(job_id: str) -> RunJob: ...
    async def get_job(job_id: str) -> RunJob: ...
    async def list_jobs(...) -> list[RunJob]: ...
```

If the current app already has a different app-state pattern, use that pattern.

---

## FastAPI lifecycle

Use FastAPI lifespan or startup/shutdown events.

Preferred:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_manager.start()
    yield
    await run_manager.stop()
```

Do not create multiple workers on reload accidentally.

If the current `app/main.py` already has a lifespan, integrate carefully.

---

## Handling blocking WaveSpeed calls

Inspect `node_runner.py` and `wavespeed_adapter.py`.

If execution is already async, keep it async.

If execution blocks the event loop, use the smallest safe change:

```python
await asyncio.to_thread(...)
```

or move only the blocking WaveSpeed call into a thread.

Do not rewrite the WaveSpeed adapter unnecessarily.

Do not call the WaveSpeed SDK outside `WaveSpeedAdapter`.

---

## Workflow execution inside jobs

For workflow jobs, reuse the existing resolver and node execution logic.

Rules:

1. Build plan before queueing.
2. Store plan snapshot on the job.
3. Set `progress_total` to number of runnable steps.
4. For each step:
   - Check `cancel_requested`.
   - Set `current_node_id`.
   - Update project node status to `queued` or `running`.
   - Resolve upstream input using existing resolver behavior.
   - Run node through existing runner.
   - Append output asset IDs and URLs to job.
   - Increment `progress_current`.
   - Persist project after each completed node if current architecture allows it.
5. If cancel requested between steps:
   - Mark remaining nodes as `skipped` or leave idle.
   - Mark job `cancelled`.
6. If any node fails:
   - Mark job `error`.
   - Preserve completed outputs.
   - Store error details.

Do not implement parallel execution in V7.

---

## Project run history integration

Current project already has a `runs` array.

V7 should make it cleaner and more useful.

For every queued job that reaches a terminal status, append or update a project run history item:

```json
{
  "id": "job_abc",
  "type": "workflow_whole_graph",
  "status": "success",
  "started_at": "...",
  "finished_at": "...",
  "node_ids": ["node_1", "node_2"],
  "asset_ids": ["asset_1"],
  "output_urls": ["https://..."],
  "warnings": [],
  "errors": [],
  "job_id": "job_abc"
}
```

If a run history format already exists, extend it without breaking old entries.

Avoid unlimited growth if easy:

```text
Keep latest 100 project runs by default.
```

Do not delete existing user history unexpectedly unless implementing a clear cap with docs.

---

## Frontend UX

Update:

```text
web/index.html
web/app.js
web/style.css
```

### Run Manager panel

Add a simple panel or drawer:

```text
Run Manager
- active jobs
- queued jobs
- completed recent jobs
```

Each job card should show:

```text
job id short
kind
project name/id
status
current node title
progress_current / progress_total
started_at
finished_at
error message if any
Cancel button when queued/running
Retry button when error/cancelled
Open project if job belongs to another loaded project, if simple
```

### Polling

Use polling, not WebSockets.

Suggested behavior:

```js
setInterval(refreshJobs, 1500) only while panel open or active jobs exist
```

Avoid excessive polling when there are no active jobs.

### Run buttons

Do not remove existing run buttons abruptly.

Recommended V7 behavior:

- Single node `Run` button queues a job by default.
- Workflow run buttons queue jobs by default.
- Keep direct synchronous endpoints available in backend for API compatibility.
- Show “Queued” immediately after job creation.
- Poll job until terminal status.
- Reload current project after terminal status.

If this is too large, add new buttons first:

```text
Queue Run
Queue Selected
Queue From Selected
Queue Whole Graph
```

Then Codex can switch existing buttons later.

### Node statuses

When a job is queued or running:

```text
node.status = queued/running
```

When it succeeds:

```text
node.status = success
```

When it fails:

```text
node.status = error
node.error_message = ...
```

When workflow cancellation skips a node:

```text
node.status = skipped
```

Only use `skipped` if the schema supports it.

### Job status badges

Add CSS classes:

```text
job-queued
job-running
job-success
job-error
job-cancelled
job-cancel-requested
```

### User messages

Use clear messages:

```text
Job queued.
Job running...
Cancel requested. The current WaveSpeed call may finish before the job stops.
Queued job cancelled.
Job failed. You can retry it.
Job completed.
```

Do not claim exact progress for active WaveSpeed model execution.

---

## Cost guard integration

V7 must not bypass V4 cost guard.

Before queueing any job:

- Estimate cost.
- Check local cost guard.
- If blocked, do not queue.
- If confirmation is required, frontend should ask before queueing.
- Store estimate and guard summary on the job if useful.

For workflow jobs:

- Use the workflow plan’s total estimated cost.
- Block if `max_workflow_run_usd` is exceeded.
- Preserve plan warnings on job.

---

## Duplicate active run protection

Add simple protection if feasible:

- Do not queue two active jobs for the same node if that node is already queued/running.
- Do not queue two active whole-graph jobs for the same project by accident.
- If blocked, show a clear message.

This can be a warning instead of a hard block if it complicates the code.

---

## Error handling

Return consistent FastAPI errors for:

- Missing project.
- Missing node.
- Unsupported job kind.
- Disabled model.
- Cost guard blocked.
- Workflow plan errors.
- Job not found.
- Cannot cancel terminal job.
- Cannot retry running job.
- WaveSpeed run failure.
- No output URL returned.

Frontend must show:

- Job-level error.
- Node-level error where applicable.
- Workflow-level error for plan/run issues.

---

## Tests

Add:

```text
tests/test_v7.py
```

Tests should not call live WaveSpeed.

Use mocks/fakes for node execution.

Suggested backend tests:

1. Queue node job creates `queued` job.
2. Job transitions to `running` then `success` with fake runner.
3. Queued job can be cancelled.
4. Running workflow job honors `cancel_requested` between steps.
5. Failed job can be retried and creates a new job ID.
6. Cost guard blocked node is not queued.
7. Workflow job stores `progress_total` from plan steps.
8. Job terminal status writes or updates project run history.
9. `GET /api/jobs` filters by project/status if implemented.
10. `DELETE /api/jobs/completed` clears only terminal in-memory jobs.
11. Existing V2/V3/V4/V5/V6 tests still pass.

Frontend validation:

```powershell
node --check web/app.js
```

Do not add a heavy JS testing framework unless the project already has one.

---

## Documentation updates

Update:

```text
PROJECT_SUMMARY.md
FINAL_PROJECT_CONTEXT.md
README.md
```

Docs should mention:

- V7 Local Run Manager implemented.
- Runs can be queued locally.
- Jobs can be listed and polled.
- Queued jobs can be cancelled.
- Active jobs support best-effort cancel only.
- Failed/cancelled jobs can be retried.
- Project run history is cleaner.
- Polling is used; no WebSockets/Redis/Celery/database.
- In-memory jobs are lost on server restart, while completed project run history remains if persisted.
- Live WaveSpeed generation requires a valid `WAVESPEED_API_KEY`.

Do not overclaim.

---

## Checkpoint build plan

Codex should implement V7 in checkpoints.

### Checkpoint 0 — Inspect and plan only

Do not edit files.

Inspect current code and report:

1. Whether V2/V3/V4/V5/V6 are implemented.
2. Current run endpoints.
3. Current workflow endpoints.
4. Current project `runs` shape.
5. Current node statuses.
6. Current frontend run buttons.
7. Whether `node_runner.py` is async or blocking.
8. Files that need to change for V7.
9. Risks.

Then propose a short implementation plan.

---

### Checkpoint 1 — Backend schemas and local manager skeleton

Goal: Add job models and a local manager without changing frontend behavior yet.

Tasks:

1. Add job schemas to `app/schemas.py` or a new schema section.
2. Create `app/services/run_manager.py`.
3. Add in-memory job storage.
4. Add queue/list/get/cancel/retry skeleton.
5. Add lifecycle start/stop in `app/main.py` if needed.
6. Do not wire live execution yet.

Validation:

```powershell
python -m compileall app
python -m unittest discover -s tests -v
```

---

### Checkpoint 2 — Job API endpoints

Goal: Expose job management endpoints.

Tasks:

1. Create `app/routers/jobs.py`.
2. Register it in `app/main.py`.
3. Add:
   - `GET /api/jobs`
   - `GET /api/jobs/{job_id}`
   - `POST /api/jobs/{job_id}/cancel`
   - `POST /api/jobs/{job_id}/retry`
   - `DELETE /api/jobs/completed`
4. Add tests for endpoint shape and error cases.
5. Do not queue WaveSpeed runs yet if execution is not ready.

Validation:

```powershell
python -m compileall app
python -m unittest discover -s tests -v
```

Manual smoke test:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000/docs
```

Confirm `/api/jobs` appears.

---

### Checkpoint 3 — Queue single-node runs

Goal: Queue and execute one node through existing node runner.

Tasks:

1. Add `POST /api/jobs/node`.
2. Run existing node cost preflight before queueing.
3. Queue job.
4. Worker executes existing node runner.
5. Update job status and project node status.
6. Persist output asset IDs/URLs through existing project save behavior.
7. Append/update project run history.
8. Add tests with fake runner.

Validation:

```powershell
python -m compileall app
python -m unittest discover -s tests -v
```

Manual test:

1. Start server.
2. Open app.
3. Add Text to Image node.
4. Queue node run.
5. Confirm job appears.
6. Confirm node changes queued/running/success.
7. Confirm output preview appears when finished.

---

### Checkpoint 4 — Queue workflow runs

Goal: Queue selected/from-node/whole-graph workflow runs.

Tasks:

1. Add:
   - `POST /api/jobs/workflow/selected`
   - `POST /api/jobs/workflow/from-node/{node_id}`
   - `POST /api/jobs/workflow/all`
2. Build plan before queueing.
3. Store plan snapshot on job.
4. Use `progress_total = len(plan.steps)`.
5. Execute steps sequentially through existing workflow/node runner logic.
6. Respect cancellation between steps.
7. Update project run history.
8. Add tests with fake multi-step workflow.

Validation:

```powershell
python -m compileall app
python -m unittest discover -s tests -v
```

Manual test:

1. Create connected graph.
2. Queue whole graph.
3. Confirm job progress increments per completed node.
4. Confirm outputs appear.
5. Confirm run history updates.

---

### Checkpoint 5 — Frontend Run Manager panel

Goal: Make queued jobs visible and usable in vanilla UI.

Tasks:

1. Add Run Manager panel in `web/index.html`.
2. Add CSS for job cards/status badges in `web/style.css`.
3. Add frontend state for jobs and polling in `web/app.js`.
4. Add `refreshJobs()`.
5. Add cancel/retry buttons.
6. Reload current project when a job reaches terminal status.
7. Avoid excessive polling when there are no active jobs.

Validation:

```powershell
node --check web/app.js
python -m uvicorn app.main:app --reload --port 8000
```

Manual test:

1. Open app.
2. Open Run Manager panel.
3. Queue a node run.
4. Confirm job appears.
5. Cancel queued job if possible.
6. Retry failed/cancelled job if possible.

---

### Checkpoint 6 — Switch run buttons to queued mode

Goal: Make the normal UI use the run manager.

Tasks:

1. Update node `Run` button to queue by default.
2. Update workflow buttons to queue by default.
3. Keep existing synchronous backend endpoints unchanged.
4. Keep existing cost confirmation behavior before queueing.
5. Show clear queued/running messages.
6. Ensure old manual test paths still work.

Validation:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
```

Manual test:

1. Run Text to Image from node button.
2. Confirm it queues instead of freezing UI.
3. Run whole graph.
4. Confirm job appears and status updates.
5. Confirm project outputs persist after job finishes.

---

### Checkpoint 7 — Cancellation and retry polish

Goal: Make cancellation and retry behavior reliable.

Tasks:

1. Cancel queued jobs immediately.
2. Mark running jobs as `cancel_requested`.
3. Stop workflow jobs between steps.
4. Show honest message for active WaveSpeed calls:
   ```text
   Cancel requested. The active WaveSpeed call may finish first.
   ```
5. Retry failed/cancelled jobs with a new job ID.
6. Prevent retry of running jobs.
7. Prevent duplicate active runs if feasible.
8. Add tests.

Validation:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
```

---

### Checkpoint 8 — Docs and final context

Goal: Update docs for V7.

Tasks:

1. Update `PROJECT_SUMMARY.md`.
2. Update `FINAL_PROJECT_CONTEXT.md`.
3. Update `README.md` only if useful.
4. Mention V7 status and limitations.
5. Add manual test path.
6. Do not include secrets or local `.env` values.

Validation:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
```

---

## Acceptance criteria

V7 is complete when:

1. `/api/jobs` endpoints exist and are visible in `/docs`.
2. Single-node runs can be queued.
3. Workflow runs can be queued.
4. UI shows active/queued/completed jobs.
5. Jobs show real step count progress, not fake model progress.
6. Queued jobs can be cancelled.
7. Running jobs can be marked `cancel_requested`.
8. Workflow jobs stop between steps after cancel request.
9. Failed/cancelled jobs can be retried with a new job ID.
10. Cost guard is checked before queueing.
11. Node statuses update during queued jobs.
12. Project outputs still persist correctly.
13. Project run history records terminal jobs.
14. Existing synchronous endpoints still work.
15. Existing V2/V3/V4/V5/V6 behavior still works.
16. Tests pass.
17. No React, React Flow, database, auth, billing, Redis, Celery, or new model category is added.

---

## Manual test path

Run:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8000
```

Then open:

```text
http://localhost:8000
```

Test path:

1. Create a new project.
2. Add a Text to Image node.
3. Enter a prompt.
4. Click Run.
5. Confirm a job appears in Run Manager.
6. Confirm status changes from `queued` to `running`.
7. Confirm output preview appears after success.
8. Add Image to Image node.
9. Connect Text to Image output to Image to Image image input.
10. Queue Run From Selected or Run Whole Graph.
11. Confirm progress shows step count.
12. Confirm outputs persist after completion.
13. Queue another run and cancel it while queued if possible.
14. Queue a workflow and cancel while running.
15. Confirm cancellation stops before the next step.
16. Force or simulate a failed job.
17. Retry failed job.
18. Save project.
19. Refresh page.
20. Reload project.
21. Confirm completed run history remains.
22. Restart server.
23. Confirm active in-memory jobs are gone, but persisted project run history remains.

Also test cost guard:

1. Set a very low `max_workflow_run_usd`.
2. Try to queue a workflow.
3. Confirm the job is blocked before entering the queue.

---

## Suggested Codex prompt

Use this prompt after placing `TASK_V7.md` in the repo root:

```text
Read TASK_V7.md and implement it.

Start with Checkpoint 0 only:
1. Inspect the repo.
2. Verify current V2, V3, V4, V5, and V6 status from code.
3. Inspect current run endpoints, workflow endpoints, node_runner, workflow_resolver, project runs shape, and frontend run buttons.
4. Propose a short implementation plan for V7.

Do not edit files until I approve the plan.
```

After Codex gives the plan:

```text
Proceed with Checkpoint 1 only.

Make the smallest compatible backend changes for job schemas and LocalRunManager skeleton.
Run the validation commands listed in TASK_V7.md.
Report changed files, test results, and risks.
```

Then continue checkpoint by checkpoint.

---

## What not to do yet

Do not use V7 to add:

- More WaveSpeed models.
- React Flow.
- Database.
- Auth.
- Billing.
- Redis/Celery/RQ.
- WebSockets/SSE unless polling is impossible.
- ZIP exports with binary assets.
- Collaboration.
- Production deployment hardening.
- Professional editing tools.

Recommended future task after V7:

```text
TASK_V8 — Asset Library and Cleanup:
asset search/filter, storage cleanup, stale local-file detection, and optional portable ZIP export planning
```

Only start V8 after queued run UX is stable.
