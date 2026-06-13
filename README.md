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
  frontend/                  React + React Flow source app
  web/
  index.html                 Built static frontend served by FastAPI
  assets/                    Built frontend CSS/JS assets
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

Run local tests:

```bat
python -m pytest
```

Run frontend browser smoke tests:

```bat
npm run test:e2e --prefix frontend
```

Rebuild the React frontend served by FastAPI:

```bat
cd frontend
npm install
npm run build
cd ..
```

During frontend development, run FastAPI on port `8000` and Vite on port `5173`:

```bat
python -m uvicorn app.main:app --reload --port 8000
cd frontend
npm run dev
```

Regenerate the V11 WaveSpeed catalog:

```bat
python scripts\import_wavespeed_catalog.py docs\reference\wavespeed_model_catalog_drilldown.xlsx
```

Catalog endpoints:

```text
GET /api/model-catalog/summary
GET /api/model-catalog/models/wavespeed-ai/z-image/turbo
GET /api/model-catalog/models/alibaba/happyhorse-1.0/text-to-video
GET /api/models?enabled_only=true
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

V8 was a UI organization pass. The current frontend has since moved to a React + React Flow source app in `frontend/`, built as static assets served by FastAPI from `web/`. It keeps the same local FastAPI/static deployment shape while providing a studio layout with grouped command bars, searchable node library, dynamic category filters, canvas stats, a selection strip, tabbed inspector, toast feedback, and safer keyboard shortcuts. Existing project, template, asset, workflow, and run-manager APIs remain unchanged.

## V9 model enablement

V9 focuses on model enablement and media workflow functionality. The runner now uses node-type preparers from the registry instead of a tiny hardcoded model allowlist, and project assets can be image, audio, video, or other files.

The upload node still uses the backward-compatible `upload_image` node type, but it now behaves as **Upload Asset** and accepts image, audio, video, 3D/archive, and text-like files. Localhost URLs are blocked for remote WaveSpeed inputs; upload local media to WaveSpeed first or use a public HTTPS URL.

Mask-based models require a supplied mask image in V9. There is no brush, layer, or mask drawing editor.

V11 expands the model menu beyond the small V9 curated batch. Normal add-node menus load enabled models from `/api/models?enabled_only=true`; catalog rows excluded from runtime are not shown as runnable cards and remain inspectable through `/api/model-catalog/excluded` or `/api/model-catalog?include_excluded=true`.

## Important implementation notes

Localhost file URLs are usually not reachable by remote AI APIs. For image, audio, or video nodes, use the upload endpoint with `upload_to_wavespeed=true`, then copy the returned `wavespeed_url` into the node input field or select the uploaded asset in the node card.

Cost estimates are local starting estimates, not exact billing. The canvas displays model and workflow estimates in Malaysian Ringgit using the UI-only conversion `USD 1 = RM4.06`; backend API fields, stored project settings, and cost guard thresholds remain USD (`*_usd`).

Curated enabled model IDs include:

```text
wavespeed-ai/z-image/turbo
wavespeed-ai/z-image-turbo/image-to-image
wavespeed-ai/image-upscaler
wavespeed-ai/image-background-remover
wavespeed-ai/wan-2.2/i2v-480p-ultra-fast
wavespeed-ai/wan-2.2/t2v-480p-ultra-fast
wavespeed-ai/openai-whisper
wavespeed-ai/qwen3-tts/text-to-speech
wavespeed-ai/qwen3-tts/voice-design
wavespeed-ai/latentsync
wavespeed-ai/infinitetalk
wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid
wavespeed-ai/z-image/turbo-inpaint
```

Curated enabled node types include text-to-image, image-to-image/remix, reference-to-image, upscale image, remove background, remove object/inpaint, image-to-video, start-end video, text-to-video, text-to-speech, speech-to-text, generate voice, lip sync, talking avatar, and text-to-3D.

The full catalog adds hundreds of additional enabled `generic_wavespeed` entries. Use `/api/model-catalog/summary` and `/api/models?enabled_only=true` for the current count.

See `docs/V9_MODEL_ENABLEMENT.md` for curl examples for the new runnable models.
Live dry-runs can be repeated with `python scripts/live_wavespeed_v9_smoke.py --confirm-spend-credits` after setting any required media URL environment variables documented there.

## V10 Weave-style workflow layer

V10 adds artifact lineage, utility nodes, variant batches, model comparison, winner promotion, branch-from-any-artifact, production recipes, export packages, and run snapshots. AI execution remains WaveSpeed-only; local utility nodes only orchestrate prompts, assets, selection, comparison, and export metadata.

Prompt-like inputs on saved project model nodes are graph-sourced. Write prompt text in a Prompt Card, LLM text/vision node, or transcript node, then connect that output to model prompt/text inputs. The model cards show those prompt fields as connected inputs so prompts stay reusable and branchable instead of being hidden inside one model node.

Current UI reachability: recipes, basic branching, utility nodes, uploads, run history, previews, and workflow runs are available in the React canvas. Variant batches, model comparison sets, artifact winner promotion, export packages, and run snapshot clone/rerun are backend/API-first for now; use the endpoints below when testing those workflows.

Current utility nodes:

| Node | Purpose | Runnable |
| --- | --- | --- |
| Prompt Card | Reusable prompt and negative prompt text. | No |
| Style Card | Reusable visual style and quality notes. | No |
| Character / Reference Card | Reusable character, product, voice, or reference description. | No |
| Upload Asset / Asset Input | Select or upload a project asset as graph input. | No |
| Asset Selector | Select one artifact from upstream outputs or project assets. | No |
| Compare Board | Collect outputs for review. | No |
| Variant Batch | Describe local variant fan-out metadata. | No |
| Reroute | Organize graph connections. | No |
| Note | Canvas note. | No |
| Group Frame | Canvas grouping metadata. | No |
| Export Package | Collect deliverables into export metadata. | No |
| Video Last Frame | Extract a video's final frame into an image asset. | Yes, local |
| Stitch Videos | Stitch multiple video assets into one local MP4. | Yes, local |

Useful V10 endpoints:

```bat
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/nodes/NODE_ID/variants ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":\"PROJECT_ID\",\"node_id\":\"NODE_ID\",\"variant_count\":4,\"parameters\":[{\"field\":\"seed\",\"strategy\":\"seed\",\"values\":[]}],\"save_to_project\":true}"
```

```bat
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/nodes/NODE_ID/compare-models ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":\"PROJECT_ID\",\"source_node_id\":\"NODE_ID\",\"model_ids\":[],\"save_to_project\":true}"
```

```bat
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/artifacts/ASSET_ID/branch ^
  -H "Content-Type: application/json" ^
  -d "{\"target_node_type\":\"image_to_video\",\"target_input_name\":\"image\",\"title\":\"Animate winner\"}"
```

```bat
curl -X POST http://localhost:8000/api/projects/PROJECT_ID/export-package ^
  -H "Content-Type: application/json" ^
  -d "{\"asset_ids\":[]}"
```

Recipes are available at `/api/recipes`, and the V10 parity/guardrail map is documented in `docs/V10_WEAVE_PARITY_MAP.md`.

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

Node cards show a primary output handle and media input handles such as `image`, `last_image`, `video`, and `audio`. Drag from an output handle to an input handle, or click an output handle and then click a compatible input handle, to create an edge. The app blocks self-loops, exact duplicate edges, obvious cycles, and known incompatible media kinds. Click an edge or label to select it, then use `Delete Selected Edge` or the Delete/Backspace key to remove it.

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
2. Improve React canvas ergonomics around handles, edge labels, and selection.
3. Add more WaveSpeed categories only after request parameters are verified.
4. Delay database/auth/billing until the local single-user workflow is stable.

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
