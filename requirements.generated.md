# Requirements — Generated From Current Project

Generated date: 2026-06-13

This document is reverse-engineered from the current repository implementation. It does not replace `requirements.md`. Requirement statuses mean:

- **Verified:** directly supported by code, tests, or current docs.
- **Inferred:** likely intended from implementation shape, but not explicitly documented.
- **Proposed:** useful future requirement, not currently implemented.
- **Unknown:** behavior is unclear from available evidence.

## 1. Project Overview

The application is a local MVP AI canvas workflow builder for composing media generation workflows around WaveSpeed models. The backend is a Python FastAPI app in `app/`. The current frontend source is a React + React Flow app in `frontend/`, built into static assets under `web/`, which FastAPI serves at `/`.

Users can create local projects, add model and utility nodes to a visual canvas, connect nodes through graph edges, upload/select assets, queue single-node or workflow runs, preview generated outputs, branch from artifacts, manage local project settings, use model overrides and local cost guard controls, export/import/duplicate projects, and create projects from templates or recipes.

Storage is local JSON and filesystem-based. There is no database, authentication, billing, background-worker service, or professional media editor.

## 2. Product Goal

The product goal is to provide a simple "Weave-lite" creative workflow canvas for AI media generation. The main user goal is to assemble reusable prompt, asset, model, and utility nodes into a graph, run the graph through WaveSpeed-backed models or local utilities, inspect outputs, and save/reload the workflow state locally.

## 3. Target Users

- **Verified:** Local developer/operator testing WaveSpeed model workflows.
  - Evidence: `README.md` setup and curl commands; `AGENTS.md` local run commands; local JSON storage in `app/core/config.py`.
- **Inferred:** Creative technologist building prompt-to-media and media-to-media workflows.
  - Evidence: node catalog, Prompt Card, asset inputs, image/video/audio/avatar/3D categories, branching, previews, recipes.
- **Inferred:** Product/engineering collaborator using Codex to expand the MVP.
  - Evidence: `CODEX_TASKS.md`, `TASK_V*.md`, `docs/functional_requirement_gap_audit.md`.
- **Unknown:** Multi-user teams, paid customers, or production administrators are not modeled in the current implementation.

## 4. Current Scope

- **Verified:** FastAPI backend with documented routes under `/api/*`.
- **Verified:** React + React Flow source app under `frontend/`, built into `web/` for FastAPI static serving.
- **Verified:** Local project CRUD using JSON files in `data/projects`.
- **Verified:** Project settings with model overrides and local cost guard thresholds.
- **Verified:** Local asset upload into `data/uploads`, with optional upload to WaveSpeed.
- **Verified:** WaveSpeed SDK access isolated to `app/services/wavespeed_adapter.py`.
- **Verified:** Model execution isolated to `app/services/node_runner.py`.
- **Verified:** Workflow planning/input mapping isolated to `app/services/workflow_resolver.py`.
- **Verified:** Registry/model metadata from `app/services/model_catalog.py`, `app/services/registry.py`, and `app/data/wavespeed_catalog.normalized.json`.
- **Verified:** 1015 registry model specs and 13 local utility tools are exposed by the current registry.
- **Verified:** Single-node queueing, workflow queueing, job status, cancel, retry, clear completed.
- **Verified:** Project export/import/duplicate and templates.
- **Verified:** API-first V10 surfaces for artifacts, variants, model comparison, export packages, recipes, and run snapshots.
- **Verified:** Browser smoke tests cover main UI reachability for loading, adding nodes, uploading, dragging, connecting, saving edge state, queueing workflow, and deleting projects.

## 5. Out of Scope

- **Verified:** No Next.js, Tailwind, database, auth, billing, background workers, Redis/Celery, WebSockets/SSE, or professional editing tools.
  - Evidence: `AGENTS.md`, `README.md`, `FINAL_PROJECT_CONTEXT.md`.
- **Verified:** No layers, masks editor, brush editor, timeline, vector editor, crop studio, or Photoshop-like panels.
  - Evidence: `requirements.md` and `README.md`.
- **Verified:** No invented model parameters for unverified model categories.
  - Evidence: `requirements.md`, `CODEX_TASKS.md`, `node_runner.py` preparer tests.
- **Verified:** Runtime-excluded catalog rows are not normal runnable add-node cards.
  - Evidence: `requirements.md`, `app/routers/model_catalog.py`, `app/services/catalog_repository.py`.
- **Proposed:** Production user management, cloud storage, persistent queue workers, billing, and collaborative editing are future concerns only.

## 6. Functional Requirements

### FR-001: Serve The Application Locally
- Status: Verified
- Priority: P0
- Source evidence:
  - `app/main.py`
  - `lifespan`, `app.mount("/uploads", ...)`, `app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")`
  - FastAPI starts the run manager and serves uploads plus built frontend files.
- User story:
  - As a local user, I want one FastAPI server to expose the API and app UI, so that I can use the workflow app at `localhost:8000`.
- Acceptance criteria:
  - Given dependencies are installed
  - When I run `python -m uvicorn app.main:app --reload --port 8000`
  - Then `/docs` exposes API docs and `/` serves the built frontend.
- Current implementation notes:
  - `frontend/` is source only; `web/` is served runtime output.
- Gaps:
  - Unknown whether the repository intentionally keeps stale built asset hashes during development.

### FR-002: Create, Load, Update, And Delete Projects
- Status: Verified
- Priority: P0
- Source evidence:
  - `app/routers/projects.py`
  - `list_projects`, `create_project`, `get_project`, `update_project`, `delete_project`
  - `frontend/src/main.jsx` calls `/api/projects` and `/api/projects/{project_id}`.
  - `tests/test_v4.py`, `tests/test_v5.py`, `frontend/tests/ui-smoke.spec.js`.
- User story:
  - As a workflow user, I want to create, edit, save, reload, and delete projects, so that I can manage local workflow files.
- Acceptance criteria:
  - Given the app is running
  - When I create a project
  - Then it is saved as a local JSON-backed project and appears in the project list.
  - Given an existing project
  - When I update name, description, nodes, edges, assets, runs, or settings
  - Then `PUT /api/projects/{project_id}` persists the update.
  - Given a project
  - When I delete it
  - Then the API returns `{ "ok": true }`.
- Current implementation notes:
  - Projects are Pydantic `Project` objects persisted by `app/services/project_store.py`.
  - Invalid project IDs return 400; missing projects return 404.
- Gaps:
  - No user ownership or server-side undo.

### FR-003: Persist Local Project Data
- Status: Verified
- Priority: P0
- Source evidence:
  - `app/schemas.py`
  - `Project`, `CanvasNode`, `CanvasEdge`, `Asset`, `ProjectSettings`
  - `data/projects/*.json` sample files.
  - `tests/test_v3.py`, `tests/test_v4.py`, `tests/test_v5.py`, `tests/test_v6.py`.
- User story:
  - As a user, I want project state to persist across browser refreshes and server restarts, so that my workflow is not lost.
- Acceptance criteria:
  - Given a project with nodes, edges, assets, runs, settings, and positions
  - When the project is saved
  - Then the same structure can be loaded later from local JSON.
- Current implementation notes:
  - Project fields include `id`, `name`, `description`, `nodes`, `edges`, `assets`, `runs`, `variant_sets`, `comparison_sets`, `export_packages`, `settings`, and timestamps.
  - Backward compatibility aliases exist for edge fields.
- Gaps:
  - No migration/version field on raw project JSON was observed beyond export envelopes.

