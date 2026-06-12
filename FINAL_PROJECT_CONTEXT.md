# Final Project Context

## One-Paragraph Summary

This project is a FastAPI plus vanilla HTML/CSS/JS MVP for an AI canvas workflow app inspired by Figma Weave, but intentionally without professional editing tools. Users can create/load local projects, add draggable catalog-driven node cards, manually wire nodes with visual handles, upload assets, queue supported WaveSpeed nodes and simple graph workflows through a local Run Manager, branch generated outputs, preview media, save node state and positions, configure project settings, use model overrides, estimate local node/workflow cost, export/import portable workflow JSON, duplicate projects, and reuse built-in or local workflow templates. The backend uses local JSON files, local upload/template folders, and an in-memory local job queue only; there is no database, auth, billing system, React, Next.js, Tailwind, Redis/Celery, or hardcoded secret.

## Product Goal

Build a simple AI canvas for composing generation workflows around WaveSpeed models. The MVP should make it easy to create a project, add media-generation nodes, wire compatible nodes, provide inputs through simple forms, upload or select source assets, run nodes, preview outputs, branch from outputs, save/reload state, and keep the model registry extensible for future WaveSpeed categories.

## Non-Goals

- No professional editing tools: no layers panel, masks, brushes, timeline editor, vector editor, crop studio, or Photoshop-style workspace.
- No React, Next.js, Tailwind, heavy canvas/flow library, or drag-and-drop dependency.
- No database, multi-user storage, auth, billing, external queues, production background workers, or production deployment setup.
- No hardcoded API keys or committed secrets.
- No invented execution parameters for unverified WaveSpeed model categories.

## Current Architecture

- Backend: Python FastAPI app in `app/`.
- Frontend: static vanilla app in `web/`, served at `/`.
- Static uploads: `data/uploads`, served at `/uploads`.
- Project storage: local JSON files under `data/projects`.
- Template storage: user templates under `data/templates`; built-in starter templates in `app/services/template_store.py`.
- Settings: `app/core/config.py`, loading `.env` and environment variables. The only WaveSpeed secret variable is `WAVESPEED_API_KEY`.
- WaveSpeed integration: `app/services/wavespeed_adapter.py` wraps the SDK for `run_model`, `upload_file`, and output URL extraction.
- Model capability source of truth: `app/services/model_catalog.py` plus registry conversion in `app/services/registry.py`.
- Workflow execution: graph planning/resolution in `app/services/workflow_resolver.py`, workflow endpoints in `app/routers/workflows.py`.
- Local run management: in-memory queue and single worker in `app/services/run_manager.py`, job endpoints in `app/routers/jobs.py`.

## Current Backend Files

- `app/main.py`: creates FastAPI app, starts/stops the local run manager through lifespan, registers routers, configures CORS, mounts `/uploads`, and serves the static frontend at `/`.
- `app/core/config.py`: runtime settings, env loading, runtime directory creation.
- `app/core/storage.py`: JSON read/write helpers.
- `app/schemas.py`: Pydantic models for projects, nodes, edges, assets, catalog, run estimates, run responses, and queued job requests/status.
- `app/routers/health.py`: health endpoint.
- `app/routers/models.py`: simple categories and models registry endpoints.
- `app/routers/model_catalog.py`: richer catalog and cheapest-model endpoints.
- `app/routers/projects.py`: local project CRUD and project settings get/update endpoints.
- `app/routers/templates.py`: built-in/user template endpoints.
- `app/routers/assets.py`: upload endpoint with size checking and optional WaveSpeed upload.
- `app/routers/runs.py`: node estimate and single-node execution endpoints.
- `app/routers/workflows.py`: workflow plan/run/history endpoints.
- `app/routers/jobs.py`: local job list/get/cancel/retry/clear and queue endpoints.
- `app/services/project_store.py`: validates project IDs and persists project JSON.
- `app/services/portable_project.py`: project export/import/duplicate helpers, sanitization, and ID remapping.
- `app/services/project_validation.py`: shared settings/model override and edge reference validation.
- `app/services/template_store.py`: built-in templates plus local user-template JSON persistence.
- `app/services/registry.py`: exposes registry models and resolves model precedence.
- `app/services/model_catalog.py`: catalog entries, costs, enabled flags, planned categories.
- `app/services/cost_estimator.py`: local cost estimate and guard logic.
- `app/services/node_runner.py`: prepares inputs, validates runnable models, runs WaveSpeed, stores node output metadata.
- `app/services/run_manager.py`: local in-process queue, job lifecycle, best-effort cancel, retry, progress counts, duplicate-run checks, and project run history integration.
- `app/services/wavespeed_adapter.py`: WaveSpeed SDK adapter.
- `app/services/workflow_resolver.py`: graph normalization, cycle checks, topological planning, input resolution.

