# WaveSpeed Canvas MVP - Current Project Summary

## Purpose

This project is a FastAPI plus vanilla HTML/CSS/JavaScript MVP for a lightweight AI canvas workflow app. It lets users build simple WaveSpeed media workflows with projects, draggable node cards, manual visual connections, uploaded assets, generated outputs, branches, queued local runs, run history, project settings, model overrides, local cost guard controls, portable project JSON exports/imports, local project duplication, and reusable workflow templates.

The app is intentionally not a professional editor. It does not include layers, masks, brushes, vector tools, timelines, keyframes, React, React Flow, databases, auth, billing, or multi-user collaboration.

## Architecture

- Backend: Python FastAPI in `app/`.
- Frontend: static vanilla UI in `web/`, served from `/`.
- Project storage: local JSON under `data/projects`.
- Template storage: local JSON under `data/templates`, plus built-in templates in code.
- Upload storage: local files under `data/uploads`, served from `/uploads`.
- WaveSpeed SDK access: only through `app/services/wavespeed_adapter.py`.
- Model execution: `app/services/node_runner.py`.
- Model catalog/registry: `app/services/model_catalog.py` and `app/services/registry.py`.
- Workflow planning/execution: `app/services/workflow_resolver.py` and `app/routers/workflows.py`.
- Local run management: in-memory queue in `app/services/run_manager.py`, exposed by `app/routers/jobs.py`.

## Main Backend Endpoints

