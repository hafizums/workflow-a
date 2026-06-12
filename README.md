# WaveSpeed Canvas MVP — FastAPI Codex Build Pack

This is a local MVP app, not a finished production app.

Goal: build a lightweight node-canvas creative workflow app using Python FastAPI and WaveSpeed. It should feel like a simple "Weave-lite" workflow builder: generate, branch, remix, animate, and export AI media without professional editing tools.

## What is included

```text
app/
  main.py                    FastAPI app entrypoint
  schemas.py                 Pydantic API/data models
  core/config.py             .env settings
  core/storage.py            JSON file persistence helpers
  routers/health.py          Health endpoint
  routers/models.py          Node category + model registry endpoints
  routers/projects.py        Project CRUD using local JSON files
  routers/templates.py       Workflow template API
  routers/jobs.py            Local in-memory run manager API
  routers/assets.py          Local upload + optional WaveSpeed upload
  routers/runs.py            Generic WaveSpeed node runner
  services/registry.py       Node categories and starter model specs
  services/run_manager.py    Local queue, retry, cancel, and run history bridge
  services/portable_project.py
  services/template_store.py
  services/wavespeed_adapter.py
  web/
  index.html                 Vanilla canvas UI
  style.css                  Basic layout styling
  app.js                     Vanilla front-end logic and connector editor
requirements.txt             Python dependencies
requirements.md              Product + technical requirements for Codex
CODEX_TASKS.md               Step-by-step implementation tasks
.env.example                 Environment template
```

## Windows CMD setup

Open **Command Prompt** in the project folder.

```bat
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

Set your key in `.env`:

```env
WAVESPEED_API_KEY=your_real_wavespeed_key_here
```

Run the app:

```bat
python -m uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

## Fast test commands

Health check:

```bat
curl http://localhost:8000/api/health
```

List model registry:

```bat
curl http://localhost:8000/api/models
```

List workflow templates:

```bat
curl http://localhost:8000/api/templates
```

List local run-manager jobs:

```bat
curl http://localhost:8000/api/jobs
```

Run text-to-image from CMD:

```bat
curl -X POST http://localhost:8000/api/runs/node ^
  -H "Content-Type: application/json" ^
  -d "{\"model_id\":\"wavespeed-ai/z-image/turbo\",\"node_type\":\"text_to_image\",\"inputs\":{\"prompt\":\"A clean futuristic product poster, studio lighting\",\"size\":\"1024*1024\",\"seed\":-1,\"output_format\":\"jpeg\"},\"save_to_project\":false}"
```

## Current MVP behavior

The MVP supports:

1. Creating local projects.
2. Adding draggable model nodes to a simple canvas.
3. Editing node inputs with simple card controls.
4. Running enabled WaveSpeed model nodes.
5. Uploading files locally.
6. Optionally uploading local files to WaveSpeed so image/video models can consume them.
7. Saving project JSON under `data/projects`.
8. Running selected/downstream/whole-graph workflows.
9. Using project settings, model overrides, and local cost guard controls.
10. Exporting/importing portable project JSON.
11. Duplicating projects locally.
12. Creating projects from built-in or user-saved workflow templates.
13. Manually wiring node outputs to media inputs with visual handles.
14. Selecting and deleting workflow edges.
15. Queueing single-node and workflow runs through the local Run Manager.
16. Cancelling queued jobs, requesting best-effort cancellation for running jobs, and retrying failed/cancelled jobs.

## V8 UI upgrade

V8 keeps the vanilla FastAPI/static frontend but reorganizes the interface into **WaveSpeed Studio v8**: a studio layout with grouped command bars, searchable node library, dynamic category filters, canvas stats, a selection strip, tabbed inspector, toast feedback, and safer keyboard shortcuts. Existing project, template, asset, workflow, and run-manager APIs remain unchanged.

## Important implementation notes

Localhost file URLs are usually not reachable by remote AI APIs. For image-to-image or image-to-video nodes, use the upload endpoint with `upload_to_wavespeed=true`, then copy the returned `wavespeed_url` into the node input field.

Enabled model IDs include:

```text
wavespeed-ai/z-image/turbo
wavespeed-ai/z-image-turbo/image-to-image
wavespeed-ai/image-upscaler
wavespeed-ai/image-background-remover
wavespeed-ai/wan-2.2/i2v-480p-ultra-fast
wavespeed-ai/qwen3-tts/text-to-speech
```

Other categories are represented as disabled or planned catalog entries until their request parameters and UX are verified.

## Portability

Project export:

```bat
curl http://localhost:8000/api/projects/PROJECT_ID/export
```

Project import:

```bat
curl -X POST http://localhost:8000/api/projects/import ^
  -F "file=@workflow.json"
```

Project duplication:

```bat
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/duplicate ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Copy of workflow\",\"include_outputs\":true,\"include_run_history\":false}"
```

Exported JSON uses schema `wavespeed_canvas_project_export` version `1`. Exports strip local filesystem paths and mark localhost-only asset URLs as non-portable. Import creates a new project, remaps node/edge/asset IDs, resets runtime status, validates settings and edge references, and does not call WaveSpeed.

## Visual connections

Node cards show a primary output handle and media input handles such as `image`, `last_image`, `video`, and `audio`. Drag from an output handle to an input handle to create an edge. The app blocks self-loops, exact duplicate edges, obvious cycles, and known incompatible media kinds. Click an edge or label to select it, then use `Delete Selected Edge` or the Delete/Backspace key to remove it.

Connected inputs show a badge with the upstream source node. Branch buttons remain available as shortcuts and create the same edge shape as manual wiring.

## Local Run Manager

V7 adds a local in-process Run Manager. The normal node `Run` button and workflow run buttons queue jobs instead of blocking on the request. Jobs are kept in memory and exposed through:

```text
GET    /api/jobs
GET    /api/jobs/{job_id}
POST   /api/jobs/{job_id}/cancel
POST   /api/jobs/{job_id}/retry
DELETE /api/jobs/completed
POST   /api/jobs/node
POST   /api/jobs/workflow/selected
POST   /api/jobs/workflow/from-node/{node_id}
POST   /api/jobs/workflow/all
```

The frontend polls `/api/jobs` while work is active and shows queued/running/success/error/cancelled jobs in the Run Manager panel. Progress is real step count progress, not model-progress percentages. Queued jobs cancel immediately. Running jobs can be marked `cancel_requested`; an active WaveSpeed SDK call may still finish before the job stops. Workflow jobs check for cancellation between steps.

Completed terminal jobs are written into the project `runs` history and capped to the latest 100 entries. In-memory jobs disappear when the server restarts, but persisted completed run history remains in the project JSON.

## What Codex should build next

Use `requirements.md` as the product/technical spec and `CODEX_TASKS.md` as the implementation sequence.

Good next local-product steps:

1. Add asset cleanup/storage management.
2. Improve connector ergonomics with zoom/pan only if the vanilla canvas starts to feel cramped.
3. Add more WaveSpeed categories only after request parameters are verified.
4. Delay database/auth/billing/React until the local single-user workflow is stable.

## Out of scope for MVP

Do not build professional edit tools yet:

- No Photoshop-style layer system.
- No vector editor.
- No timeline editor.
- No brush masking UI.
- No advanced inpainting canvas.
- No keyframe editor.
- No multi-user real-time collaboration.

Build the AI workflow first.