## Current Frontend Files

- `web/index.html`: top bar, collapsible side menus, node library, canvas, inspector, workflow panels, Run Manager panel, log area.
- `web/app.js`: project loading/saving, model library rendering, node forms, node dragging, visual handle wiring, connection SVGs, edge selection/deletion, upload handling, queued run handling, job polling/cancel/retry, workflow actions, asset panel, previews, branching.
- `web/style.css`: dark three-column MVP layout, collapsible side-tab controls, node card styles, canvas grid, media previews, workflow/job panels, responsive fallback.

## Current API Endpoints

- `GET /api/health`
- `GET /api/categories`
- `GET /api/models`
- `GET /api/models?enabled_only=true`
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
- `GET /api/workflows/{project_id}/plan?mode=selected|from_node|whole_graph&node_id=...`
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
- `GET /docs`
- `GET /`

## Current Data Model

- `Project`: `id`, `name`, `description`, `nodes`, `edges`, `assets`, `runs`, `settings`, timestamps.
- `ProjectSettings`: `model_overrides` and `cost_guard`.
- `CostGuardSettings`: `enabled`, `warn_at_usd_per_run`, `block_at_usd_per_run`, `max_workflow_run_usd`, `block_on_unknown_cost`.
- `CanvasNode`: `id`, `type`, `title`, `model_id`, `estimated_base_cost_usd`, `x`, `y`, `inputs`, `output_asset_ids`, `output_urls`, `last_run`, `status`, `error_message`, timestamps.
- `CanvasEdge`: normalized aliases for `source_node_id`, `target_node_id`, `source_handle`, `target_handle`, `source_output`, `target_input`.
- `Asset`: `id`, `kind`, `filename`, `content_type`, `local_path`, `public_url`, `wavespeed_url`, `metadata`, `created_at`.
- `NodeStatus`: `idle`, `queued`, `running`, `success`, `error`, `skipped`.
- `RunJob`: in-memory local job model with `single_node`, `workflow_selected`, `workflow_from_node`, or `workflow_whole_graph` kind; `queued`, `running`, `success`, `error`, `cancel_requested`, or `cancelled` status; real step-count progress; node/asset/output URL lists; warnings/errors; timestamps.
- `AssetKind`: `image`, `video`, `audio`, `other`.

## Enabled WaveSpeed Models

- `text_to_image`: `wavespeed-ai/z-image/turbo`, image output, verified. Required `prompt`; optional `size`, `seed`, `output_format`.
- `image_to_image`: `wavespeed-ai/z-image-turbo/image-to-image`, image output, verified. Required `prompt` and `image`; optional `size`, `strength`, `seed`, `output_format`.
- `upscale_image`: `wavespeed-ai/image-upscaler`, image output, verified. Required `image`; optional `target_resolution`, `output_format`; runner adds sync/base64 flags.
- `remove_background`: `wavespeed-ai/image-background-remover`, image output, verified. Required `image`; runner adds sync/base64 flags.
- `image_to_video`: `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast`, video output, verified. Required `image` and `prompt`; optional `negative_prompt`, `duration`, `seed`, `last_image`.
- `text_to_speech`: `wavespeed-ai/qwen3-tts/text-to-speech`, audio output, verified. Required `text`; optional `language`, `voice`, `style_instruction`.

## Planned/Disabled Model Categories

- Image: `reference_to_image`, `remove_object`.
- Video: `start_end_to_video`, `text_to_video`, `reference_to_video`, `video_extend`, `video_effect`.
- Audio: `text_to_audio`, `speech_to_text`, `generate_voice`.
- Avatar: `talking_avatar`, `lip_sync`, `portrait_transfer`.
- 3D: `image_to_3d`, `text_to_3d`.
- System: `generic_wavespeed`.

These categories are visible in the catalog as candidate, needs-params, disabled, or experimental. They are not executable unless `enabled=true` in the catalog and supported in `node_runner.py`.

## TASK_V2 Summary