- `GET /api/health`
- `GET /api/categories`
- `GET /api/models`
- `GET /api/model-catalog`
- `GET /api/model-catalog/cheapest`
- `GET /api/model-catalog/{node_type}`
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `PUT /api/projects/{project_id}`
- `DELETE /api/projects/{project_id}`
- `GET /api/projects/{project_id}/settings`
- `PUT /api/projects/{project_id}/settings`
- `GET /api/projects/{project_id}/export`
- `POST /api/projects/import`
- `POST /api/projects/{project_id}/duplicate`
- `POST /api/assets/upload?upload_to_wavespeed=true|false`
- `POST /api/runs/estimate`
- `POST /api/runs/node`
- `GET /api/workflows/{project_id}/plan`
- `POST /api/workflows/{project_id}/run-selected`
- `POST /api/workflows/{project_id}/run-from-node/{node_id}`
- `POST /api/workflows/{project_id}/run-all`
- `GET /api/workflows/{project_id}/runs`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/cancel`
- `POST /api/jobs/{job_id}/retry`
- `DELETE /api/jobs/completed`
- `POST /api/jobs/node`
- `POST /api/jobs/workflow/selected`
- `POST /api/jobs/workflow/from-node/{node_id}`
- `POST /api/jobs/workflow/all`
- `GET /api/templates`
- `POST /api/templates`
- `GET /api/templates/{template_id}`
- `PUT /api/templates/{template_id}`
- `DELETE /api/templates/{template_id}`
- `POST /api/templates/from-project/{project_id}`
- `POST /api/templates/{template_id}/create-project`

## Enabled WaveSpeed Models

- `text_to_image`: `wavespeed-ai/z-image/turbo`
- `image_to_image`: `wavespeed-ai/z-image-turbo/image-to-image`
- `upscale_image`: `wavespeed-ai/image-upscaler`
- `remove_background`: `wavespeed-ai/image-background-remover`
- `image_to_video`: `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast`
- `text_to_speech`: `wavespeed-ai/qwen3-tts/text-to-speech`

Disabled/planned catalog entries remain visible but non-runnable until their request parameters and product UX are verified.

## Project Settings

Projects include `settings.model_overrides` and `settings.cost_guard`.

Model override rules:

- Node-level `model_id` wins over project override.
- Project override wins over catalog default.
- Overrides must use enabled compatible models.
- Disabled or incompatible models are rejected by the backend.

Cost guard fields:

- `enabled`
- `warn_at_usd_per_run`
- `block_at_usd_per_run`
- `max_workflow_run_usd`
- `block_on_unknown_cost`

Cost values are local starting estimates only, not exact billing.

## Frontend Behavior

- Create/load/save projects.
- Add catalog-driven nodes from `/api/models`.
- Disabled planned nodes show as coming soon and cannot be added.
- Upload image assets locally and optionally upload to WaveSpeed.
- Drag node cards and save positions.
- Drag from output handles to media input handles to create manual workflow edges.
- See ghost connector lines while wiring nodes.
- Select SVG edges, see target-input labels, and delete selected edges.
- See connected-input badges on node fields and disconnect individual inputs.
- Edit node inputs through simple card forms.
- Run single nodes with cost preflight.
- Queue single-node runs through the Run Manager.
- Preview generated image/video/audio assets.
- Branch image outputs into remix or image-to-video nodes.
- Preview workflow plans with total estimated cost.
- Queue selected-node, downstream, or whole-graph workflow runs.
- Poll queued/running jobs, cancel queued jobs, request best-effort cancellation for running jobs, and retry failed/cancelled jobs.
- Open Project Settings to edit cost guard and model overrides.
- Node cards show effective model, output kind, estimated cost, and source.
- Export portable JSON project files.
- Import portable JSON project files as new local projects.
- Duplicate the current project locally.
- Open a Templates panel, create projects from built-in or user templates, save the current project as a local template, and delete user templates.

## Visual Connector Editor

V6 implements manual wiring without React or a graph library. Node cards expose one primary output handle and media input handles such as `image`, `last_image`, `video`, and `audio`. The frontend blocks self-loops, exact duplicate edges, obvious cycles, missing node references, and known incompatible media connections. New edges are saved in project JSON and are preserved by export/import, duplication, and templates.

Branch buttons remain available as shortcuts and now use the same edge creation helper as manual wiring.

## Local Run Manager

V7 implements a local in-process Run Manager without Redis, Celery, a database, WebSockets, or SSE. The app stores active jobs in memory, runs one job at a time by default, and exposes job list/get/cancel/retry/clear endpoints under `/api/jobs`.

Single-node and workflow run buttons now queue jobs. The frontend shows a Run Manager panel with job id, kind, project, status, current node, real step-count progress, timestamps, and error/warning messages. It polls only while jobs are active or after refresh. Queued jobs cancel immediately. Running jobs can be marked `cancel_requested`; active WaveSpeed SDK calls are best-effort only and may finish before the job stops. Workflow jobs stop between steps after cancellation is requested.

Terminal jobs are written into project `runs` history with `job_id`, status, node ids, asset ids, output URLs, warnings, errors, and progress counts. Project run history is capped to the latest 100 entries. In-memory jobs are lost on server restart, while persisted project run history remains in project JSON.

## Workflow Portability

V5 project exports use schema `wavespeed_canvas_project_export` version `1`. Export strips local filesystem paths and marks localhost-only asset URLs as non-portable. Import accepts either a full export envelope or raw project-shaped JSON, creates a new project ID, remaps node/edge/asset IDs, validates node types/settings/edge references, resets runtime status to `idle`, and never calls WaveSpeed.

Built-in templates:

- Basic Image Remix
- Product Cleanup
- Image to Short Video
- UGC Starter
- Voiceover Only

## Validation Commands

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8000
```

Open:

- `http://localhost:8000`
- `http://localhost:8000/docs`
- `http://localhost:8000/api/models`
- `http://localhost:8000/api/model-catalog`

## Known Limitations

- Local JSON storage only; not safe for production multi-user concurrency.
- No auth, billing, rate limits, or usage metering.
- Local run jobs are in-memory only and disappear on server restart; persisted project run history remains.
- Active WaveSpeed SDK calls cannot be force-killed by the local cancel button; running cancellation is best-effort and checked between workflow steps.
- No production queue, database-backed jobs, WebSockets, SSE, Redis, Celery, or real progress streaming.
- Cost guard is local estimate-based protection, not exact billing control.
- Only the first upstream output URL is used for workflow input mapping.
- Visual connector editing is intentionally simple: no zoom/pan, minimap, multi-select, or advanced edge routing.
- Live WaveSpeed runs require `WAVESPEED_API_KEY`, network access, and WaveSpeed availability.
- V5 JSON portability does not bundle binary asset files; remote `wavespeed_url` values can remain useful, but local upload URLs may not travel across machines.
