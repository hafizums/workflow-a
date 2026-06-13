# Functional Requirement Gap Audit

Audit date: 2026-06-13

Scope: source documents `requirements.md`, `FINAL_PROJECT_CONTEXT.md`, `PROJECT_SUMMARY.md`, `CODEX_TASKS.md`, `AGENTS.md`, and `README.md` compared against `app/`, `frontend/`, `web/`, `tests/`, and existing docs/task-result files.

This is a functional audit only. It does not include production-hardening backlog such as auth, billing, database persistence, rate limiting, deployment, multi-user concurrency, or professional editing tools unless a source document already presents the behavior as current MVP functionality.

## 1. Executive Summary

Total current gaps found: **0**

Priority counts:

- **P0:** 0
- **P1:** 0
- **P2:** 0
- **P3:** 0

The project docs and implementation are now mostly aligned. The current source of truth is a FastAPI backend plus React/React Flow frontend in `frontend/`, built to static assets under `web/`. The registry is catalog-scale: normal add-node menus use enabled curated/catalog models from `/api/models?enabled_only=true`, and runtime-excluded catalog rows are inspectable through `/api/model-catalog/excluded` rather than shown as disabled runnable cards.

Documentation contradictions found in the earlier audit have been resolved in the source docs: disabled-placeholder wording was replaced with the enabled/excluded catalog policy, the V10 advanced workflows are documented as API-first where the UI does not expose full panels yet, utility nodes are documented, and historical vanilla-canvas task notes are marked as historical.

The previous functional test-depth gap has been closed for the documented MVP paths: the Playwright smoke suite now covers core React UI reachability, manual handle-based edge creation, saved edge payloads, reload persistence, node dragging, local asset upload, project delete reachability, workflow queue entry, previews, raw responses, and MYR run-cost labels.

## 2. Source-of-Truth Map

### requirements.md

Claims the product is a simple AI canvas workflow builder for local projects, nodes, edges, assets, WaveSpeed runs, output previews, branching, and saved workflows. It now documents the current React/React Flow source layout in `frontend/` and static build output in `web/`, while preserving the old `web/app.js` scaffold as historical. It describes curated friendly nodes, catalog-scale `generic_wavespeed` nodes, enabled add-node menus, excluded catalog inspection endpoints, prompt-source rules, and a local utility-node table.

### FINAL_PROJECT_CONTEXT.md

Claims the current app is a FastAPI + React/React Flow MVP with local JSON projects, upload/template folders, in-memory local jobs, project settings, model overrides, cost guard, export/import/duplicate/templates, visual connector editing, Run Manager, catalog-scale models, output previews, and local utility nodes. It now documents enabled catalog behavior, excluded-model inspection endpoints, local utility nodes, and API-first V10 advanced workflows.

### PROJECT_SUMMARY.md

Claims the project is FastAPI plus React/React Flow with static assets served from `web/`. It summarizes endpoints, storage, architecture boundaries, project settings, prompt-source rules, visual connector behavior, run manager behavior, validation commands, manual testing, catalog-scale enabled models, excluded-model inspection, local utility nodes, and V10 API-first workflows.

### CODEX_TASKS.md

Defines historical phased work. It is now explicitly labeled as historical build order, not the current implementation contract. The current contract is AGENTS/README/FINAL context, with React + React Flow in `frontend/`.

### AGENTS.md

Sets the current active project rules: backend stays FastAPI; frontend is React + React Flow in `frontend/`, built to static `web/` assets served by FastAPI; no Next.js, Tailwind, database, auth, billing, background workers, or pro editing tools; no hardcoded secrets; WaveSpeed SDK access stays in `wavespeed_adapter.py`; execution in `node_runner.py`; metadata in `model_catalog.py`/`registry.py`; workflow mapping in `workflow_resolver.py`; local project storage remains backward compatible.

### README.md

Describes setup, running, local tests, React frontend build/dev commands, catalog endpoints, current MVP behavior, V8 UI migration, V9 curated model enablement, V10 workflow layer, utility-node table, portability, and V11 catalog scale-out. It now distinguishes curated starter models from the full enabled catalog and documents the excluded-model inspection path.

## 3. Requirement Coverage Matrix