TASK_V2 is implemented in the current code. It added graph-aware workflow planning and execution, run history, node status changes, edge normalization, cycle detection, topological run order, upstream output resolution, selected-node runs, downstream runs, whole-graph runs, and frontend workflow panels/actions. Remaining V2 limitations are intentional MVP limits: no parallel execution, cancellation, background queue, or freehand connector UI.

## TASK_V3 Summary

TASK_V3 is implemented through the model catalog, schema expansion, catalog endpoints, project-level model overrides, local cost estimates, cost guard warnings/blocks, added execution support for verified safe models, media-aware frontend previews/forms, asset grid improvements, workflow branching to video, and tests in `tests/test_v3.py`. The code supports enabled execution only for verified implemented models and keeps unverified categories disabled.

## TASK_V4 Summary

TASK_V4 is implemented. It added project settings endpoints, backend validation for model overrides, expanded cost guard fields, workflow total cost aggregation, workflow preflight blocking, a vanilla Project Settings panel, frontend cost guard/model override controls, catalog-driven node library cleanup, effective model/cost/source display on node cards, workflow plan cost summaries, and tests in `tests/test_v4.py`. The frontend no longer depends on stale hardcoded runnable model definitions; disabled catalog entries remain visible but cannot be added or run.

## TASK_V5 Summary

TASK_V5 is implemented. It added Workflow Portability v1: portable JSON export/import, local project duplication, shared validation for imported settings and edges, built-in starter templates, user-saved local templates under `data/templates`, project creation from templates, frontend controls for export/import/duplicate/templates/save-as-template, and tests in `tests/test_v5.py`. Export strips local file paths and marks localhost-only asset URLs as non-portable. Import creates a new project, remaps node/edge/asset IDs, resets node runtime state, validates imported data, and never calls WaveSpeed.

Built-in templates:

- Basic Image Remix
- Product Cleanup
- Image to Short Video
- UGC Starter
- Voiceover Only

## TASK_V6 Summary

TASK_V6 is implemented. It added Visual Connector Editor v1 without React or a graph library. Node cards show output handles and media input handles. Users can drag from an output handle to a compatible input handle, see a ghost connector, create a validated edge immediately, save/reload the edge in project JSON, select an edge, delete the selected edge, and see connected-input badges with source-node hints. Frontend validation blocks self-loops, exact duplicates, obvious cycles, missing source/target/input, and known incompatible media connections. Branch shortcuts remain available and use the same edge helper. Tests in `tests/test_v6.py` cover backend edge compatibility, workflow planning behavior, and V5 portability/template preservation for V6 edge fields.

## TASK_V7 Summary

TASK_V7 is implemented. It added Local Run Manager v1 without Redis, Celery, a database, WebSockets, or SSE. `app/services/run_manager.py` keeps an in-memory job registry and one local worker queue, starts/stops through FastAPI lifespan, queues single-node and workflow jobs, checks V4 cost guard before queueing, prevents duplicate active node jobs and duplicate active whole-graph jobs, updates node statuses, records real step-count progress, writes terminal jobs into project `runs` history, caps history to the latest 100 entries, supports cancelling queued jobs immediately, marks running jobs as `cancel_requested`, stops workflow jobs between steps when cancellation is requested, and retries failed/cancelled jobs with new job IDs. `app/routers/jobs.py` exposes the `/api/jobs` endpoints. The vanilla frontend now has a Run Manager panel, polls jobs while active, queues normal node/workflow run buttons by default, and provides cancel/retry controls. Tests in `tests/test_v7.py` cover queued node execution, cancellation, retry, workflow cancellation between steps, cost guard blocking, progress totals, filters, clearing completed jobs, and endpoint shape.

## Current Frontend Behavior

