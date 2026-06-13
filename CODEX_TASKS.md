# Codex Tasks - Build Order

This file is historical build order, not the current implementation contract. The current frontend is React + React Flow in `frontend/`, built to static assets in `web/`; see `AGENTS.md`, `README.md`, and `FINAL_PROJECT_CONTEXT.md` for current architecture and validation commands.

## Phase 0 - Validate Scaffold

1. Install dependencies from `requirements.txt`.
2. Start `python -m uvicorn app.main:app --reload --port 8000`.
3. Confirm `/api/health` works.
4. Confirm `/api/models` works.
5. Confirm static UI loads at `/`.

## Phase 1 - Clean Backend Foundation

1. Add unit tests for config, registry, project CRUD, asset upload, and WaveSpeedAdapter URL extraction.
2. Move project persistence logic from router into `services/project_store.py`.
3. Add structured logging.
4. Add consistent API error shape.
5. Add `.gitignore` for `.env`, `.venv`, `data/uploads`, and generated outputs.

## Phase 2 - Replace Raw JSON Node Editing

1. Generate inspector forms from `ModelSpec.fields`.
2. Add validation before calling `/api/runs/node`.
3. Add field types: string, number, integer, boolean, select, asset_url.
4. Add quick preset prompts.

## Phase 3 - Real Canvas

1. Historical note: this phase originally kept a vanilla canvas. The current implementation uses React + React Flow.
2. Support draggable nodes.
3. Support connecting node outputs to node inputs.
4. Persist node positions and edges.
5. Add context actions: duplicate, delete, branch from output.

## Phase 4 - Workflow Execution

1. Add `workflow_resolver.py`.
2. Resolve connected output asset URL into target input field.
3. Add run-single-node.
4. Add run-from-selected-node.
5. Add run-whole-graph in topological order.
6. Add cancellation support where possible.

## Phase 5 - Asset Previews

1. Add image previews in node cards.
2. Add video preview panel.
3. Add audio player.
4. Add copy URL button.
5. Add download button.
6. Add asset grid panel.

## Phase 6 - Add More WaveSpeed Models

Only add a model after checking its model page and request parameters.

Suggested next categories:

1. Image to Video.
2. Start-End Video.
3. Remove Background.
4. Upscale Image.
5. Text to Speech.
6. Lip Sync / Avatar.

For each model, update:

1. `app/services/registry.py`.
2. Frontend field rendering.
3. Example payload in docs.
4. Tests.

## Phase 7 - Database

1. Add SQLModel or SQLAlchemy.
2. Store projects, nodes, edges, assets, and runs.
3. Add migrations with Alembic.
4. Keep JSON export/import.

## Phase 8 - UI Upgrade

## Phase 11 - WaveSpeed Catalog Scale-Out

1. Store the WaveSpeed workbook at `docs/reference/wavespeed_model_catalog_drilldown.xlsx`.
2. Regenerate `app/data/wavespeed_catalog.normalized.json` with `scripts/import_wavespeed_catalog.py`.
3. Use curated node types for friendly V9/V10 nodes.
4. Use `generic_wavespeed` plus exact `model_id` for catalog-scale models.
5. Keep all executable AI calls on WaveSpeed.
6. Use `/api/model-catalog/*` for catalog search, schema, capability, and exclusion lookup.
7. Use mocked tests for catalog runtime paths unless deliberately doing a live smoke test with a real key.

1. Rework static frontend into WaveSpeed Studio v8 layout.
2. Add searchable node library and category filters.
3. Add canvas stats and selection bar.
4. Add tabbed inspector.
5. Add toast feedback and keyboard shortcuts.
6. Preserve existing FastAPI routes and local JSON storage.

## Phase 9 - Production Hardening

1. Add authentication.
2. Add per-user project permissions.
3. Add rate limits.
4. Add usage metering.
5. Add cost budget per user.
6. Add deployment config.
7. Add Dockerfile and compose file.