### FR-004: Render A Visual Canvas
- Status: Verified
- Priority: P1
- Source evidence:
  - `frontend/src/main.jsx`
  - `App`, `WorkflowCard`, `NodeSettingsPopover`, React Flow imports/components.
  - `frontend/tests/ui-smoke.spec.js`.
- User story:
  - As a user, I want to see workflow nodes on a canvas, so that I can understand and edit media generation flow visually.
- Acceptance criteria:
  - Given a loaded project
  - When the UI renders
  - Then project nodes appear as cards at saved `x`/`y` positions.
  - Given I drag a node
  - When I save the project
  - Then the changed position is included in the saved payload.
- Current implementation notes:
  - The current UI uses React Flow. Node settings are shown in a right-side popover for model nodes; utility nodes retain inline fields.
  - Browser smoke covers dragged node position persistence.
- Gaps:
  - No multi-user collaboration; no pro canvas editing tools.

### FR-005: Add Model And Utility Nodes
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/routers/models.py`
  - `list_models`, `list_categories`, `list_tools`
  - `app/services/registry.py`, `app/services/utility_tools.py`
  - `frontend/src/main.jsx` model and utility rail/context menus.
  - `frontend/tests/ui-smoke.spec.js`.
- User story:
  - As a user, I want to add model and utility cards to the canvas, so that I can build a workflow from reusable parts.
- Acceptance criteria:
  - Given `/api/models?enabled_only=true` returns model specs
  - When I click Add Node in the model or utility menu
  - Then a node is added to the current project canvas.
- Current implementation notes:
  - Registry contains 1015 enabled model specs and 13 utility tools at generation time.
  - Utility tools include Prompt Card, Style Card, Character Card, Asset Input, Asset Selector, Compare Board, Variant Batch, Reroute, Note, Group Frame, Export Package, Video Last Frame, and Stitch Videos.
- Gaps:
  - Unknown whether every catalog model has been manually verified against live WaveSpeed behavior.

### FR-006: Edit Node Inputs
- Status: Verified
- Priority: P1
- Source evidence:
  - `frontend/src/main.jsx`
  - `NodeSettingsPopover`, `NodeField`, `WorkflowCard`
  - `app/schemas.py` `ModelField`, `WaveSpeedCatalogField`.
- User story:
  - As a user, I want model and utility nodes to expose appropriate input controls, so that I can configure runs without editing raw JSON.
- Acceptance criteria:
  - Given a node with field metadata
  - When it is selected
  - Then editable inputs render from the field schema.
  - Given a prompt-like model field
  - When it is displayed
  - Then it is treated as a connected input rather than a freeform model-card prompt field.
- Current implementation notes:
  - Model node settings are in the right-side selected-node panel.
  - Prompt-like saved model inputs are expected to come from Prompt Card, LLM, or transcript nodes.
- Gaps:
  - Unknown whether every schema field type from the 1000+ catalog renders optimally.

### FR-007: Connect Nodes With Edges
- Status: Verified
- Priority: P1
- Source evidence:
  - `frontend/src/main.jsx`
  - `onConnect`, `handleQuickConnect`, handle test IDs.
  - `app/schemas.py` `CanvasEdge`
  - `app/services/workflow_resolver.py`
  - `tests/test_v6.py`, `frontend/tests/ui-smoke.spec.js`.
- User story:
  - As a user, I want to wire outputs into downstream inputs, so that one node can feed another.
- Acceptance criteria:
  - Given a Prompt Card and Text to Image node
  - When I connect the Prompt Card output to the Text to Image prompt input
  - Then an edge is created and saved with `target_input` equal to `prompt`.
  - Given I reload the project
  - When the canvas renders
  - Then the saved edge is visible.
- Current implementation notes:
  - The UI supports React Flow drag connections and a click output then click input fallback.
  - Backend workflow resolver normalizes edge aliases and detects cycles/missing references.
- Gaps:
  - Advanced edge routing is intentionally absent.

### FR-008: Validate Prompt Source Rules
- Status: Verified
- Priority: P1
- Source evidence:
  - `requirements.md`
  - `app/services/workflow_resolver.py`
  - `validate_prompt_card_inputs`
  - `tests/test_v10_utility_nodes.py`.
- User story:
  - As a user, I want reusable text prompts to live in text-source nodes, so that model cards can be clean and branchable.
- Acceptance criteria:
  - Given a model node with a required prompt/text input
  - When no valid Prompt Card, LLM, or transcript source is connected
  - Then planning or saved-node execution returns a clear error.
- Current implementation notes:
  - The frontend shows connected-input placeholders for prompt fields.
  - Backend rejects missing or invalid prompt-source wiring.
- Gaps:
  - Unknown whether all text-like catalog fields should follow this rule or only known prompt/text inputs.

### FR-009: Upload And Select Assets
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/routers/assets.py`
  - `upload_asset`, `infer_asset_kind`
  - `app/services/model_input_resolver.py`, `node_runner.py`
  - `frontend/src/main.jsx` asset upload calls.
  - `tests/test_asset_resolution.py`, `tests/test_model_input_resolver.py`, `frontend/tests/ui-smoke.spec.js`.
- User story:
  - As a user, I want to upload local files and use them as graph inputs, so that image/video/audio models can consume my assets.
- Acceptance criteria:
  - Given a file under the upload size limit
  - When I upload it
  - Then the API stores it in `data/uploads`, infers its kind, and returns an `Asset`.
  - Given `upload_to_wavespeed=true`
  - When upload succeeds
  - Then the returned asset includes `wavespeed_url`.
- Current implementation notes:
  - Supported inferred kinds are image, video, audio, and other.
  - Default max upload size is 50 MB.
  - Localhost URLs are rejected for remote WaveSpeed inputs.
- Gaps:
  - No asset cleanup/storage-management UI.

### FR-010: Execute A Single Node
- Status: Verified
- Priority: P0
- Source evidence:
  - `app/routers/runs.py`
  - `run_node`, `run_saved_local_utility_node`
  - `app/services/node_runner.py`
  - `tests/test_v3.py`, `tests/test_node_runner_preparers.py`, `tests/test_generic_wavespeed_runner.py`.
- User story:
  - As a user, I want to run one node, so that I can generate or transform one output before running a larger workflow.
- Acceptance criteria:
  - Given a runnable saved model node with valid inputs
  - When I run it
  - Then the app resolves model inputs, checks cost guard, calls WaveSpeed through the adapter, stores node output metadata, and returns output URLs/assets.
  - Given a runnable local utility node
  - When I run it from a saved project
  - Then it runs locally and returns local output assets.
- Current implementation notes:
  - `/api/runs/node` can run immediately.
  - The frontend usually queues runs through `/api/jobs/node`.
- Gaps:
  - Live WaveSpeed success depends on valid `WAVESPEED_API_KEY` and external API availability.

### FR-011: Integrate With WaveSpeed Through An Adapter
- Status: Verified
- Priority: P0
- Source evidence:
  - `app/services/wavespeed_adapter.py`
  - `app/services/node_runner.py`
  - `tests/test_v10_wavespeed_only_guard.py`.
- User story:
  - As a developer, I want all WaveSpeed SDK usage isolated, so that model execution remains maintainable and secrets stay controlled.
- Acceptance criteria:
  - Given app code outside the adapter
  - When scanning imports
  - Then non-WaveSpeed AI clients are not imported.
  - Given `WAVESPEED_API_KEY` is missing
  - When a WaveSpeed call needs credentials
  - Then the adapter returns a clear error.