- Opens at `http://localhost:8000`.
- Auto-loads the last project from local storage, falls back to first project, or creates one.
- Lets users create, load, edit, and save projects.
- Renders node library entries from `/api/models`.
- Shows disabled/planned nodes with reason text and disabled `Coming Soon` buttons.
- Opens a Project Settings panel for cost guard and model overrides.
- Exports/imports portable project JSON and duplicates projects from the top bar.
- Opens a Templates panel to create projects from built-in/user templates.
- Saves the current project as a reusable local user template.
- Lets users drag nodes with a move handle and saves `x`/`y` in project JSON after saving.
- Lets users manually drag from output handles to media input handles to create edges.
- Draws SVG connection lines from handle positions, with target-input labels and selected-edge styling.
- Lets users select and delete edges, including via the `Delete Selected Edge` button or Delete/Backspace key.
- Shows connected-input badges and disconnect actions on node input fields.
- Upload node stores local assets and can optionally upload to WaveSpeed.
- Node fields are generated from model field specs where available.
- Node cards show effective model, output kind, estimated cost, and model source.
- Run button estimates cost first, respects local cost guard, then queues `/api/jobs/node`.
- Output previews support images, videos, audio, copy/open/download actions.
- Generated image outputs can branch to remix nodes.
- Image outputs can branch to image-to-video when that model is enabled.
- Workflow panel can preview plan with total estimated cost, queue selected, queue from selected, queue whole graph, and refresh run history.
- Workflow run buttons preflight the plan and block/confirm before queueing jobs when cost guard requires it.
- Run Manager panel shows queued/running/completed jobs with status, current node, step-count progress, timestamps, cancel/retry actions, and open-project action when useful.
- Left and right side menus are collapsible through persistent side tabs so the canvas can use more horizontal space.

## Current Known Limitations

- Local JSON storage is not safe for concurrent multi-user production use.
- No authentication, authorization, user ownership, billing integration, rate limiting, or real cost accounting.
- Local Run Manager jobs are in-memory only and disappear on server restart; persisted project run history remains in project JSON.
- Active WaveSpeed SDK calls cannot be force-cancelled locally; running cancellation is best-effort, and workflow cancellation is honored between steps.
- No production queue, Redis/Celery/RQ, database-backed jobs, WebSockets, SSE, or exact model progress streaming.
- Cost estimates are local starting estimates, not exact billing or real usage metering.
- Only the first upstream output URL is used for workflow input mapping.
- Visual connector editing is intentionally simple: no zoom/pan, minimap, multi-select, or advanced edge routing.
- Local upload/project files can accumulate without cleanup tooling.
- JSON portability does not bundle binary asset files; remote URLs may still work, but local upload URLs are not portable across machines.
- Disabled model candidates may have model IDs but do not have verified request parameters or required UX.
- Live WaveSpeed execution depends on a valid `WAVESPEED_API_KEY`, installed SDK, network access, and WaveSpeed availability.

## Validation Commands

Run these from the project root:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8000
```

Then open:

- `http://localhost:8000`
- `http://localhost:8000/docs`
- `http://localhost:8000/api/models`
- `http://localhost:8000/api/model-catalog`
- `http://localhost:8000/api/templates`
- `http://localhost:8000/api/jobs`

## Manual Test Path

1. Set `WAVESPEED_API_KEY` in `.env` or the shell environment.
2. Start the server with `python -m uvicorn app.main:app --reload --port 8000`.
3. Open `http://localhost:8000`.
4. Create a project and save it.
5. Add a Text to Image node, enter a prompt, run it, confirm a Run Manager job appears, and confirm an image preview appears after success.
6. Click Branch from output to create an Image to Image remix node, edit the prompt, run it, and confirm output preview appears.
7. Upload an image asset, select it in a remix/upscale/remove-background/image-to-video node, run the node, and confirm output asset URLs/previews appear.
8. Drag nodes, save, refresh, reload the project, and confirm positions remain.
9. Use Preview Plan and Queue Selected/Queue From Selected/Queue Whole Graph on a small connected graph and confirm job progress uses step counts.
10. Open `/docs`, `/api/models`, and `/api/model-catalog` to verify API and registry visibility.
11. Click Export Project and confirm a JSON file downloads.
12. Click Import Project and select the exported JSON, then confirm a new project loads with the same workflow shape.
13. Click Duplicate Project and confirm a copied project loads.
14. Open Templates, create a project from Basic Image Remix, save a user template from the current project, and delete that user template.
15. Add Text to Image and Image to Image nodes, drag from the Text to Image output handle to the Image to Image `image` input handle, and confirm an edge label appears.
16. Save, refresh, reload, and confirm the manual edge remains.
17. Click the edge, delete it, reconnect it, and confirm Preview Plan uses the connection.
18. Queue a job and cancel it while queued if possible.
19. Queue a multi-step workflow, request cancel while running, and confirm it stops before the next step.
20. Simulate or force a failed job, retry it, and confirm the retry uses a new job ID.
21. Save, refresh, reload, and confirm terminal run history remains.
22. Restart the server and confirm active in-memory jobs are gone while persisted run history remains.

## Current Bugs/Risks