| ID | Functional area | Requirement | Source file + section/line reference if available | Implementation evidence | Test evidence | Status | Priority | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RQ-001 | Architecture | Backend uses Python FastAPI. | AGENTS.md Project Rules; requirements.md section 7 | `app/main.py` creates FastAPI app, includes routers, mounts uploads/static frontend. | Route/service tests use FastAPI `TestClient` throughout `tests/`. | Implemented | P0 | Aligned. |
| RQ-002 | Architecture | WaveSpeed SDK access stays behind adapter; model execution stays in node runner; workflow mapping stays in workflow resolver. | AGENTS.md Architecture Rules; requirements.md WaveSpeed adapter section | `app/services/wavespeed_adapter.py`; `app/services/node_runner.py`; `app/services/workflow_resolver.py`. | `tests/test_v10_wavespeed_only_guard.py`, `tests/test_node_runner_preparers.py`, workflow tests. | Implemented | P0 | Aligned. |
| RQ-003 | Frontend architecture | Current frontend is React + React Flow built to static assets served by FastAPI. | AGENTS.md; README "What is included"; PROJECT_SUMMARY Architecture; FINAL_PROJECT_CONTEXT Current Architecture | `frontend/package.json`, `frontend/src/main.jsx`, `web/index.html`, `web/assets/*`. | `npm run build --prefix frontend`; JS syntax validation on latest built asset; Playwright smoke tests. | Implemented | P1 | Aligned. |
| RQ-004 | Validation | Compile backend, build frontend, check built JS, run unittests, run Playwright smoke, and start uvicorn. | AGENTS.md; FINAL_PROJECT_CONTEXT; PROJECT_SUMMARY | Commands are documented for backend/frontend build and test paths; `frontend/package.json` includes `test:e2e`. | `npm run test:e2e --prefix frontend` passes; previous backend validations pass. | Implemented | P1 | Aligned. |
| RQ-005 | Projects | Create, rename, save, reopen/load, and delete projects. | requirements.md section 5.1; PROJECT_SUMMARY endpoints | `app/routers/projects.py`; `frontend/src/main.jsx` has create/load/save/delete; local JSON in `project_store.py`. | Python project tests; Playwright smoke covers delete reachability and save/reload edge persistence through the project API. | Implemented | P1 | Aligned. |
| RQ-006 | Project persistence | Project JSON includes ID, name, description, nodes, edges, assets, timestamps, and remains backward compatible. | requirements.md section 5.1; AGENTS.md Architecture Rules | `app/schemas.py`, `project_store.py`, import/export validation. | `tests/test_v3.py`, `tests/test_v4.py`, `tests/test_v5.py`. | Implemented | P1 | Aligned. |
| RQ-007 | Canvas | Add/select/move/connect nodes, persist positions/edges, show status, show output thumbnail/link. | requirements.md section 5.2; FINAL_PROJECT_CONTEXT current behavior | React Flow canvas in `frontend/src/main.jsx`, `onNodesChange`, `onConnect`, click-to-connect handles, edge validation, `OutputPreview`. | Backend edge/workflow tests; Playwright smoke covers loaded nodes, add-node reachability, node dragging, save payload for changed positions, manual handle edge creation, saved edge payload, and reload persistence. | Implemented | P2 | Aligned. |
| RQ-008 | Node library | Sidebar/context menu shows model categories and lets users add nodes. | requirements.md section 5.3; README V11 | Frontend fetches `/api/models?enabled_only=true`, groups by provider/category, has rail library and right-click context menu. | Registry/catalog tests; Playwright smoke covers model and utility add-node buttons. | Implemented | P1 | Aligned. |
| RQ-009 | Model visibility | Normal add-node menus show enabled models; runtime-excluded catalog rows are inspectable separately. | requirements.md section 9.5; README V9/V11; PROJECT_SUMMARY; FINAL_PROJECT_CONTEXT | Registry check: 1015 models, 1015 enabled, 0 disabled; `/api/model-catalog/excluded`; frontend uses enabled-only models. | `tests/test_model_registry_contract.py`; catalog API tests. | Implemented | P1 | Former disabled-placeholder contradiction resolved. |
| RQ-010 | Assets | Upload local assets, optionally upload to cloud, select/use them in nodes. | requirements.md section 5.5; README implementation notes; FINAL_PROJECT_CONTEXT manual test | `app/routers/assets.py`; frontend asset rail and node-local upload/select controls; `workflow_resolver.py` resolves asset IDs/URLs. | Asset resolver/model input tests; Playwright smoke covers asset rail upload. | Implemented | P1 | Aligned. |
| RQ-011 | Upload/Asset Input node | Upload Asset/Asset Input acts as a graph source for selected/uploaded assets. | requirements.md Upload Image/utility sections; README V9 upload node note | `registry.py`/`utility_tools.py` expose asset fields; frontend mirrors selected/uploaded asset into node outputs; planner treats upload as non-runnable source. | `tests/test_v10_utility_nodes.py`; Playwright covers utility add-node reachability. | Implemented | P1 | Aligned. |
| RQ-012 | Prompt sourcing | Model prompt/text fields come from Prompt Card, LLM, or transcript nodes. | requirements.md prompt/text rule; README V10; PROJECT_SUMMARY Prompt Source Rule; FINAL_PROJECT_CONTEXT Prompt Source Rule | `workflow_resolver.py` validates prompt sources; frontend locks prompt fields and shows connected-input placeholders. | `tests/test_v10_utility_nodes.py`; Playwright smoke includes connected Prompt Card/Text to Image. | Implemented | P2 | Aligned. |
| RQ-013 | Node execution | `POST /api/runs/node` executes enabled WaveSpeed models and stores results when saving to a project. | requirements.md section 6.4; README current behavior | `app/routers/runs.py`, `node_runner.py`, `wavespeed_adapter.py`, `local_utility_runner.py`. | `tests/test_v3.py`, `tests/test_node_runner_preparers.py`, `tests/test_generic_wavespeed_runner.py`, `tests/test_v10_utility_nodes.py`. | Implemented | P0 | Broad mock coverage. |
| RQ-014 | Workflow planning/execution | Preview/run selected, downstream/from-node, and whole graph; detect cycles/missing inputs; aggregate cost. | FINAL_PROJECT_CONTEXT V2/V4/V7; PROJECT_SUMMARY Workflow/Run Manager | `workflow_resolver.py`, `workflows.py`, `jobs.py`, `run_manager.py`, frontend workflow/run controls. | `tests/test_v4.py`, `tests/test_v6.py`, `tests/test_v7.py`; Playwright smoke covers whole-graph queue entry point with mocked jobs. | Implemented | P1 | Aligned. |
| RQ-015 | Cost guard/model overrides | Project settings support compatible model overrides and cost guard warnings/blocks. | PROJECT_SUMMARY Project Settings; FINAL_PROJECT_CONTEXT V4 | `projects.py` settings endpoints, `project_validation.py`, `cost_estimator.py`, settings UI. | `tests/test_v4.py`. | Implemented | P1 | Aligned. |
| RQ-016 | Cost display | Frontend displays estimates in MYR while backend settings/cost guard remain USD. | README implementation notes; PROJECT_SUMMARY Project Settings; FINAL_PROJECT_CONTEXT Cost Display Convention | `frontend/src/main.jsx` uses `DISPLAY_USD_TO_MYR_RATE = 4.06`; backend fields remain `*_usd`. | Backend USD cost tests; Playwright smoke checks `RM0.0203` run label. | Implemented | P3 | Aligned. |
| RQ-017 | Output previews/actions | Show generated image/video/audio/text/other previews plus open/copy/download actions and raw response details. | requirements.md canvas/error sections; FINAL_PROJECT_CONTEXT current behavior; CODEX_TASKS Phase 5 | `OutputPreview`, `OutputItem`, `PreviewMedia` in `frontend/src/main.jsx`. | Backend output normalizer tests; Playwright smoke covers Open, Copy URL, Download, Raw response. | Implemented | P2 | Aligned. |
| RQ-018 | Project portability/templates | Export/import portable JSON, duplicate projects, built-in/user templates. | README Portability; FINAL_PROJECT_CONTEXT V5; PROJECT_SUMMARY frontend behavior | `portable_project.py`, `templates.py`, `project_recipes.py`; frontend export/import/duplicate/templates/recipes controls. | `tests/test_v5.py`, `tests/test_v10_recipes.py`. | Implemented | P1 | Aligned. |
| RQ-019 | V10 advanced workflows | Variants, model comparison, artifact lineage, branch from artifacts, export packages, run snapshots, recipes. | README V10; PROJECT_SUMMARY V10 reachability; docs/V10_WEAVE_PARITY_MAP.md | Backend routers/services exist; docs now state advanced V10 paths are API-first where not UI-exposed. | `tests/test_v10_*` files cover backend/service behavior. | Implemented | P2 | Not a UI gap because current docs explicitly say API-first. |
| RQ-020 | V11 catalog scale-out | 1000+ model catalog, exact model IDs, generic WaveSpeed runtime, catalog endpoints. | requirements.md V11 paragraph; docs/V11_CATALOG_SCALEOUT.md; README catalog endpoints | `catalog_repository.py`, `model_catalog.py`, `registry.py`, `generic_wavespeed` runner path; `/api/model-catalog/*`. | Catalog repository/API/generic runner tests. | Implemented | P1 | Aligned. |
| RQ-021 | Local utility nodes | Local utility nodes orchestrate prompts/assets/comparison/export metadata, plus last-frame and stitch-video utilities. | requirements.md utility table; README utility table; PROJECT_SUMMARY; FINAL_PROJECT_CONTEXT | `utility_tools.py`, `local_utility_runner.py`, frontend utility menu/cards. | `tests/test_v10_utility_nodes.py`; Playwright utility add-node smoke. | Implemented | P2 | Former documentation gap resolved. |
| RQ-022 | Error handling | Backend returns clear errors; frontend shows node status/errors and debugging response data. | requirements.md Error handling; README notes | Routers raise detailed `HTTPException`; frontend sets status/error messages and raw output details. | Backend error-path tests; Playwright raw response smoke. | Implemented | P2 | Aligned for MVP. |
| RQ-023 | Browser/UI tests | Tests should prove required functional UI behavior. | Audit definition; CODEX_TASKS Phase 1/5 | `frontend/tests/ui-smoke.spec.js` with mocked API; `frontend/playwright.config.js`; `frontend/package.json` `test:e2e`. | 7 Playwright tests pass, including manual handle edge creation and reload persistence. | Implemented | P2 | Aligned. |

