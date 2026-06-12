# TASK V4 Results

## Summary

TASK V4 implemented Project Control Center v1 for the FastAPI + vanilla frontend WaveSpeed Canvas MVP.

The task focused on making TASK V3 settings usable from the browser and stabilizing cost/catalog behavior before adding more model categories, a database, auth, billing, React, or professional editing tools.

## Backend Changes

- Added project settings endpoints:
  - `GET /api/projects/{project_id}/settings`
  - `PUT /api/projects/{project_id}/settings`
- Expanded `CostGuardSettings` with:
  - `max_workflow_run_usd`
  - `block_on_unknown_cost`
- Kept backward-compatible fields:
  - `warn_at_usd_per_run`
  - `block_at_usd_per_run`
- Accepted input aliases:
  - `warn_above_usd`
  - `max_single_run_usd`
- Added model override validation:
  - valid node type required
  - compatible model required
  - enabled model required
  - disabled or unsupported models rejected
- Added workflow plan cost aggregation:
  - `estimated_total_cost_usd`
  - `estimated_known_cost_usd`
  - workflow-level `cost_guard`
  - per-step `cost_guard`
- Workflow run endpoints now preflight plans and block before WaveSpeed calls when cost guard blocks the run.

## Frontend Changes

- Added a Project Settings button and panel.
- Added cost guard controls:
  - enable cost guard
  - warn above USD
  - max single run USD
  - max workflow run USD
  - block unknown-cost models
- Added model override dropdowns for enabled compatible runnable node types.
- Cleaned frontend catalog duplication:
  - removed stale hardcoded runnable `NODE_DEFS`
  - removed old `TODO_ADD_*` placeholders
  - node library now uses `/api/models`
  - disabled planned models show as `Coming Soon`
- Node cards now show:
  - effective model ID
  - estimated cost
  - output kind
  - model source: catalog default, project override, or node override
- Workflow plan panel now shows total estimated cost and cost guard status.
- Workflow run buttons preflight cost before calling run endpoints.

## Tests

Added `tests/test_v4.py` covering:

- old project settings defaults
- settings endpoint defaults
- settings persistence
- invalid override rejection
- disabled override rejection
- incompatible override rejection
- invalid cost threshold rejection
- full project update validation
- single-run cost guard allow/block
- workflow total cost aggregation
- workflow cost blocking before execution

Existing V3 tests still pass.

## Validation

Checkpoint validation commands:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8000
```

Final automated validation passed for compile, frontend syntax, and tests.

HTTP smoke checks confirmed:

- `/`
- `/api/health`
- `/api/models`
- `/api/model-catalog`

## Manual Test Path

1. Set `WAVESPEED_API_KEY` in `.env` or shell environment.
2. Start the app with `python -m uvicorn app.main:app --reload --port 8000`.
3. Open `http://localhost:8000`.
4. Create or load a project.
5. Open Project Settings.
6. Set low cost guard values and save.
7. Add nodes from the catalog-driven node library.
8. Confirm disabled nodes show as coming soon.
9. Confirm node cards show model/cost/source details.
10. Preview workflow plan and confirm total estimated cost appears.
11. Try blocked node/workflow runs and confirm they stop before execution.
12. Save, refresh, reload, and confirm settings persist.

## Known Limitations

- Cost estimates are starting estimates only, not exact billing.
- No live WaveSpeed generation was performed during V4 validation.
- Browser visual automation was not available in this environment.
- Workflow execution still runs synchronously in request/response.
- Local JSON storage remains single-user/dev-oriented.
