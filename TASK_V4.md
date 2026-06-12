# TASK_V4.md — Project Control Center: Settings, Cost Guard UX, Model Override UX, and Catalog Cleanup

## Status

This task comes after `TASK_V2.md` and `TASK_V3.md`.

Assume the current project already has:

- FastAPI backend.
- Vanilla HTML/CSS/JS frontend.
- Local JSON project storage.
- Local upload storage.
- WaveSpeed node execution.
- Workflow planning/execution from `TASK_V2`.
- Cost-aware model catalog and first expanded media nodes from `TASK_V3`.

Before coding, Codex must verify this from the current repo. If any assumption is wrong, do not rewrite the app. Report the mismatch and make the smallest compatible change.

---

## High-level goal

Build **Project Control Center v1**.

The goal is to make the existing `TASK_V3` settings usable from the browser and clean up model/catalog duplication before adding more models, React, database storage, auth, or billing.

This task should expose and stabilize:

1. Project-level model overrides.
2. Project-level cost guard settings.
3. Workflow-level cost estimates.
4. Clear UI warnings/blocks before expensive runs.
5. A single catalog-driven source of truth for frontend node definitions.
6. Documentation and test coverage for the settings/cost behavior.

This task should **not** add more WaveSpeed model categories unless they are already implemented in the current codebase.

---

## Why this is TASK V4

`TASK_V3` added a cost-aware model catalog, cheapest/default model mapping, model override concepts, cost estimates, cost guard behavior, and a few verified runnable models.

The next useful product step is not another batch of models. The next useful step is making the project safer and easier to control:

- Users should see which model each node will use.
- Users should understand estimated cost before running a node or workflow.
- Users should be able to set project-level cost limits.
- Users should be able to override default models from a simple project settings panel.
- The frontend should stop relying on duplicated/old hardcoded node definitions when backend catalog data exists.

---

## Read these files first

Read these files before making a plan:

- `FINAL_PROJECT_CONTEXT.md`
- `PROJECT_SUMMARY.md`
- `TASK_V2.md`
- `TASK_V3.md`
- `README.md`
- `requirements.md`
- `CODEX_TASKS.md`
- `app/main.py`
- `app/schemas.py`
- `app/services/model_catalog.py`
- `app/services/registry.py`
- `app/services/cost_estimator.py`
- `app/services/project_store.py`
- `app/services/node_runner.py`
- `app/services/workflow_resolver.py`
- `app/routers/model_catalog.py`
- `app/routers/projects.py`
- `app/routers/runs.py`
- `app/routers/workflows.py`
- `web/index.html`
- `web/app.js`
- `web/style.css`
- existing files under `tests/`

Also inspect:

- current API routes registered in `app/main.py`
- current `ProjectSettings` / `CostGuard` schemas
- current frontend `NODE_DEFS` or any duplicated model definitions
- current run estimate behavior
- current workflow plan response shape

---

## Important constraints

Do not add:

- React.
- React Flow.
- Next.js.
- Tailwind.
- SQLite/Postgres.
- Auth.
- Billing integration.
- Multi-user accounts.
- Background workers.
- Job queues.
- More WaveSpeed models.
- Professional editing tools.
- Layers, masks, brush editor, vector editor, timeline, crop studio, keyframes, or Photoshop-like panels.

Do not:

- Hardcode secrets.
- Commit `.env` or `WAVESPEED_API_KEY`.
- Present estimates as exact billing.
- Enable disabled model categories without verifying official request parameters and adding runner support.
- Rewrite the whole frontend.
- Break existing project JSON files without migration/backward compatibility.

Keep:

- FastAPI backend.
- Vanilla frontend.
- Local JSON storage.
- Existing endpoints working.
- Existing runnable models working.
- WaveSpeed SDK usage only behind `WaveSpeedAdapter`.

---

## Target feature set

### 1. Project settings API

Add or improve backend support for project settings.

Preferred endpoints:

```text
GET  /api/projects/{project_id}/settings
PUT  /api/projects/{project_id}/settings
```

If the existing project update endpoint already handles settings cleanly, these endpoints can still be added as convenience wrappers. Do not remove existing project CRUD endpoints.

The settings response should include:

```json
{
  "model_overrides": {
    "text_to_image": "wavespeed-ai/z-image/turbo"
  },
  "cost_guard": {
    "enabled": true,
    "warn_above_usd": 0.05,
    "max_single_run_usd": 0.10,
    "max_workflow_run_usd": 0.25,
    "block_on_unknown_cost": true
  }
}
```

Use the existing schema names if they already exist. Add only minimal new Pydantic schemas if needed, for example:

- `ProjectSettingsUpdate`
- `CostGuardSettingsUpdate`
- `ModelOverrideUpdate`

Validation rules:

- `model_overrides` keys must be valid node types.
- Override model IDs must exist in the catalog/registry.
- Override model IDs must be compatible with the node type.
- Do not allow a disabled or unsupported model to become runnable through settings.
- Cost values must be numbers greater than or equal to zero.
- `warn_above_usd` should not exceed `max_single_run_usd` if both are set.
- `max_workflow_run_usd` should be allowed to be higher than `max_single_run_usd`.
- Unknown settings fields should be rejected or ignored consistently.

Backward compatibility:

- Projects without `settings` should load with defaults.
- Projects without `runs` should still load.
- Projects created before V4 should not crash.

---

### 2. Effective model resolution visibility

Make effective model resolution easy to understand.

For each node, the backend should be able to tell the frontend:

- node type
- node model ID if set
- project override model ID if set
- catalog default model ID
- effective model ID
- whether the effective model is enabled/runnable
- estimated base cost
- pricing note
- output kind

This can be implemented by extending existing catalog/model endpoints or by adding a small helper endpoint.

Suggested endpoint if useful:

```text
GET /api/projects/{project_id}/model-resolution
```

Alternative:

- Include effective model metadata in workflow plan responses.
- Include it in node run estimate responses.
- Let frontend calculate display from `/api/model-catalog` and project settings.

Choose the smallest clean design.

---

### 3. Workflow cost estimate aggregation

Improve workflow planning so users can see approximate total cost before running a workflow.

Update the workflow plan response to include:

```json
{
  "estimated_total_cost_usd": 0.06,
  "pricing_note": "Starting estimate only; final cost may depend on duration, resolution, character count, and model parameters.",
  "cost_guard": {
    "status": "ok|warning|blocked|unknown",
    "message": "...",
    "limit_usd": 0.25
  },
  "steps": [
    {
      "node_id": "node_1",
      "node_type": "text_to_image",
      "effective_model_id": "wavespeed-ai/z-image/turbo",
      "estimated_base_cost_usd": 0.005,
      "cost_guard": {
        "status": "ok|warning|blocked|unknown",
        "message": "..."
      }
    }
  ]
}
```

Rules:

- Use existing `cost_estimator.py` if present.
- Do not calculate exact billing.
- Unknown cost should be shown as unknown, not `$0`.
- Disabled/unrunnable nodes should not count as runnable cost.
- Workflow run endpoints should respect project cost guard settings.
- If blocked, return a clear API error and do not call WaveSpeed for blocked steps.

---

### 4. Project settings frontend panel

Add a simple project settings panel to the existing vanilla UI.

Possible UI placement:

- A `Project Settings` button in the top bar.
- A modal/panel.
- Or a right-side tab near the inspector.

The settings panel should include:

#### Cost guard section

Fields:

- Enable/disable cost guard.
- Warn above USD.
- Max single run USD.
- Max workflow run USD.
- Block unknown-cost models.

Text to show:

```text
Cost estimates are starting estimates only. Final WaveSpeed cost can vary by model settings.
```

#### Model overrides section

For each enabled runnable node type, show:

- Node type display name.
- Current default model.
- Current project override if any.
- Select dropdown of compatible enabled models.
- Reset to default button.

At minimum, support overrides for currently runnable node types:

- `text_to_image`
- `image_to_image`
- `upscale_image`
- `remove_background`
- `image_to_video`
- `text_to_speech`

Do not show disabled models as selectable overrides unless they are clearly disabled and cannot be saved as active overrides.

---

### 5. Node card cost/model display

Improve each node card so the user can see:

- Effective model ID.
- Output kind.
- Estimated base cost.
- Whether project override is active.
- Whether the model is disabled or unsupported.

Example display:

```text
Model: wavespeed-ai/z-image/turbo
Cost: starts at $0.005/run
Source: project default
```

If node model differs from project default, show:

```text
Source: node override
```

If project override applies, show:

```text
Source: project override
```

---

### 6. Run and workflow confirmation behavior

Before running a node:

1. Call the existing run estimate endpoint or equivalent logic.
2. Show a warning if the estimate crosses warning threshold.
3. Block if the estimate crosses max single run threshold.
4. Block if cost is unknown and `block_on_unknown_cost=true`.
5. Only call the run endpoint after the estimate passes.

Before running a workflow:

1. Call the workflow plan endpoint.
2. Show estimated total cost.
3. Show per-step costs.
4. Block if total crosses max workflow threshold.
5. Block if any step is blocked.
6. Do not call WaveSpeed for blocked workflows.

For warnings, a simple browser `confirm()` is acceptable for V4.

---

### 7. Frontend catalog cleanup

Clean up duplicate model/node definitions.

Goals:

- Use backend catalog/registry as source of truth for node library.
- Avoid stale `NODE_DEFS` entries with old placeholder IDs.
- Keep only small frontend fallback definitions if absolutely necessary.
- Make disabled/planned nodes visibly disabled with reason text from backend.
- Make field rendering use backend field specs where available.

Also fix known minor frontend issues:

- Remove any text encoding artifact around the cost separator.
- Make missing catalog data fail gracefully.
- Make asset/video/audio previews resilient to missing URLs.
- Make disabled node buttons impossible to run.

---

### 8. Tests

Add tests for V4 behavior.

Suggested file:

```text
tests/test_v4.py
```

Test at least:

1. Default project settings are created for old projects.
2. Settings endpoint returns defaults.
3. Settings endpoint persists updates.
4. Invalid node type override is rejected.
5. Disabled/unsupported model override is rejected.
6. Valid model override is accepted.
7. Cost guard blocks a single run estimate above max.
8. Cost guard allows a cheap run below max.
9. Workflow plan includes estimated total cost.
10. Workflow plan returns blocked status when total exceeds max workflow cost.
11. Existing V2/V3 tests still pass.

Do not require a real WaveSpeed API key for unit tests.

Use mocks/stubs for WaveSpeed calls if needed.

---

### 9. Documentation

Update or create these docs:

- `FINAL_PROJECT_CONTEXT.md`
- `PROJECT_SUMMARY.md`
- optionally `TASK_V4_RESULTS.md`

Document:

- New settings endpoints.
- How model overrides work.
- How cost guard works.
- What is still only an estimate.
- Manual test path.
- Remaining non-goals.

If `AGENTS.md` does not exist, create a short repo-level `AGENTS.md` with:

- run commands
- validation commands
- no-secret rules
- no React/database/auth/billing yet
- WaveSpeed SDK usage must stay behind `WaveSpeedAdapter`
- model execution must stay in `node_runner.py`
- project storage must stay backward compatible

Keep `AGENTS.md` practical and short.

---

## Implementation checkpoints

### Checkpoint 0 — Inspect and plan only

Codex must first inspect the repo and report:

1. Whether V2 appears implemented.
2. Whether V3 appears implemented.
3. Current settings schema shape.
4. Current cost estimator behavior.
5. Current frontend catalog duplication locations.
6. Proposed files to change.

Do not edit files during Checkpoint 0.

---

### Checkpoint 1 — Backend settings API

Implement project settings get/update support.

Expected files may include:

- `app/schemas.py`
- `app/routers/projects.py`
- `app/services/project_store.py`
- `app/services/registry.py`
- `app/services/model_catalog.py`
- tests

Validation:

```bat
python -m compileall app
python -m unittest discover -s tests -v
```

---

### Checkpoint 2 — Cost aggregation and guard behavior

Implement workflow plan cost aggregation and blocking behavior.

Expected files may include:

- `app/services/cost_estimator.py`
- `app/services/workflow_resolver.py`
- `app/routers/runs.py`
- `app/routers/workflows.py`
- tests

Validation:

```bat
python -m compileall app
python -m unittest discover -s tests -v
```

---

### Checkpoint 3 — Frontend project settings panel

Add project settings UI.

Expected files may include:

- `web/index.html`
- `web/app.js`
- `web/style.css`

Validation:

```bat
node --check web/app.js
python -m uvicorn app.main:app --reload --port 8000
```

Manual browser validation:

- Open `http://localhost:8000`.
- Create/load project.
- Open Project Settings.
- Change cost guard values.
- Save settings.
- Refresh page.
- Confirm settings persist.

---

### Checkpoint 4 — Catalog cleanup and node display

Make node library and node cards catalog-driven.

Expected files may include:

- `web/app.js`
- `web/style.css`
- maybe `app/routers/models.py` or `app/routers/model_catalog.py`

Validation:

```bat
node --check web/app.js
python -m compileall app
```

Manual browser validation:

- Node library renders enabled and disabled models correctly.
- Disabled models cannot run.
- Node cards show effective model and estimated cost.
- No stale placeholder IDs appear as runnable models.

---

### Checkpoint 5 — Docs and final validation

Update docs and run all validations.

Validation commands:

```bat
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8000
```

Manual test path:

1. Set `WAVESPEED_API_KEY` in `.env` or shell environment.
2. Start server:

```bat
python -m uvicorn app.main:app --reload --port 8000
```

3. Open:

```text
http://localhost:8000
```

4. Create or load a project.
5. Open Project Settings.
6. Set `warn_above_usd` to a low value, for example `0.004`.
7. Save settings.
8. Add a `text_to_image` node.
9. Run estimate/run and confirm warning appears because text-to-image starts above `0.004`.
10. Set `max_single_run_usd` to a value lower than `image_to_video`, for example `0.01`.
11. Try running `image_to_video` and confirm it blocks before calling WaveSpeed.
12. Set `max_workflow_run_usd` low enough to block a multi-node workflow.
13. Preview workflow plan and confirm total estimated cost appears.
14. Try `Run Whole Graph` and confirm blocked workflows do not call WaveSpeed.
15. Set a valid project model override and confirm node cards show project override.
16. Try to save a disabled model override and confirm the backend rejects it.
17. Save project, refresh, reload, and confirm settings persist.
18. Confirm existing text-to-image, remix, upscale, remove-background, image-to-video, and text-to-speech nodes still behave as before when cost guard allows them.
19. Open:

```text
http://localhost:8000/docs
http://localhost:8000/api/model-catalog
```

20. Confirm API docs and catalog still work.

---

## Definition of done

TASK V4 is done when:

- Existing V2 workflow behavior still works.
- Existing V3 catalog and runnable models still work.
- Project settings can be viewed and updated from API.
- Project settings can be viewed and updated from browser UI.
- Cost guard settings persist in project JSON.
- Node cards show effective model and estimated cost.
- Workflow plan shows total estimated cost.
- Single-node runs respect cost guard.
- Workflow runs respect cost guard.
- Disabled/unverified models cannot be activated through overrides.
- Frontend no longer depends on stale duplicated model definitions for runnable nodes.
- Tests cover settings and cost guard behavior.
- Validation commands pass.
- Documentation is updated.
- No secrets are committed.

---

## Suggested Codex prompt

Use this prompt after placing `TASK_V4.md` in the repo root:

```text
Read TASK_V4.md and implement it.

Start with Checkpoint 0 only:
1. Inspect the repo.
2. Verify current V2 and V3 status from code.
3. Identify current settings/cost/catalog implementation.
4. Identify frontend catalog duplication.
5. Propose a short implementation plan.

Do not edit files until I approve the plan.
```

After approving the plan, continue with:

```text
Proceed with Checkpoint 1 only.
Make the smallest compatible backend changes for project settings API and tests.
Run the validation commands listed in TASK_V4.md.
Report changed files, test results, and any risk.
```

Then continue checkpoint by checkpoint.

---

## Notes for future tasks

After TASK V4 is stable, the next reasonable task could be one of these:

1. `TASK_V5 — Workflow Templates and Project Import/Export`
2. `TASK_V5 — Visual Connector Editor Without React`
3. `TASK_V5 — Start-End Video Node After Official Parameter Verification`
4. `TASK_V5 — Local Job Queue and Run Progress`

Do not jump to database/auth/billing/React until the local single-user product is stable and pleasant to use.