- Current implementation notes:
  - Adapter exposes model runs, LLM chat, file upload, and output URL extraction.
- Gaps:
  - Unknown retry/backoff behavior for transient WaveSpeed failures.

### FR-012: Plan And Execute Workflows
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/routers/workflows.py`
  - `get_workflow_plan`, `run_selected_node`, `run_from_node`, `run_all`
  - `app/services/workflow_resolver.py`
  - `tests/test_v4.py`, `tests/test_v6.py`, `tests/test_v7.py`.
- User story:
  - As a user, I want to preview and run selected, downstream, or whole-graph workflows, so that I can execute connected nodes in order.
- Acceptance criteria:
  - Given a graph with connected nodes
  - When I request a workflow plan
  - Then the API returns runnable nodes, warnings, errors, cost totals, and cost guard status.
  - Given a valid graph
  - When I run selected/from-node/all
  - Then the API executes nodes in resolved order or queues jobs through the Run Manager.
- Current implementation notes:
  - Direct workflow run endpoints execute synchronously.
  - Job queue workflow endpoints are used by the frontend for normal queueing.
- Gaps:
  - No parallel execution; no durable external queue.

### FR-013: Queue Jobs And Track Progress
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/routers/jobs.py`
  - `app/services/run_manager.py`
  - `app/schemas.py` `RunJob`
  - `tests/test_v7.py`.
- User story:
  - As a user, I want node and workflow runs to be queued with visible status, so that the UI does not block while generation is running.
- Acceptance criteria:
  - Given a saved project node
  - When I queue a node job
  - Then a `RunJob` is returned with status and progress fields.
  - Given a queued or running job
  - When I cancel it
  - Then queued jobs cancel immediately and running jobs become cancel-requested.
  - Given a failed or cancelled job
  - When I retry it
  - Then a new job ID is created.
- Current implementation notes:
  - The queue is in-memory and one local worker is started from FastAPI lifespan.
  - Completed terminal jobs are written into project run history.
- Gaps:
  - Jobs disappear on server restart except persisted terminal run history.

### FR-014: Show Run History
- Status: Verified
- Priority: P2
- Source evidence:
  - `app/routers/workflows.py` `list_workflow_runs`
  - `app/services/run_manager.py`
  - `README.md` Local Run Manager section.
  - `tests/test_v7.py`.
- User story:
  - As a user, I want completed runs saved in the project, so that I can inspect previous generation results.
- Acceptance criteria:
  - Given a job reaches a terminal state
  - When the project is saved
  - Then the run history contains the terminal job/run data and is capped to recent entries.
- Current implementation notes:
  - Docs say run history is capped to latest 100 entries.
- Gaps:
  - Unknown exact breadth of frontend run-history filtering/search.

### FR-015: Display Output Previews And Actions
- Status: Verified
- Priority: P1
- Source evidence:
  - `frontend/src/main.jsx`
  - `OutputPreview`, `OutputItem`, `PreviewMedia`
  - `app/services/model_output_normalizer.py`
  - `tests/test_model_output_normalizer.py`, `frontend/tests/ui-smoke.spec.js`.
- User story:
  - As a user, I want to preview generated outputs and copy/open/download them, so that I can inspect and reuse results.
- Acceptance criteria:
  - Given a node with output URLs or assets
  - When the node card renders
  - Then media previews and Open/Copy URL/Download/Raw response actions are available where applicable.
- Current implementation notes:
  - Supports image/video/audio/text/other output shapes.
- Gaps:
  - Unknown whether every remote content type previews correctly in browser.

### FR-016: Branch From Outputs Or Artifacts
- Status: Verified
- Priority: P2
- Source evidence:
  - `frontend/src/main.jsx` branch action.
  - `app/routers/artifacts.py` `branch_artifact`
  - `app/services/branching.py`
  - `tests/test_v10_branching.py`.
- User story:
  - As a user, I want to create a downstream node from an existing output, so that I can remix or continue media generation.
- Acceptance criteria:
  - Given an image, audio, or text-like artifact
  - When I branch from it with a compatible target
  - Then a new node and edge are created.
  - Given an incompatible target
  - When branching is requested
  - Then the API returns a clear 400 error.
- Current implementation notes:
  - Frontend branch buttons exist for image outputs.
  - API-first artifact branching covers broader artifact types.
- Gaps:
  - Full artifact-branch UI reachability appears narrower than API capability.

### FR-017: Configure Cost Guard And Model Overrides
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/routers/projects.py` settings routes.
  - `app/schemas.py` `ProjectSettings`, `CostGuardSettings`
  - `app/services/project_validation.py`, `app/services/cost_estimator.py`
  - `tests/test_v4.py`.
- User story:
  - As a user, I want local cost guard and model override settings, so that I can avoid accidental expensive runs and choose compatible defaults.
- Acceptance criteria:
  - Given valid settings
  - When I update project settings
  - Then settings persist.
  - Given invalid cost thresholds or incompatible model overrides
  - When I update settings
  - Then the API rejects the update.
  - Given a blocked cost estimate
  - When I run a node or workflow
  - Then execution is blocked before model execution.
- Current implementation notes:
  - Backend stores and evaluates cost in USD.
  - Frontend displays estimates in MYR using a UI-only conversion.
- Gaps:
  - Cost is an estimate, not exact billing.

### FR-018: Export, Import, And Duplicate Projects
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/routers/projects.py`
  - `export_project`, `import_project`, `duplicate_project`
  - `app/services/portable_project.py`
  - `tests/test_v5.py`.
- User story:
  - As a user, I want portable project JSON export/import and duplication, so that I can reuse or share workflow structures locally.
- Acceptance criteria:
  - Given a project
  - When I export it
  - Then local filesystem paths are stripped and export metadata is returned.
  - Given a valid export
  - When I import it
  - Then new project/node/edge/asset IDs are generated and runtime state is reset according to options.
  - Given invalid nodes or broken edge references
  - When importing
  - Then the API rejects the import.
- Current implementation notes:
  - Import accepts multipart JSON file or JSON body.
  - Max import JSON size defaults to 2 MB.
- Gaps:
  - No cloud sync or collaborative sharing.

### FR-019: Manage Workflow Templates
- Status: Verified
- Priority: P2
- Source evidence:
  - `app/routers/templates.py`
  - `app/services/template_store.py`
  - `tests/test_v5.py`.
- User story:
  - As a user, I want built-in and user-saved templates, so that I can start workflows quickly.
- Acceptance criteria:
  - Given templates exist
  - When I list templates
  - Then built-in/user templates are returned.
  - Given a project
  - When I save it as a template
  - Then a reusable local template is stored.
  - Given a built-in template
  - When I try to delete it
  - Then deletion is rejected.
- Current implementation notes:
  - User templates persist under `data/templates`.
- Gaps:
  - No template marketplace or remote templates.

### FR-020: Manage Recipes
- Status: Verified
- Priority: P2
- Source evidence:
  - `app/routers/recipes.py`
  - `app/routers/project_recipes.py`
  - `app/services/recipe_store.py`
  - `tests/test_v10_recipes.py`.
- User story:
  - As a user, I want recipe-based starter workflows, so that I can create common graph patterns faster.
- Acceptance criteria:
  - Given a recipe ID
  - When I create a project from it
  - Then a valid project graph is produced.
  - Given an existing project
  - When I apply a recipe
  - Then recipe nodes/edges are added.
