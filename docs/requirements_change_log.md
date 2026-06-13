# Requirements Change Log

Date: 2026-06-13

## What Changed

- Replaced the older mixed historical/future `requirements.md` with a clean current-state product requirements document.
- Based the new active requirements on `requirements.generated.md` and verified repository evidence.
- Preserved stable functional requirement IDs from `FR-001` through `FR-027`.
- Added acceptance criteria to every functional requirement.
- Added active architecture requirements for the current FastAPI plus React/React Flow implementation.
- Added API requirements grouped by feature area.
- Added data requirements for projects, nodes, edges, assets, jobs, catalog data, uploads, and configuration.
- Added non-functional requirements that are directly supported by code/docs.
- Added validation commands and a manual smoke path.
- Added a traceability matrix mapping each FR to backend files, frontend files, and tests.

## What Was Removed

- Removed legacy language implying the MVP frontend can be a simple DOM canvas while the production direction is future React Flow. The current implementation already uses React + React Flow.
- Removed future storage plans such as SQLite, PostgreSQL, and object storage from active requirements.
- Removed speculative target workflows that were examples rather than verified product requirements.
- Removed unaccepted future features from active scope, including auth, billing, database persistence, durable external workers, WebSockets/SSE, and collaboration.
- Removed references to professional editing features as potential requirements; they remain explicitly out of scope.
- Removed proposed production-hardening items from active requirements unless currently implemented.
- Removed uncertain catalog/live-model verification claims from active requirements.

## What Was Kept

- Kept FastAPI as the backend requirement.
- Kept React + React Flow as the current frontend requirement because it is the verified implementation in `frontend/`.
- Kept local JSON project persistence under `data/projects`.
- Kept local upload/template filesystem storage.
- Kept WaveSpeed SDK isolation behind `app/services/wavespeed_adapter.py`.
- Kept model execution in `app/services/node_runner.py`.
- Kept workflow planning and input mapping in `app/services/workflow_resolver.py`.
- Kept model/category metadata ownership in `model_catalog.py`, `registry.py`, `utility_tools.py`, and catalog data files.
- Kept project CRUD, canvas behavior, node creation/editing, edge persistence, asset upload, node/workflow execution, job queue, run history, output previews, branching, cost guard, model overrides, import/export/duplicate, templates, recipes, catalog inspection, generic catalog execution, local utilities, artifact APIs, advanced API-first V10 tools, error handling, and automated validation.

## What Still Needs Confirmation

- Whether React + React Flow is the permanent frontend contract despite earlier vanilla-JS instructions.
- Whether advanced API-first workflows should become full first-class UI panels.
- Which of the 1000+ catalog models should be considered product-supported after live verification.
- Whether local JSON should remain the MVP persistence layer or be replaced by a database in a future milestone.
- Whether job state should become durable across server restarts.
- What policy should govern MYR cost display and exchange-rate updates.
- Whether asset cleanup, quotas, and upload management should be prioritized next.
- Whether all text-like catalog fields should use the prompt-source rule.
- Whether excluded catalog rows should appear in the frontend as inspect-only records.