## 4. Missing / Partial Functional Requirements

No missing or partial functional requirements remain against the current MVP source documents. The audit found no P0/P1/P2/P3 functional gaps after aligning stale docs and adding browser smoke evidence for manual edge creation and reload persistence.

## 5. Requirements Implemented But Not Documented

- No major useful current behavior remains completely undocumented in the six source docs after this pass.
- Minor UI polish features, such as provider icon choices and auto-tidy details, are documented only at a high level. They are not MVP functional requirements.

## 6. Contradictions / Stale Requirements

- Historical phase text still exists in `CODEX_TASKS.md` and task summaries, but it is now labeled or contextualized as historical. The active docs agree that the current frontend is React + React Flow.
- The old `web/app.js` scaffold remains in `requirements.md` as historical scaffold, while current implementation is `frontend/src/main.jsx` built to `web/assets`.
- No current source doc now requires disabled placeholder cards as normal runnable model menu entries.

## 7. Suggested Next Implementation Batches

### Batch 1: highest confidence, smallest change

1. Keep the new browser smoke suite in the regular validation path.
2. Add focused tests when new user-facing workflow controls are added.
3. Keep source docs updated in the same change when MVP behavior changes.

### Batch 2: important but broader

1. Add screenshot regression checks for high-risk UI areas if visual churn increases.
2. Add more granular run-manager polling tests if polling behavior becomes a primary MVP promise.

### Batch 3: future/backlog

1. Add optional docs-to-registry checks for model counts/enabled status.
2. Add optional coverage for more advanced API-first V10 workflows if they become first-class UI flows.

## 8. Validation Commands

Run these exact commands after future implementation:

```powershell
python -m compileall app
npm run build --prefix frontend
$latestJs = Get-ChildItem web\assets\*.js | Sort-Object LastWriteTime -Descending | Select-Object -First 1
node --check $latestJs.FullName
python -m unittest discover -s tests -v
npm run test:e2e --prefix frontend
python -m uvicorn app.main:app --reload --port 8000
```

Manual browser smoke after implementation:

1. Open `http://localhost:8000`.
2. Create/load a project.
3. Add Prompt Card and Text to Image nodes.
4. Connect Prompt Card output to model prompt input.
5. Upload/select a local asset.
6. Save, refresh, and reload.
7. Preview plan and run only if cost guard allows it.
8. Confirm output preview, Open/Copy URL/Download actions, and run history.