- Automated browser visual testing may be unavailable in some Codex sessions if the in-app browser backend reports `iab` unavailable. In that case, use HTTP smoke checks and manual browser validation.
- Live WaveSpeed runs require a valid `WAVESPEED_API_KEY` and were not exercised in automated tests.
- If a user selects a local `localhost` asset URL for WaveSpeed image input, the runner rejects it and asks for a WaveSpeed-uploaded asset or public URL, because WaveSpeed cannot fetch localhost.

## Recommended Next Major Task

Add asset cleanup/storage management. Database/auth/billing/React remain premature until the local single-user workflow is steadier.

## Compact Upload Context

This is a FastAPI + vanilla HTML/CSS/JS MVP AI canvas app for WaveSpeed workflows. Backend files live in `app/`; frontend files live in `web/`; local project JSON is stored under `data/projects`; uploads go to `data/uploads` and are served from `/uploads`; the frontend is served at `/`. Secrets must stay in environment variables only, especially `WAVESPEED_API_KEY`.

The app currently supports local projects, draggable catalog-driven node cards, node `x`/`y` persistence, visual handle-based edge wiring, edge labels/selection/deletion, connected-input badges, local asset upload with optional WaveSpeed upload, model registry/catalog endpoints, project settings, model overrides, local cost guard, queued node/workflow execution through the local Run Manager, job polling/cancel/retry, persistent terminal run history, output assets, media previews, branch creation from image outputs to remix or image-to-video nodes, portable project JSON export/import, local project duplication, and reusable workflow templates.

Core endpoints: `/api/health`, `/api/categories`, `/api/models`, `/api/model-catalog`, `/api/model-catalog/cheapest`, `/api/projects`, `/api/projects/{project_id}/settings`, `/api/projects/{project_id}/export`, `/api/projects/import`, `/api/projects/{project_id}/duplicate`, `/api/templates`, `/api/assets/upload`, `/api/runs/estimate`, `/api/runs/node`, `/api/workflows/{project_id}/plan`, `/api/workflows/{project_id}/run-selected`, `/api/workflows/{project_id}/run-from-node/{node_id}`, `/api/workflows/{project_id}/run-all`, `/api/workflows/{project_id}/runs`, `/api/jobs`, `/api/jobs/node`, `/api/jobs/workflow/selected`, `/api/jobs/workflow/from-node/{node_id}`, `/api/jobs/workflow/all`, `/docs`, and `/`.

Enabled runnable WaveSpeed models are `wavespeed-ai/z-image/turbo` for text-to-image, `wavespeed-ai/z-image-turbo/image-to-image` for remix, `wavespeed-ai/image-upscaler`, `wavespeed-ai/image-background-remover`, `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast` for image-to-video, and `wavespeed-ai/qwen3-tts/text-to-speech`. Disabled/planned categories remain visible but non-runnable: reference-to-image, remove-object, start/end video, text-to-video, reference-to-video, video extend/effect, text-to-audio, speech-to-text, generate voice, avatar/lip-sync/portrait transfer, image-to-3D, text-to-3D, and generic WaveSpeed.

TASK_V2 is implemented: workflow graph planning, selected/from-node/all runs, run history, edge normalization, cycle detection, topological order, and frontend workflow controls. TASK_V3 is implemented: richer model catalog, overrides/cost guard schemas, cost estimator, enabled verified safe models, frontend catalog UI, media previews, asset grid, branch-to-video, and tests. TASK_V4 is implemented: settings endpoints/UI, override validation, workflow cost totals, workflow cost blocking, catalog-driven node library cleanup, node effective-model display, and tests. TASK_V5 is implemented: export/import/duplicate/templates. TASK_V6 is implemented: visual connector editor. TASK_V7 is implemented: local in-memory Run Manager with queued single-node/workflow jobs, polling UI, best-effort cancel, retry, and project run history integration.

Validation commands: `python -m compileall app`, `node --check web/app.js`, `python -m unittest discover -s tests -v`, and `python -m uvicorn app.main:app --reload --port 8000`. Manual test: open `http://localhost:8000`, create project, add Text to Image and Image to Image, drag output to `image` input, save, refresh, reload, verify edge persistence, queue node and workflow jobs through the Run Manager, cancel/retry jobs, confirm step-count progress and terminal run history, branch to Remix, upload/select asset, run remix/upscale/remove-background/image-to-video, and verify positions/previews persist.
