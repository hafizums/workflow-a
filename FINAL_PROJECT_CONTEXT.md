# Final Project Context

## One-Paragraph Summary

This project is a FastAPI plus vanilla HTML/CSS/JS MVP for an AI canvas workflow app inspired by Figma Weave, but intentionally without professional editing tools. Users can create/load local projects, add draggable node cards, upload assets, run supported WaveSpeed nodes, branch generated outputs, preview media, save node state and positions, estimate local per-run cost, and run either one node or simple graph workflows. The backend uses local JSON files and local upload folders only; there is no database, auth, billing system, React, Next.js, Tailwind, or hardcoded secret.

## Product Goal

Build a simple AI canvas for composing generation workflows around WaveSpeed models. The MVP should make it easy to create a project, add media-generation nodes, provide inputs through simple forms, upload or select source assets, run nodes, preview outputs, branch from outputs, save/reload state, and keep the model registry extensible for future WaveSpeed categories.

## Non-Goals

- No professional editing tools: no layers panel, masks, brushes, timeline editor, vector editor, crop studio, or Photoshop-style workspace.
- No React, Next.js, Tailwind, heavy canvas/flow library, or drag-and-drop dependency.
- No database, multi-user storage, auth, billing, queues, background workers, or production deployment setup.
- No hardcoded API keys or committed secrets.
- No invented execution parameters for unverified WaveSpeed model categories.

## Current Architecture

- Backend: Python FastAPI app in `app/`.
- Frontend: static vanilla app in `web/`, served at `/`.
- Static uploads: `data/uploads`, served at `/uploads`.
- Project storage: local JSON files under `data/projects`.
- Settings: `app/core/config.py`, loading `.env` and environment variables. The only WaveSpeed secret variable is `WAVESPEED_API_KEY`.
- WaveSpeed integration: `app/services/wavespeed_adapter.py` wraps the SDK for `run_model`, `upload_file`, and output URL extraction.
- Model capability source of truth: `app/services/model_catalog.py` plus registry conversion in `app/services/registry.py`.
- Workflow execution: graph planning/resolution in `app/services/workflow_resolver.py`, workflow endpoints in `app/routers/workflows.py`.

## Current Backend Files

- `app/main.py`: creates FastAPI app, CORS, router registration, `/uploads` mount, and `/` static frontend mount.
- `app/core/config.py`: runtime settings, env loading, runtime directory creation.
- `app/core/storage.py`: JSON read/write helpers.
- `app/schemas.py`: Pydantic models for projects, nodes, edges, assets, catalog, run estimates, and run responses.
- `app/routers/health.py`: health endpoint.
- `app/routers/models.py`: simple categories and models registry endpoints.
- `app/routers/model_catalog.py`: richer catalog and cheapest-model endpoints.
- `app/routers/projects.py`: local project CRUD.
- `app/routers/assets.py`: upload endpoint with size checking and optional WaveSpeed upload.
- `app/routers/runs.py`: node estimate and single-node execution endpoints.
- `app/routers/workflows.py`: workflow plan/run/history endpoints.
- `app/services/project_store.py`: validates project IDs and persists project JSON.
- `app/services/registry.py`: exposes registry models and resolves model precedence.
- `app/services/model_catalog.py`: catalog entries, costs, enabled flags, planned categories.
- `app/services/cost_estimator.py`: local cost estimate and guard logic.
- `app/services/node_runner.py`: prepares inputs, validates runnable models, runs WaveSpeed, stores node output metadata.
- `app/services/wavespeed_adapter.py`: WaveSpeed SDK adapter.
- `app/services/workflow_resolver.py`: graph normalization, cycle checks, topological planning, input resolution.

## Current Frontend Files

- `web/index.html`: top bar, node library, canvas, inspector, workflow panels, log area.
- `web/app.js`: project loading/saving, model library rendering, node forms, node dragging, connection SVGs, upload handling, run handling, workflow actions, asset panel, previews, branching.
- `web/style.css`: dark three-column MVP layout, node card styles, canvas grid, media previews, workflow panels, responsive fallback.

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
- `POST /api/assets/upload?upload_to_wavespeed=true|false`
- `POST /api/runs/estimate`
- `POST /api/runs/node`
- `GET /api/workflows/{project_id}/plan?mode=selected|from_node|whole_graph&node_id=...`
- `POST /api/workflows/{project_id}/run-selected`
- `POST /api/workflows/{project_id}/run-from-node/{node_id}`
- `POST /api/workflows/{project_id}/run-all`
- `GET /api/workflows/{project_id}/runs`
- `GET /docs`
- `GET /`

## Current Data Model

- `Project`: `id`, `name`, `description`, `nodes`, `edges`, `assets`, `runs`, `settings`, timestamps.
- `ProjectSettings`: `model_overrides` and `cost_guard`.
- `CanvasNode`: `id`, `type`, `title`, `model_id`, `estimated_base_cost_usd`, `x`, `y`, `inputs`, `output_asset_ids`, `output_urls`, `last_run`, `status`, `error_message`, timestamps.
- `CanvasEdge`: normalized aliases for `source_node_id`, `target_node_id`, `source_handle`, `target_handle`, `source_output`, `target_input`.
- `Asset`: `id`, `kind`, `filename`, `content_type`, `local_path`, `public_url`, `wavespeed_url`, `metadata`, `created_at`.
- `NodeStatus`: `idle`, `queued`, `running`, `success`, `error`, `skipped`.
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

## Current Frontend Behavior

