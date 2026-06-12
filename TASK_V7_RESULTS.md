# TASK_V7 Results - Local Run Manager

## Status

TASK_V7 is implemented.

The app now has a local in-process Run Manager with an in-memory job registry, one local worker queue, queued single-node runs, queued workflow runs, job polling in the vanilla frontend, best-effort cancellation, retry for failed/cancelled jobs, and terminal job entries written into project run history.

## Files Changed

- `app/main.py`: starts and stops the local run manager with FastAPI lifespan and registers the jobs router.
- `app/schemas.py`: adds `RunJob`, job kind/status types, and queue request models.
- `app/routers/jobs.py`: adds job list/get/cancel/retry/clear endpoints plus queued node/workflow endpoints.
- `app/services/run_manager.py`: adds local job queue, worker execution, cost guard checks, cancellation/retry behavior, duplicate active-run protection, progress counts, and project run history integration.
- `web/index.html`: adds Run Manager UI and persistent collapsible side-menu tabs.
- `web/app.js`: queues node/workflow runs through `/api/jobs`, polls jobs, renders job cards, supports cancel/retry, reloads the current project after terminal jobs, and updates collapse button state.
- `web/style.css`: adds Run Manager styling, job status styling, compact topbar behavior, and collapsible side-menu tab styling.
- `tests/test_v7.py`: adds backend tests for queued node execution, cancellation, retry, workflow cancellation between steps, cost guard blocking, progress totals, job filtering/cleanup, and endpoint shape.
- `README.md`: documents the local Run Manager.
- `PROJECT_SUMMARY.md`: updates current state and limitations for V7.
- `FINAL_PROJECT_CONTEXT.md`: updates final handoff context for V7.

## Validation Commands

Run from the project root:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8000
```

Open:

- `http://localhost:8000`
- `http://localhost:8000/docs`
- `http://localhost:8000/api/jobs`

## Manual Test Path

1. Start the server with `python -m uvicorn app.main:app --reload --port 8000`.
2. Open `http://localhost:8000`.
3. Create or load a project.
4. Add a Text to Image node.
5. Enter a prompt.
6. Click `Run`.
7. Confirm a job appears in Run Manager.
8. Confirm the job shows queued/running/success or error.
9. Confirm output previews and project assets update after success.
10. Add an Image to Image node and connect the Text to Image output to its `image` input.
11. Use `Run From Selected` or `Run Whole Graph`.
12. Confirm workflow progress is shown as completed steps over total steps.
13. Queue another job and cancel it while queued if possible.
14. Request cancel while a workflow is running and confirm it stops before the next step when possible.
15. Force or simulate a failed job and retry it.
16. Save and refresh the project.
17. Confirm terminal run history remains.
18. Restart the server and confirm active in-memory jobs are gone while persisted run history remains.

## Notes And Limits

- Jobs are in-memory only and are lost on server restart.
- Terminal job history is persisted into project JSON and capped to the latest 100 entries.
- Running WaveSpeed SDK calls cannot be force-killed locally. Cancellation is best-effort and workflow jobs stop between steps.
- Existing synchronous endpoints remain available for API compatibility.
- No React, React Flow, database, auth, billing, Redis, Celery, WebSockets, SSE, or new model categories were added.
- Live WaveSpeed execution still requires `WAVESPEED_API_KEY` from the environment.
