# WaveSpeed Canvas MVP - Current Project Summary

## Purpose

This project is a FastAPI plus vanilla HTML/CSS/JavaScript MVP for a lightweight AI canvas workflow app. It lets users build simple WaveSpeed media workflows with projects, draggable node cards, uploaded assets, generated outputs, branches, workflow runs, run history, project settings, model overrides, and local cost guard controls.

The app is intentionally not a professional editor. It does not include layers, masks, brushes, vector tools, timelines, keyframes, React, React Flow, databases, auth, billing, or multi-user collaboration.

## Architecture

- Backend: Python FastAPI in `app/`.
- Frontend: static vanilla UI in `web/`, served from `/`.
- Project storage: local JSON under `data/projects`.
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
- `POST /api/assets/upload?upload_to_wavespeed=true|false`
- `POST /api/runs/estimate`
- `POST /api/runs/node`
- `GET /api/workflows/{project_id}/plan`
- `POST /api/workflows/{project_id}/run-selected`
- `POST /api/workflows/{project_id}/run-from-node/{node_id}`
- `POST /api/workflows/{project_id}/run-all`
- `GET /api/workflows/{project_id}/runs`

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
