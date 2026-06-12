# WaveSpeed Canvas MVP - Current Project Summary

## Purpose

This project is a FastAPI plus vanilla HTML/CSS/JavaScript MVP for a lightweight AI canvas workflow app. It lets users build simple WaveSpeed media workflows with projects, draggable node cards, uploaded assets, generated outputs, branches, workflow runs, run history, project settings, model overrides, local cost guard controls, portable project JSON exports/imports, local project duplication, and reusable workflow templates.

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
- Edit node inputs through simple card forms.
- Run single nodes with cost preflight.
- Preview generated image/video/audio assets.
- Branch image outputs into remix or image-to-video nodes.
- Preview workflow plans with total estimated cost.
- Run selected node, downstream graph, or whole graph.
- Open Project Settings to edit cost guard and model overrides.
- Node cards show effective model, output kind, estimated cost, and source.
- Export portable JSON project files.
- Import portable JSON project files as new local projects.
- Duplicate the current project locally.
- Open a Templates panel, create projects from built-in or user templates, save the current project as a local template, and delete user templates.

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
- No background jobs, cancellation, retries, or progress streaming.
- Cost guard is local estimate-based protection, not exact billing control.
- Only first upstream output URL is used for workflow mapping.
- Connector creation is branch-button based, not a full visual connector editor.
- Live WaveSpeed runs require `WAVESPEED_API_KEY`, network access, and WaveSpeed availability.
- V5 JSON portability does not bundle binary asset files; remote `wavespeed_url` values can remain useful, but local upload URLs may not travel across machines.