- Current implementation notes:
  - Frontend fetches `/api/recipes`, applies recipes, and creates projects from recipes.
- Gaps:
  - Some recipe capabilities may be notes/placeholder-oriented when a capability is unavailable.

### FR-021: Provide Model Catalog Inspection
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/routers/model_catalog.py`
  - `app/services/catalog_repository.py`
  - `app/data/wavespeed_catalog.normalized.json`
  - `tests/test_model_catalog_api.py`, `tests/test_catalog_repository.py`.
- User story:
  - As a developer/user, I want to inspect available WaveSpeed catalog models and schemas, so that I can choose or debug models.
- Acceptance criteria:
  - Given catalog data exists
  - When I request summary, capabilities, model details, or schema
  - Then the API returns catalog records.
  - Given a search/category/capability query
  - When I list catalog models
  - Then results are filtered and paginated.
- Current implementation notes:
  - Current summary reports 1009 visible catalog models and 0 excluded models.
  - Normal add-node menus are based on enabled registry models, not every raw row blindly.
- Gaps:
  - Unknown whether catalog import source workbook is present in the repo at runtime.

### FR-022: Support Generic Catalog Model Execution
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/services/registry.py`
  - `app/services/node_runner.py`
  - `app/services/model_input_resolver.py`
  - `tests/test_generic_wavespeed_runner.py`, `tests/test_registry_catalog_scaleout.py`.
- User story:
  - As a user, I want catalog models to run by exact WaveSpeed model ID, so that the app can support more than curated starter nodes.
- Acceptance criteria:
  - Given an enabled generic catalog node with a known schema
  - When it runs
  - Then the runner sends the exact catalog `model_id` and prepared inputs to WaveSpeed.
- Current implementation notes:
  - `generic_wavespeed` is a node type.
  - Media/list fields are prepared by schema-aware input resolution.
- Gaps:
  - Runtime compatibility is limited to schema metadata and preparer coverage; not all external model behavior can be proven by tests.

### FR-023: Run Local Utility Nodes
- Status: Verified
- Priority: P2
- Source evidence:
  - `app/services/local_utility_runner.py`
  - `app/services/utility_tools.py`
  - `tests/test_v10_utility_nodes.py`.
- User story:
  - As a user, I want local utility nodes for graph organization and local media operations, so that not every workflow operation spends AI credits.
- Acceptance criteria:
  - Given a `video_last_frame` node with a valid video input
  - When it runs
  - Then a local image asset is created.
  - Given a `stitch_video` node with at least two video inputs
  - When it runs
  - Then a local stitched MP4 asset is created.
- Current implementation notes:
  - Most utility nodes are non-runnable graph helpers.
  - `video_last_frame` and `stitch_video` are runnable local utilities.
- Gaps:
  - Local video utilities depend on local media tooling availability; exact external dependency behavior is Unknown.

### FR-024: Expose Artifact Management APIs
- Status: Verified
- Priority: P2
- Source evidence:
  - `app/routers/artifacts.py`
  - `app/services/artifact_service.py`
  - `tests/test_v10_artifact_lineage.py`, `tests/test_v10_branching.py`.
- User story:
  - As a user, I want generated artifacts to have lineage and view state, so that I can identify inputs, winners, and rejected assets.
- Acceptance criteria:
  - Given a project artifact
  - When I pin, reject, restore, rate, set role, or request lineage
  - Then the project artifact state updates or lineage is returned.
- Current implementation notes:
  - Artifact view state includes pinned, role, label, notes, rating, rejected, and favorite.
- Gaps:
  - Frontend reachability for all artifact state actions is Unknown.

### FR-025: Support Variants, Comparisons, Export Packages, And Run Snapshots
- Status: Verified
- Priority: P3
- Source evidence:
  - `app/routers/variants.py`, `comparisons.py`, `export_packages.py`, `run_snapshots.py`
  - `tests/test_v10_variants.py`, `tests/test_v10_compare.py`, `tests/test_v10_export_package.py`.
- User story:
  - As an advanced user, I want API-first workflow tools for variants, comparisons, export manifests, reruns, and cloning, so that I can evaluate and package outputs.
- Acceptance criteria:
  - Given a project node
  - When I create variants
  - Then variant jobs are queued and tracked.
  - Given compatible models
  - When I request comparison
  - Then comparison jobs/artifacts can be tracked and a winner selected.
  - Given assets
  - When I create an export package
  - Then a manifest with selected artifacts and lineage is persisted.
  - Given a run snapshot
  - When I rerun or clone it
  - Then a job or cloned node is created.
- Current implementation notes:
  - Current docs state these advanced V10 workflows are API-first where the UI is not fully exposed.
- Gaps:
  - Complete frontend panels for these APIs are not clearly implemented.

### FR-026: Display User-Visible Errors
- Status: Verified
- Priority: P1
- Source evidence:
  - `app/main.py` validation handler.
  - Routers raise `HTTPException` with details.
  - `frontend/src/main.jsx` API wrapper and status/error state.
  - `tests/test_v3.py`, `tests/test_v4.py`, `tests/test_v6.py`, `tests/test_v7.py`.
- User story:
  - As a user, I want clear errors when something cannot run or save, so that I can fix workflow inputs.
- Acceptance criteria:
  - Given invalid request data
  - When the API rejects it
  - Then the response contains actionable `detail` or validation `errors`.
  - Given a node run fails
  - When the project is saved
  - Then node status/error fields reflect the failure.
- Current implementation notes:
  - FastAPI validation errors return `{ "detail": "Invalid request", "errors": [...] }`.
- Gaps:
  - Unknown whether all frontend error messages are visually optimal.

### FR-027: Validate The Product With Automated Tests
- Status: Verified
- Priority: P1
- Source evidence:
  - `tests/`
  - `frontend/tests/ui-smoke.spec.js`
  - `frontend/playwright.config.js`
  - `AGENTS.md`.
- User story:
  - As a developer, I want automated tests for backend and browser behavior, so that future changes do not break MVP workflows.
- Acceptance criteria:
  - Given a future implementation change
  - When validation runs
  - Then backend compile, unit tests, frontend build/syntax, and Playwright smoke tests should pass.
- Current implementation notes:
  - Current backend suite includes 109 unittest tests.
  - Current Playwright suite includes 7 browser smoke tests.
- Gaps:
  - Visual screenshot regression tests are not implemented.

## 7. API Requirements

