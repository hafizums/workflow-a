# Codex Tasks — Build Order

## Phase 0 — Validate scaffold

1. Install dependencies from `requirements.txt`.
2. Start `python -m uvicorn app.main:app --reload --port 8000`.
3. Confirm `/api/health` works.
4. Confirm `/api/models` works.
5. Confirm static UI loads at `/`.

## Phase 1 — Clean backend foundation

1. Add unit tests for config, registry, project CRUD, asset upload, and WaveSpeedAdapter URL extraction.
2. Move project persistence logic from router into `services/project_store.py`.
3. Add structured logging.
4. Add consistent API error shape.
5. Add `.gitignore` for `.env`, `.venv`, `data/uploads`, and generated outputs.

## Phase 2 — Replace raw JSON node editing

1. Generate inspector forms from `ModelSpec.fields`.
2. Add validation before calling `/api/runs/node`.
3. Add field types: string, number, integer, boolean, select, asset_url.
4. Add quick preset prompts.

## Phase 3 — Real canvas

1. Convert frontend to React.
2. Add React Flow.
3. Support draggable nodes.
4. Support connecting node outputs to node inputs.
5. Persist node positions and edges.
6. Add context menu: duplicate, delete, branch from output.

## Phase 4 — Workflow execution

1. Add `workflow_resolver.py`.
2. Resolve connected output asset URL into target input field.
3. Add run-single-node.
4. Add run-from-selected-node.
5. Add run-whole-graph in topological order.
6. Add cancellation support where possible.

## Phase 5 — Asset previews

1. Add image previews in node cards.
2. Add video preview panel.
3. Add audio player.
4. Add copy URL button.
5. Add download button.
6. Add asset grid panel.

## Phase 6 — Add more WaveSpeed models

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

## Phase 7 — Database

1. Add SQLModel or SQLAlchemy.
2. Store projects, nodes, edges, assets, and runs.
3. Add migrations with Alembic.
4. Keep JSON export/import.

## Phase 8 — Production hardening

1. Add authentication.
2. Add per-user project permissions.
3. Add rate limits.
4. Add usage metering.
5. Add cost budget per user.
6. Add deployment config.
7. Add Dockerfile and compose file.