- Opens at `http://localhost:8000`.
- Auto-loads the last project from local storage, falls back to first project, or creates one.
- Lets users create, load, edit, and save projects.
- Renders model registry entries as addable node cards.
- Shows disabled/planned nodes with reason text.
- Lets users drag nodes with a move handle and saves `x`/`y` in project JSON after saving.
- Draws SVG connection lines for project edges.
- Upload node stores local assets and can optionally upload to WaveSpeed.
- Node fields are generated from model field specs where available.
- Run button estimates cost first, respects local cost guard, then calls `/api/runs/node`.
- Output previews support images, videos, audio, copy/open/download actions.
- Generated image outputs can branch to remix nodes.
- Image outputs can branch to image-to-video when that model is enabled.
- Workflow panel can preview plan, run selected, run from selected, run whole graph, and refresh run history.

## Current Known Limitations

- Local JSON storage is not safe for concurrent multi-user production use.
- No authentication, authorization, user ownership, billing integration, rate limiting, or real cost accounting.
- WaveSpeed calls are synchronous request/response polling through the SDK; no job queue, retries, cancellation, or progress streaming.
- Cost estimates are local starting estimates, not exact billing.
- Only the first upstream output URL is used for workflow input mapping.
- Frontend connector creation is branch-button based, not a full visual connector editor.
- Local upload/project files can accumulate without cleanup tooling.
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

## Manual Test Path

1. Set `WAVESPEED_API_KEY` in `.env` or the shell environment.
2. Start the server with `python -m uvicorn app.main:app --reload --port 8000`.
3. Open `http://localhost:8000`.
4. Create a project and save it.
5. Add a Text to Image node, enter a prompt, run it, and confirm an image preview appears.
6. Click Branch from output to create an Image to Image remix node, edit the prompt, run it, and confirm output preview appears.
7. Upload an image asset, select it in a remix/upscale/remove-background/image-to-video node, run the node, and confirm output asset URLs/previews appear.
8. Drag nodes, save, refresh, reload the project, and confirm positions remain.
9. Use Preview Plan and Run Selected/Run From Selected/Run Whole Graph on a small connected graph.
10. Open `/docs`, `/api/models`, and `/api/model-catalog` to verify API and registry visibility.

## Current Bugs/Risks

- The folder is not currently a Git repository, so tracked/untracked file status cannot be checked with `git status`.
- Some frontend static definitions in `NODE_DEFS` still include older placeholder IDs, but model catalog entries are rendered from `/api/models` and should be the primary UI source.
- There is a minor text encoding artifact in `web/app.js` display text around the cost separator.
- Automated browser visual testing was not verified in this context.
- Live WaveSpeed runs were not re-tested while creating this context file.
- If a user selects a local `localhost` asset URL for WaveSpeed image input, the runner rejects it and asks for a WaveSpeed-uploaded asset or public URL, because WaveSpeed cannot fetch localhost.

## Recommended Next Major Task

Add a small project settings panel for `model_overrides` and `cost_guard`, plus a focused cleanup pass on frontend catalog/node definition duplication. This would make TASK_V3 features visible and easier to manage without adding a database or framework.

## Compact Upload Context

This is a FastAPI + vanilla HTML/CSS/JS MVP AI canvas app for WaveSpeed workflows. Backend files live in `app/`; frontend files live in `web/`; local project JSON is stored under `data/projects`; uploads go to `data/uploads` and are served from `/uploads`; the frontend is served at `/`. Secrets must stay in environment variables only, especially `WAVESPEED_API_KEY`.

The app currently supports local projects, draggable node cards, node `x`/`y` persistence, local asset upload with optional WaveSpeed upload, model registry/catalog endpoints, node execution, workflow planning/execution, run history, output assets, media previews, and branch creation from image outputs to remix or image-to-video nodes.

Core endpoints: `/api/health`, `/api/categories`, `/api/models`, `/api/model-catalog`, `/api/model-catalog/cheapest`, `/api/projects`, `/api/assets/upload`, `/api/runs/estimate`, `/api/runs/node`, `/api/workflows/{project_id}/plan`, `/api/workflows/{project_id}/run-selected`, `/api/workflows/{project_id}/run-from-node/{node_id}`, `/api/workflows/{project_id}/run-all`, `/api/workflows/{project_id}/runs`, `/docs`, and `/`.

Enabled runnable WaveSpeed models are `wavespeed-ai/z-image/turbo` for text-to-image, `wavespeed-ai/z-image-turbo/image-to-image` for remix, `wavespeed-ai/image-upscaler`, `wavespeed-ai/image-background-remover`, `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast` for image-to-video, and `wavespeed-ai/qwen3-tts/text-to-speech`. Disabled/planned categories remain visible but non-runnable: reference-to-image, remove-object, start/end video, text-to-video, reference-to-video, video extend/effect, text-to-audio, speech-to-text, generate voice, avatar/lip-sync/portrait transfer, image-to-3D, text-to-3D, and generic WaveSpeed.

TASK_V2 is implemented: workflow graph planning, selected/from-node/all runs, run history, edge normalization, cycle detection, topological order, and frontend workflow controls. TASK_V3 is implemented: richer model catalog, overrides/cost guard schemas, cost estimator, enabled verified safe models, frontend catalog UI, media previews, asset grid, branch-to-video, and tests.

Validation commands: `python -m compileall app`, `node --check web/app.js`, `python -m unittest discover -s tests -v`, and `python -m uvicorn app.main:app --reload --port 8000`. Manual test: open `http://localhost:8000`, create project, add/run Text to Image, branch to Remix, upload/select asset, run remix/upscale/remove-background/image-to-video, save, refresh, reload, and verify positions/previews persist.