| Method | Route | Purpose | Request body | Response body | Validation rules | Error behavior | Source file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/health` | Health check | None | App/status payload | None found beyond route execution | Unknown from generated evidence if any custom errors | `app/routers/health.py` |
| GET | `/api/categories` | List node/model categories plus utility category | None | `list[CategorySpec]` | None | None expected | `app/routers/models.py` |
| GET | `/api/models` | List registry model specs and utility tools | Query `enabled_only: bool=false` | `list[ModelSpec]` | If `enabled_only`, only enabled specs returned | None expected | `app/routers/models.py` |
| GET | `/api/tools` | List utility tools | None | `list[ModelSpec]` | None | None expected | `app/routers/models.py` |
| GET | `/api/model-catalog` | List WaveSpeed catalog models | Query `include_excluded`, `category`, `capability`, `q`, `limit`, `offset` | `list[WaveSpeedCatalogModel]` | `limit` 1-1000, `offset >= 0` | FastAPI validation for invalid query | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/summary` | Catalog count/summary | None | Summary dict | None | None expected | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/capabilities` | List capabilities | None | Capability rows | None | None expected | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/capabilities/{capability}` | List models for capability | Query `include_excluded` | `list[WaveSpeedCatalogModel]` | Capability string | Empty list if none found | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/models/{model_id}` | Get catalog model by exact ID path | None | `WaveSpeedCatalogModel` | Model must exist | 404 unknown model | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/models/{model_id}/schema` | Get fields for catalog model | None | `list[WaveSpeedCatalogField]` | Model must exist | 404 unknown model | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/categories/{category}` | List catalog models by category | Query `include_excluded` | `list[WaveSpeedCatalogModel]` | Category string | Empty list if none found | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/cheapest-by-capability` | Return cheapest rows by capability | None | `{ "models": [...] }` | None | None expected | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/excluded` | List excluded catalog models | None | `list[WaveSpeedCatalogModel]` | None | None expected | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/cheapest` | Return cheapest curated/default mapping | None | Dict with models and capability rows | None | Missing entries represented as disabled rows | `app/routers/model_catalog.py` |
| GET | `/api/model-catalog/{node_type}` | Get curated catalog entry by node type | None | `CatalogModelSpec` | Node type must be known | 404 unknown node type | `app/routers/model_catalog.py` |
| GET | `/api/projects` | List projects | None | `list[Project]` | Local project files must validate | Project store errors mapped | `app/routers/projects.py` |
| POST | `/api/projects` | Create project | `ProjectCreate` | `Project` | Pydantic project create validation | Validation errors 422 | `app/routers/projects.py` |
| GET | `/api/projects/{project_id}` | Load project | None | `Project` | Valid ID and existing project | 400 invalid ID; 404 not found; 500 storage | `app/routers/projects.py` |
| PUT | `/api/projects/{project_id}` | Update project | `ProjectUpdate` | `Project` | Settings overrides validated; Pydantic types | 400 invalid settings/store; 404 not found | `app/routers/projects.py` |
| DELETE | `/api/projects/{project_id}` | Delete project | None | `{ "ok": true }` | Valid ID and existing project | 400 invalid ID; 404 not found | `app/routers/projects.py` |
| GET | `/api/projects/{project_id}/settings` | Get project settings | None | `ProjectSettings` | Project exists | 400/404/500 project errors | `app/routers/projects.py` |
| PUT | `/api/projects/{project_id}/settings` | Update project settings | `ProjectSettingsUpdate` | `ProjectSettings` | Forbid extra fields; cost thresholds non-negative; warn <= block; compatible overrides | 400 invalid override; 422 invalid cost shape; 404 not found | `app/routers/projects.py` |
| GET | `/api/projects/{project_id}/export` | Export portable project | Query `include_outputs`, `include_settings`, `include_run_history` | JSON export envelope | Project exists | 400/404/500 project errors | `app/routers/projects.py` |
| POST | `/api/projects/import` | Import project JSON | Multipart file or JSON body/import request | `ProjectImportResponse` | JSON valid; size <= max; valid nodes/settings/edges | 400 invalid JSON/import/validation | `app/routers/projects.py` |
| POST | `/api/projects/{project_id}/duplicate` | Duplicate project locally | Optional `ProjectDuplicateRequest` | `ProjectImportResponse` | Project exists; duplicate options valid | 400 portable error; 404 project not found | `app/routers/projects.py` |
| POST | `/api/assets/upload` | Upload local asset; optionally upload to WaveSpeed | Multipart `file`; query `upload_to_wavespeed` | `Asset` | File <= `max_upload_mb`; asset kind inferred | 413 too large; 400 WaveSpeed upload error | `app/routers/assets.py` |
| POST | `/api/runs/estimate` | Estimate run cost | `EstimateRunRequest` | `EstimateRunResponse` | Project/node if provided must exist; model resolves | 400 estimate/model error; 404 node/project | `app/routers/runs.py` |
| POST | `/api/runs/node` | Run node immediately | `RunNodeRequest` | `RunNodeResponse` | Saved node inputs resolved; prompt-source rule; model enabled; cost guard | 400 run/model/input/cost error; 404 node/project | `app/routers/runs.py` |
| GET | `/api/workflows/{project_id}/plan` | Preview workflow plan | Query `mode`, `node_id` | Plan dict | Project exists; mode/node validated by resolver | 400/404 project or plan errors | `app/routers/workflows.py` |
| POST | `/api/workflows/{project_id}/run-selected` | Execute selected node synchronously | `RunSelectedRequest` | Workflow response dict | Valid project/node/plan/cost | 400 plan/cost/run error; 404 project | `app/routers/workflows.py` |
| POST | `/api/workflows/{project_id}/run-from-node/{node_id}` | Execute downstream synchronously | None | Workflow response dict | Valid project/node/plan/cost | 400/404 errors | `app/routers/workflows.py` |
| POST | `/api/workflows/{project_id}/run-all` | Execute whole graph synchronously | None | Workflow response dict | Valid plan/cost | 400/404 errors | `app/routers/workflows.py` |
| GET | `/api/workflows/{project_id}/runs` | List project run history | None | `project.runs` | Project exists | 400/404 project errors | `app/routers/workflows.py` |
| GET | `/api/jobs` | List in-memory jobs | Query `project_id`, `status`, `limit` | `list[RunJob]` | Limit handled by run manager | Run manager errors mapped | `app/routers/jobs.py` |
| GET | `/api/jobs/{job_id}` | Get one job | None | `RunJob` | Job exists | 404 job not found; 500 manager error | `app/routers/jobs.py` |
| POST | `/api/jobs/{job_id}/cancel` | Cancel job | None | `RunJob` | Job exists and cancellable per manager | 404/400 manager errors | `app/routers/jobs.py` |
| POST | `/api/jobs/{job_id}/retry` | Retry failed/cancelled job | None | `RunJob` | Job exists and retryable per manager | 404/400 manager errors | `app/routers/jobs.py` |
| DELETE | `/api/jobs/completed` | Clear completed terminal jobs | None | Manager result dict | None | Unknown custom error behavior | `app/routers/jobs.py` |
| POST | `/api/jobs/node` | Queue single-node run | `QueueNodeRunRequest` | `RunJob` | Project/node/cost/model validation in manager | 400/404 manager/project errors | `app/routers/jobs.py` |
| POST | `/api/jobs/workflow/selected` | Queue selected workflow | `QueueWorkflowRunRequest` | `RunJob` | Project/node/plan/cost validation | 400/404 manager/project errors | `app/routers/jobs.py` |
| POST | `/api/jobs/workflow/from-node/{node_id}` | Queue downstream workflow | `QueueWorkflowRunRequest` | `RunJob` | Project/node/plan/cost validation | 400/404 manager/project errors | `app/routers/jobs.py` |
| POST | `/api/jobs/workflow/all` | Queue whole graph workflow | `QueueWorkflowRunRequest` | `RunJob` | Project/plan/cost validation | 400/404 manager/project errors | `app/routers/jobs.py` |
| GET | `/api/templates` | List templates | Query `category`, `builtin` | `list[WorkflowTemplate]` | Filter values optional | Template errors mapped | `app/routers/templates.py` |
| POST | `/api/templates` | Create user template | `WorkflowTemplateCreate` | `WorkflowTemplate` | Template payload valid | 400 template/validation errors | `app/routers/templates.py` |
| POST | `/api/templates/from-project/{project_id}` | Save project as template | `TemplateFromProjectRequest` | `WorkflowTemplate` | Project exists; template valid | 404 project; 400 template errors | `app/routers/templates.py` |
| GET | `/api/templates/{template_id}` | Get template | None | `WorkflowTemplate` | Template exists | 404 not found | `app/routers/templates.py` |
| PUT | `/api/templates/{template_id}` | Update template | `WorkflowTemplateUpdate` | `WorkflowTemplate` | Template exists and mutable | 400 builtin/validation; 404 not found | `app/routers/templates.py` |
| DELETE | `/api/templates/{template_id}` | Delete template | None | `{ "ok": true }` | Built-in templates cannot be deleted | 400 builtin; 404 not found | `app/routers/templates.py` |
| POST | `/api/templates/{template_id}/create-project` | Create project from template | `CreateProjectFromTemplateRequest` | `Project` | Template exists; project valid | Template errors mapped | `app/routers/templates.py` |
| GET | `/api/recipes` | List recipes | None | `list[WorkflowRecipe]` | None | None expected | `app/routers/recipes.py` |
| GET | `/api/recipes/{recipe_id}` | Get recipe | None | `WorkflowRecipe` | Recipe exists | 404 recipe error | `app/routers/recipes.py` |
| POST | `/api/recipes/{recipe_id}/create-project` | Create project from recipe | Optional `CreateProjectFromRecipeRequest` | `Project` | Recipe exists | 404 recipe error | `app/routers/recipes.py` |
| POST | `/api/projects/{project_id}/apply-recipe/{recipe_id}` | Apply recipe to existing project | None | `Project` | Project and recipe exist | 400 project store; 404 project/recipe | `app/routers/project_recipes.py` |
| GET | `/api/projects/{project_id}/artifacts` | List artifacts | Query `kind`, `role` | Artifact list | Project exists | 400/404 project errors | `app/routers/artifacts.py` |
| GET | `/api/projects/{project_id}/artifacts/{asset_id}` | Get artifact | None | `Asset` | Artifact exists | 404 artifact/project | `app/routers/artifacts.py` |
| GET | `/api/projects/{project_id}/artifacts/{asset_id}/lineage` | Get lineage tree | None | Lineage dict | Artifact exists | 404 artifact/project | `app/routers/artifacts.py` |
| POST | `/api/projects/{project_id}/artifacts/{asset_id}/pin` | Pin artifact | None | `Asset` | Artifact exists | 404 artifact/project | `app/routers/artifacts.py` |
| POST | `/api/projects/{project_id}/artifacts/{asset_id}/unpin` | Unpin artifact | None | `Asset` | Artifact exists | 404 artifact/project | `app/routers/artifacts.py` |
| POST | `/api/projects/{project_id}/artifacts/{asset_id}/reject` | Reject artifact | None | `Asset` | Artifact exists | 404 artifact/project | `app/routers/artifacts.py` |
| POST | `/api/projects/{project_id}/artifacts/{asset_id}/restore` | Restore rejected artifact | None | `Asset` | Artifact exists | 404 artifact/project | `app/routers/artifacts.py` |
| POST | `/api/projects/{project_id}/artifacts/{asset_id}/role` | Set artifact role | `ArtifactRoleUpdate` | `Asset` | Role enum valid; artifact exists | 404 artifact; validation 422 | `app/routers/artifacts.py` |
| POST | `/api/projects/{project_id}/artifacts/{asset_id}/rating` | Rate artifact | `ArtifactRatingUpdate` | `Asset` | Rating accepted by service | 400 artifact/rating error | `app/routers/artifacts.py` |
| POST | `/api/projects/{project_id}/artifacts/{asset_id}/branch` | Branch from artifact | `BranchArtifactRequest` | `{ node, edge }` | Compatible artifact/target | 400 artifact/branch error | `app/routers/artifacts.py` |
| POST | `/api/projects/{project_id}/nodes/{node_id}/variants` | Queue variant set | `VariantRunRequest` | `VariantSet` | Project/node valid; variant request valid | 400 variant; 404 project | `app/routers/variants.py` |
| GET | `/api/projects/{project_id}/variants` | List variant sets | None | `list[VariantSet]` | Project exists | Project errors mapped | `app/routers/variants.py` |
| GET | `/api/projects/{project_id}/variants/{variant_set_id}` | Get variant set | None | `VariantSet` | Variant exists | 404 variant/project | `app/routers/variants.py` |
| POST | `/api/projects/{project_id}/variants/{variant_set_id}/promote/{asset_id}` | Promote variant artifact | None | `VariantSet` | Asset belongs to set | 400 not part; 404 artifact/variant | `app/routers/variants.py` |
| POST | `/api/projects/{project_id}/variants/{variant_set_id}/cancel` | Cancel variant jobs | None | `VariantSet` | Variant exists | 404 variant/project; manager errors recorded | `app/routers/variants.py` |
| POST | `/api/projects/{project_id}/nodes/{node_id}/compare-models` | Queue model comparison | `ModelCompareRequest` | `ComparisonSet` | Compatible models/fields | 400 compare error; 404 project | `app/routers/comparisons.py` |
| GET | `/api/projects/{project_id}/comparisons` | List comparisons | None | `list[ComparisonSet]` | Project exists | Project errors mapped | `app/routers/comparisons.py` |
| GET | `/api/projects/{project_id}/comparisons/{comparison_id}` | Get comparison | None | `ComparisonSet` | Comparison exists | 404 comparison/project | `app/routers/comparisons.py` |
| POST | `/api/projects/{project_id}/comparisons/{comparison_id}/winner/{asset_id}` | Choose comparison winner | None | `ComparisonSet` | Asset belongs to comparison | 400 invalid winner; 404 comparison/artifact | `app/routers/comparisons.py` |
| POST | `/api/projects/{project_id}/export-package` | Create export manifest | Optional `{ asset_ids: [] }` | `ExportPackageManifest` | Assets valid if specified | 400 export package; 404 project | `app/routers/export_packages.py` |
| GET | `/api/projects/{project_id}/export-package/{package_id}` | Read export manifest | None | `ExportPackageManifest` | Package exists | 404 package/project | `app/routers/export_packages.py` |
| POST | `/api/projects/{project_id}/runs/{run_id}/rerun` | Rerun from saved run snapshot | None | `RunJob` | Run references a node | 400 missing node/manager; 404 run/project | `app/routers/run_snapshots.py` |
| POST | `/api/projects/{project_id}/runs/{run_id}/clone-node` | Clone node from run snapshot | None | `CanvasNode` | Run and source node exist | 400 project store; 404 run/source node | `app/routers/run_snapshots.py` |

## 8. Data Requirements

- **Configuration**
  - Status: Verified.
  - `app/core/config.py` loads `.env` and environment variables with Pydantic settings.
  - Key fields: `WAVESPEED_API_KEY`, `cors_origins`, `data_dir`, `upload_dir`, `project_dir`, `template_dir`, `max_upload_mb`, `max_import_json_mb`.
  - Runtime directories are created automatically.

- **Project files**
  - Status: Verified.
  - Stored under `data/projects`.
  - Shape follows `app/schemas.py` `Project`: `id`, `name`, `description`, `nodes`, `edges`, `assets`, `runs`, `variant_sets`, `comparison_sets`, `export_packages`, `settings`, timestamps.
  - Sample files exist in `data/projects/*.json`.

- **Nodes**
  - Status: Verified.
  - Shape follows `CanvasNode`: `id`, `type`, `title`, `model_id`, `estimated_base_cost_usd`, `x`, `y`, `inputs`, `output_asset_ids`, `output_urls`, `last_run`, `status`, `error_message`, timestamps.
  - Status enum: `idle`, `queued`, `running`, `success`, `error`, `skipped`.

- **Edges**
  - Status: Verified.
  - Shape follows `CanvasEdge`: `id`, `source_node_id`, `target_node_id`, `source_handle`, `target_handle`, `source_output`, `target_input`, plus aliases for backward compatibility.

- **Assets/artifacts**
  - Status: Verified.
  - Shape follows `Asset`: `id`, `kind`, `filename`, `content_type`, `local_path`, `public_url`, `wavespeed_url`, `created_at`, `metadata`, `lineage`, `view`, `versions`.
  - Asset kind enum: image, video, audio, other.
  - Artifact view state includes pinned, role, label, notes, rating, rejected, favorite.

- **Uploads**
  - Status: Verified.
  - Stored under `data/uploads`.
  - Uploaded asset metadata includes generated stored filename and size bytes.

- **Templates**
  - Status: Verified.
  - User templates are stored under `data/templates`.
  - Built-in templates are defined in `app/services/template_store.py`.

- **Model catalog**
  - Status: Verified.
  - Normalized catalog file: `app/data/wavespeed_catalog.normalized.json`.
  - Exclusion file: `app/data/model_exclusions.json`.
  - Current summary: 1009 visible catalog models, 5226 schema fields, 56 capabilities, 0 excluded models.

- **Run jobs**
  - Status: Verified.
  - `RunJob` is an in-memory model, not file-persisted.
  - Terminal jobs are copied into `project.runs`.

- **Export envelopes**
  - Status: Verified.
  - `ProjectExportEnvelope` includes schema metadata and project payload.
  - Export strips local paths and can omit outputs/settings/run history.

## 9. Non-Functional Requirements

- **Local MVP deployment**
  - Status: Verified.
  - App runs locally with FastAPI and local filesystem persistence.

- **Security/secrets**
  - Status: Verified.
  - `WAVESPEED_API_KEY` is read from environment or `.env`; code must not hardcode secrets.
  - `.env` contents must not be printed or committed.

- **Architecture boundaries**
  - Status: Verified.
  - WaveSpeed SDK usage must stay in `wavespeed_adapter.py`.
  - Model execution must stay in `node_runner.py`.
  - Workflow planning/input mapping must stay in `workflow_resolver.py`.
  - Model metadata comes from `model_catalog.py` and `registry.py`.

- **Storage limitations**
  - Status: Verified.
  - Project, template, and upload storage are local filesystem only.
  - Default upload max is 50 MB; default import JSON max is 2 MB.

- **Queue limitations**
  - Status: Verified.
  - Run Manager is local in-memory with a local worker. Jobs do not survive server restart.

- **Cost assumptions**
  - Status: Verified.
  - Cost estimates are local starting estimates, not exact billing.
  - Backend stores costs in USD. Frontend displays estimates in MYR using a UI-only conversion.

- **Frontend build**
  - Status: Verified.
  - Frontend source is React + React Flow in `frontend/`; built assets are served from `web/`.

## 10. Requirement Traceability Matrix

| Requirement ID | Requirement | Code evidence | Frontend evidence | Test evidence | Status | Gap notes |
| --- | --- | --- | --- | --- | --- | --- |
| FR-001 | Serve app locally | `app/main.py` | `web/index.html`, `web/assets/*` | Compile/build validation documented | Verified | `frontend/` is source, not directly served |
| FR-002 | Project CRUD | `app/routers/projects.py`, `project_store.py` | `frontend/src/main.jsx` project actions | `test_v4.py`, `test_v5.py`, UI smoke delete | Verified | No auth/ownership |
| FR-003 | Local project persistence | `schemas.py`, `project_store.py` | Save/load calls | `test_v3.py`, `test_v4.py`, `test_v5.py`, `test_v6.py` | Verified | No raw project schema version |
| FR-004 | Visual canvas | React Flow code in `frontend/src/main.jsx` | `WorkflowCard`, canvas controls | UI smoke drag save | Verified | No professional editor tools |
| FR-005 | Add model/utility nodes | `models.py`, `registry.py`, `utility_tools.py` | rail/context menus | UI smoke add nodes | Verified | Full live model behavior not proven |
| FR-006 | Edit node inputs | `ModelField`, `WaveSpeedCatalogField` | `NodeSettingsPopover`, `NodeField` | Field/preparer tests | Verified | Some catalog fields may need UI polish |
| FR-007 | Connect nodes | `CanvasEdge`, `workflow_resolver.py` | `onConnect`, `handleQuickConnect` | `test_v6.py`, UI smoke edge reload | Verified | Advanced routing absent |
| FR-008 | Prompt source rule | `validate_prompt_card_inputs` | connected prompt placeholders | `test_v10_utility_nodes.py` | Verified | Text-like field coverage unclear |
| FR-009 | Asset upload/select | `assets.py`, input resolvers | Assets rail/node upload | asset resolver tests, UI smoke upload | Verified | No cleanup UI |
| FR-010 | Single node execution | `runs.py`, `node_runner.py` | Run buttons/job queue | node runner tests | Verified | Live API depends on key |
| FR-011 | WaveSpeed adapter boundary | `wavespeed_adapter.py` | Not applicable | `test_v10_wavespeed_only_guard.py` | Verified | Retry behavior unknown |
| FR-012 | Workflow plan/run | `workflows.py`, `workflow_resolver.py` | Run rail/workflow controls | `test_v4.py`, `test_v6.py`, `test_v7.py` | Verified | No durable/parallel queue |
| FR-013 | Job queue | `jobs.py`, `run_manager.py` | polling/cancel/retry calls | `test_v7.py`, UI smoke queue | Verified | Jobs in memory only |
| FR-014 | Run history | `workflows.py`, `run_manager.py` | Runs rail | `test_v7.py` | Verified | Frontend filtering unknown |
| FR-015 | Output previews | `model_output_normalizer.py` | `OutputPreview` | output normalizer tests, UI smoke output actions | Verified | Remote preview coverage unknown |
| FR-016 | Branching | `artifacts.py`, `branching.py` | branch button | `test_v10_branching.py` | Verified | Full artifact UI narrower than API |
| FR-017 | Cost guard/overrides | `projects.py`, `cost_estimator.py` | settings UI calls | `test_v4.py` | Verified | Estimates only |
| FR-018 | Portability | `portable_project.py`, project routes | import/export/duplicate calls | `test_v5.py` | Verified | Local only |
| FR-019 | Templates | `templates.py`, `template_store.py` | templates rail/actions | `test_v5.py` | Verified | No remote marketplace |
| FR-020 | Recipes | `recipes.py`, `project_recipes.py` | recipe calls | `test_v10_recipes.py` | Verified | Some recipe placeholders |
| FR-021 | Catalog inspection | `model_catalog.py`, `catalog_repository.py` | model list consumes enabled models | catalog API/repository tests | Verified | Source workbook availability unknown |
| FR-022 | Generic catalog execution | `registry.py`, `node_runner.py`, `model_input_resolver.py` | model cards by catalog specs | generic runner tests | Verified | Live behavior not fully proven |
| FR-023 | Local utilities | `local_utility_runner.py`, `utility_tools.py` | utility menu/cards | `test_v10_utility_nodes.py` | Verified | Media tool dependency unknown |
| FR-024 | Artifact APIs | `artifacts.py`, `artifact_service.py` | Partial/unknown | lineage/branch tests | Verified | Full UI reachability unknown |
| FR-025 | V10 advanced APIs | variants/comparisons/export/run snapshots routers | API-first per docs | V10 tests | Verified | Full UI not implemented |
| FR-026 | Visible errors | router `HTTPException`s, validation handler | status/error state | error-path tests | Verified | UI polish unknown |
| FR-027 | Automated validation | tests and Playwright config | UI smoke tests | 109 backend tests, 7 UI tests | Verified | No screenshot regression |

## 11. Missing Requirements / Gaps

- **Verified gap:** There is no asset cleanup/storage-management workflow.
  - Evidence: README next-build list and absence of cleanup route/UI found in inspected routers.
- **Verified gap:** There is no database/auth/billing/multi-user ownership.
  - Evidence: explicitly out of scope in docs and no related routes/schemas.
- **Verified gap:** In-memory jobs are not durable across server restart.
  - Evidence: `README.md` Local Run Manager section and in-memory `run_manager.py`.
- **Verified gap:** Advanced V10 features are API-first rather than fully exposed in the UI.
  - Evidence: `README.md` V10 reachability and frontend API usage.
- **Inferred gap:** Some of the 1000+ catalog models may need live verification beyond schema-level tests.
  - Evidence: catalog scale-out plus generic runner tests; no evidence of live testing every model.
- **Inferred gap:** Some generated catalog fields may need per-field frontend polish.
  - Evidence: generic field rendering across large catalog; tests focus on core smoke paths.
- **Proposed gap:** Add screenshot regression tests for canvas/popover layout.
  - Evidence: current tests are behavioral Playwright tests, not visual regression tests.
- **Unknown:** Whether local `ffmpeg`/media tooling is always installed for local video utilities.

## 12. Questions For Product Owner

1. Should the long-term frontend contract remain React + React Flow, or should the product return to vanilla JS as older docs originally said?
2. Should advanced V10 APIs become first-class UI panels, or remain API-first developer tools?
3. Which catalog models should be treated as product-supported versus merely schema-visible?
4. Should the app continue using local JSON storage for MVP, or is a database planned soon?
5. Should job history become durable for queued/running jobs, or is in-memory behavior acceptable?
6. What exact MYR/USD conversion policy should be used if cost display becomes user-facing beyond local estimates?
7. Should asset cleanup, storage quotas, or upload management be prioritized next?
8. Should all prompt-like catalog fields be forced through Prompt Card/LLM sources, or only known `prompt`/`text` style inputs?
9. Should local utility nodes remain separate from model nodes in the UI taxonomy?
10. Should the product expose excluded catalog rows in the UI as inspect-only records?

## 13. Suggested Next Requirements.md

The following is a cleaned requirements draft that could replace the old `requirements.md` after product-owner review.

```md
# Requirements — WaveSpeed Canvas MVP

## Overview

Build a local AI canvas workflow app for composing WaveSpeed-powered media generation workflows. The app lets users create projects, add model and utility nodes, connect nodes visually, upload/select assets, run nodes or workflows, preview outputs, branch from artifacts, manage local settings, and save/reload workflow state.

## Architecture

- Backend: Python FastAPI in `app/`.
- Frontend: React + React Flow source in `frontend/`, built to static files in `web/`.
- Static serving: FastAPI serves `web/` at `/` and `data/uploads` at `/uploads`.
- Storage: local JSON/filesystem under `data/`.
- No database, auth, billing, external queue, Next.js, Tailwind, or professional editing tools in MVP.

## Core User Capabilities

1. Create, load, update, save, and delete local projects.
2. Add model nodes and local utility nodes to a React Flow canvas.
3. Drag nodes and persist `x`/`y` positions.
4. Connect node outputs to compatible inputs by dragging handles or clicking output then input.
5. Save and reload edges in project JSON.
6. Upload local image/video/audio/other assets.
7. Optionally upload assets to WaveSpeed for remote model input use.
8. Configure node inputs through schema-driven forms.
9. Keep model prompt/text inputs graph-sourced from Prompt Card, LLM, or transcript nodes.
10. Run a single node through the local Run Manager or immediate run endpoint.
11. Preview workflow plans for selected, downstream/from-node, or whole-graph modes.
12. Queue selected, downstream/from-node, or whole-graph workflow jobs.
13. View job status, progress, cancel, retry, and clear completed jobs.
14. Persist terminal run history into project JSON.
15. Preview image/video/audio/text/other outputs with Open, Copy URL, Download, and raw response details.
16. Branch from compatible outputs/artifacts into downstream nodes.
17. Export/import portable project JSON.
18. Duplicate projects locally.
19. Use built-in and user-saved templates.
20. Use built-in recipes to create or extend workflow graphs.
21. Configure project model overrides and local cost guard thresholds.
22. Inspect model catalog summary, capabilities, schemas, excluded rows, and cheapest models.
23. Use local utility nodes including Prompt Card, Style Card, Character Card, Asset Input, Asset Selector, Compare Board, Variant Batch, Reroute, Note, Group Frame, Export Package, Video Last Frame, and Stitch Videos.

## Backend Requirements

- Keep WaveSpeed SDK usage inside `app/services/wavespeed_adapter.py`.
- Keep model execution inside `app/services/node_runner.py`.
- Keep workflow planning and connected input mapping inside `app/services/workflow_resolver.py`.
- Keep model/category metadata in `app/services/model_catalog.py`, `app/services/registry.py`, and catalog data files.
- Read `WAVESPEED_API_KEY` only from environment variables or `.env`.
- Return clear FastAPI errors for invalid project IDs, missing nodes/assets, invalid imports, incompatible model overrides, missing required inputs, blocked cost guard runs, unknown models, disabled/excluded models, upload failures, and WaveSpeed errors.

## Frontend Requirements

- Use the React + React Flow app in `frontend/`.
- Build frontend assets into `web/` with `npm run build --prefix frontend`.
- Load `/api/projects`, `/api/models?enabled_only=true`, and `/api/categories` on startup.
- Auto-load the last project when available.
- Provide rail/popover menus for Project, Models, Utility, Run, Files/Templates, Assets, and Runs.
- Provide a right-click canvas menu for adding utility/model nodes.
- Show model/provider icons, model names, estimated costs in MYR, node status, previews, and run buttons.
- Show model settings in a selected-node panel; keep utility fields inline where appropriate.

## Data Requirements

- Project JSON must remain backward compatible with older local project files.
- Projects include nodes, edges, assets, runs, settings, variant sets, comparison sets, export packages, and timestamps.
- Assets include local path, public URL, optional WaveSpeed URL, metadata, lineage, view state, and versions.
- Jobs are in-memory only, but terminal run snapshots are persisted into project runs.
- Exports must strip local filesystem paths and remap IDs on import.

## Validation

Run before completing implementation work:

```powershell
python -m compileall app
npm run build --prefix frontend
$latestJs = Get-ChildItem web\assets\*.js | Sort-Object LastWriteTime -Descending | Select-Object -First 1
node --check $latestJs.FullName
python -m unittest discover -s tests -v
npm run test:e2e --prefix frontend
python -m uvicorn app.main:app --reload --port 8000
```

## Out Of Scope

- Database persistence.
- Authentication or per-user project permissions.
- Billing or real credit enforcement.
- Durable distributed job workers.
- WebSockets/SSE.
- Collaborative editing.
- Professional editing tools: layers, masks editor, brush editor, vector editor, crop studio, timeline, or Photoshop-like panels.
- Unverified model parameters.
```
