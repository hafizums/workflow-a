# Requirements - WaveSpeed Canvas MVP

Last reviewed: 2026-06-13

This file is the active product requirements document for the current repository. It is based on verified implementation evidence from `requirements.generated.md`, the FastAPI app, React/React Flow frontend source, tests, local data shapes, and project docs.

## 1. Product Overview

WaveSpeed Canvas MVP is a local AI media workflow canvas. Users create projects, add model and utility nodes, connect node outputs to downstream inputs, upload/select assets, run WaveSpeed-backed models or local utilities, inspect generated outputs, and save/reload workflow state.

The product is intentionally a lightweight workflow builder, not a professional media editor.

## 2. Product Goal

Enable a local user to compose and run AI media generation workflows around WaveSpeed models using a visual graph of prompts, assets, model nodes, and utility nodes.

## 3. Target Users

- Local developers and operators testing WaveSpeed model workflows.
- Creative technologists building prompt-to-media and media-to-media workflows.
- Codex-assisted product/engineering contributors maintaining and extending the MVP.

## 4. Current Scope

- Python FastAPI backend in `app/`.
- React + React Flow frontend source in `frontend/`.
- Static frontend build output in `web/`, served by FastAPI.
- Local JSON project storage under `data/projects`.
- Local upload storage under `data/uploads`.
- Local template storage under `data/templates`.
- WaveSpeed model execution through a dedicated adapter.
- Catalog-driven model registry with curated and generic WaveSpeed model specs.
- Local utility nodes for prompt, asset, graph, comparison, export, and simple video utility workflows.
- In-memory local job queue with persisted terminal run history.
- Project import/export/duplicate/templates/recipes.
- API-first advanced workflow surfaces for artifacts, variants, comparisons, export packages, and run snapshots.

## 5. Out Of Scope

- Database persistence.
- Authentication or per-user authorization.
- Billing, credit purchasing, or real billing enforcement.
- Durable distributed workers such as Redis, Celery, or external queues.
- WebSockets/SSE progress streaming.
- Collaborative multi-user editing.
- Next.js or Tailwind.
- Professional editing tools such as layers, brush editor, mask editor, vector editor, crop studio, or timeline.
- Invented model parameters for models without verified schema metadata.

## 6. Architecture Requirements

- WaveSpeed SDK access must stay behind `app/services/wavespeed_adapter.py`.
- Model execution must stay in `app/services/node_runner.py`.
- Workflow planning and connected input mapping must stay in `app/services/workflow_resolver.py`.
- Model/category metadata must come from `app/services/model_catalog.py`, `app/services/registry.py`, `app/services/utility_tools.py`, and catalog data files.
- Project storage must remain backward compatible with older local JSON project files.
- The WaveSpeed API key must come only from `WAVESPEED_API_KEY` in environment variables or `.env`.

## 7. Functional Requirements

### FR-001: Serve The Local Application
- Status: Verified
- Priority: P0
- Requirement: The app must serve FastAPI API routes, uploaded files, and the built frontend from a single local FastAPI process.
- Source evidence:
  - `app/main.py`: FastAPI app creation, router registration, lifespan run-manager startup, `/uploads` mount, `/` static mount.
  - `frontend/package.json`: `build` writes static assets to `../web`.
- Acceptance criteria:
  - Given dependencies are installed, when `python -m uvicorn app.main:app --reload --port 8000` runs, then `http://localhost:8000/docs` shows FastAPI docs.
  - Given the frontend has been built, when `http://localhost:8000` is opened, then FastAPI serves `web/index.html` and `web/assets/*`.
  - Given uploaded assets exist, when their `/uploads/...` URL is requested, then FastAPI serves the file from the configured upload directory.

### FR-002: Create, Load, Save, And Delete Projects
- Status: Verified
- Priority: P0
- Requirement: Users must be able to create, list, load, update/save, and delete local projects.
- Source evidence:
  - `app/routers/projects.py`: `list_projects`, `create_project`, `get_project`, `update_project`, `delete_project`.
  - `app/services/project_store.py`: local project persistence.
  - `frontend/src/main.jsx`: project load/save/delete UI calls.
  - `tests/test_v4.py`, `tests/test_v5.py`, `frontend/tests/ui-smoke.spec.js`.
- Acceptance criteria:
  - Given the API is running, when `POST /api/projects` receives a valid `ProjectCreate`, then it returns and persists a `Project`.
  - Given saved projects exist, when `GET /api/projects` is called, then it returns the available projects.
  - Given a valid project ID, when `GET /api/projects/{project_id}` is called, then it returns that project.
  - Given a valid project update, when `PUT /api/projects/{project_id}` is called, then changed project fields are persisted.
  - Given a valid project ID, when `DELETE /api/projects/{project_id}` is called, then the API returns `{ "ok": true }`.

### FR-003: Persist Project Data Locally
- Status: Verified
- Priority: P0
- Requirement: Project data must persist as backward-compatible local JSON.
- Source evidence:
  - `app/schemas.py`: `Project`, `CanvasNode`, `CanvasEdge`, `Asset`, `ProjectSettings`.
  - `data/projects/*.json`: sample persisted project files.
  - `tests/test_v3.py`, `tests/test_v4.py`, `tests/test_v5.py`, `tests/test_v6.py`.
- Acceptance criteria:
  - Given a project with nodes, edges, assets, runs, settings, and positions, when the project is saved, then the project can be loaded later with those fields intact.
  - Given an older supported project shape, when it is loaded, then defaults such as project settings are applied without breaking the file.
  - Given edge aliases from older shapes, when a workflow is planned, then edges normalize into the current edge model.

### FR-004: Render And Edit The Canvas
- Status: Verified
- Priority: P1
- Requirement: The frontend must render project nodes on a React Flow canvas and allow node selection and movement.
- Source evidence:
  - `frontend/src/main.jsx`: `App`, React Flow configuration, `WorkflowCard`, node state mapping.
  - `frontend/src/styles.css`: canvas and node styling.
  - `frontend/tests/ui-smoke.spec.js`: drag-position persistence smoke test.
- Acceptance criteria:
  - Given a project with nodes, when the UI loads, then each node renders as a card on the canvas.
  - Given a node has `x` and `y`, when the canvas renders, then the card appears at the saved position.
  - Given a user drags a node by its move handle and saves the project, when the save payload is sent, then the changed `x` or `y` value is included.

### FR-005: Add Model And Utility Nodes
- Status: Verified
- Priority: P1
- Requirement: Users must be able to add enabled model nodes and local utility nodes from UI menus.
- Source evidence:
  - `app/routers/models.py`: `/api/models`, `/api/categories`, `/api/tools`.
  - `app/services/registry.py`: model registry.
  - `app/services/utility_tools.py`: utility tools.
  - `frontend/src/main.jsx`: rail menus and context menu node creation.
  - `frontend/tests/ui-smoke.spec.js`: add model and utility nodes.
- Acceptance criteria:
  - Given `/api/models?enabled_only=true` returns enabled specs, when the user adds a model from the model menu, then a matching node is added to the canvas.
  - Given utility tools exist, when the user adds a utility from the utility menu, then a utility node is added to the canvas.
  - Given a model or utility node is added, when the project is saved, then the node is included in project JSON.

### FR-006: Edit Node Inputs With Schema-Driven Controls
- Status: Verified
- Priority: P1
- Requirement: Node inputs must be edited through UI controls derived from model or utility field metadata.
- Source evidence:
  - `app/schemas.py`: `ModelField`, `WaveSpeedCatalogField`.
  - `frontend/src/main.jsx`: `NodeSettingsPopover`, `NodeField`, `WorkflowCard`.
  - `tests/test_node_runner_preparers.py`, `tests/test_model_input_resolver.py`.
- Acceptance criteria:
  - Given a node has field metadata, when it is selected, then the UI shows corresponding controls.
  - Given a field value changes, when the project is saved, then the value is persisted under `node.inputs`.
  - Given a prompt-like saved model field is required, when the UI displays it, then it is represented as a connected input rather than a freeform model prompt field.

### FR-007: Connect Nodes With Edges
- Status: Verified
- Priority: P1
- Requirement: Users must be able to connect node outputs to compatible node inputs and persist those edges.
- Source evidence:
  - `app/schemas.py`: `CanvasEdge`.
  - `app/services/workflow_resolver.py`: graph and edge resolution.
  - `frontend/src/main.jsx`: `onConnect`, `handleQuickConnect`, handle rendering.
  - `tests/test_v6.py`, `frontend/tests/ui-smoke.spec.js`.
- Acceptance criteria:
  - Given two compatible nodes, when the user drags from an output handle to an input handle, then an edge is created.
  - Given two compatible nodes, when the user clicks an output handle and then a compatible input handle, then an edge is created.
  - Given a Prompt Card output connected to a Text to Image prompt input, when the project is saved, then the saved edge includes `target_input: "prompt"`.
  - Given a saved edge, when the project reloads, then the edge renders on the canvas.
  - Given a self-loop, exact duplicate, missing node reference, obvious cycle, or known incompatible media connection, when planning or connecting is attempted, then the app blocks or reports the issue.

### FR-008: Enforce Prompt Source Rules
- Status: Verified
- Priority: P1
- Requirement: Saved model prompt/text inputs must come from a connected Prompt Card, LLM node, or transcript-style source rather than hidden freeform model-card text.
- Source evidence:
  - `app/services/workflow_resolver.py`: `validate_prompt_card_inputs`.
  - `frontend/src/main.jsx`: connected prompt placeholders.
  - `tests/test_v10_utility_nodes.py`.
- Acceptance criteria:
  - Given a saved model node requires a prompt/text input, when no valid source node is connected, then workflow planning or saved-node execution returns a clear error.
  - Given a Prompt Card or LLM text output is connected to a model prompt input, when inputs are resolved, then the downstream model receives the upstream text.
  - Given an LLM prompt source has not run yet, when a downstream model needs its output, then the resolver reports that the source must run first.

### FR-009: Upload And Use Assets
- Status: Verified
- Priority: P1
- Requirement: Users must be able to upload local assets, optionally upload them to WaveSpeed, and use them in nodes.
- Source evidence:
  - `app/routers/assets.py`: `upload_asset`, `infer_asset_kind`.
  - `app/services/model_input_resolver.py`, `app/services/node_runner.py`.
  - `frontend/src/main.jsx`: asset upload and node-local upload.
  - `tests/test_asset_resolution.py`, `tests/test_model_input_resolver.py`, `frontend/tests/ui-smoke.spec.js`.
- Acceptance criteria:
  - Given a local file under the configured upload size limit, when uploaded, then the API stores it and returns an `Asset`.
  - Given an uploaded asset, when its content type or suffix indicates image, video, or audio, then the asset kind is inferred accordingly.
  - Given `upload_to_wavespeed=true`, when WaveSpeed upload succeeds, then the asset contains `wavespeed_url`.
  - Given a remote WaveSpeed model requires local media, when resolving inputs, then local files are uploaded or localhost URLs are rejected with a clear error.

### FR-010: Run A Single Node
- Status: Verified
- Priority: P0
- Requirement: The backend must run a single saved or direct node request using the resolved model or local utility.
- Source evidence:
  - `app/routers/runs.py`: `/api/runs/node`.
  - `app/services/node_runner.py`: WaveSpeed model execution.
  - `app/services/local_utility_runner.py`: runnable local utilities.
  - `tests/test_v3.py`, `tests/test_node_runner_preparers.py`, `tests/test_generic_wavespeed_runner.py`, `tests/test_v10_utility_nodes.py`.
- Acceptance criteria:
  - Given a runnable model node with valid resolved inputs, when `/api/runs/node` is called, then the backend resolves the effective model, checks cost guard, calls WaveSpeed through the adapter, and returns output URLs/assets.
  - Given `save_to_project=true` and a saved node, when a run succeeds, then node status, output URLs, output asset IDs, and `last_run` are updated.
  - Given a runnable local utility node is run from a saved project, when it succeeds, then local output assets are created without a WaveSpeed model call.
  - Given a model is unknown, disabled, excluded, missing required inputs, or blocked by cost guard, when run is requested, then the API returns a clear error and marks the saved node error where applicable.

### FR-011: Isolate WaveSpeed Integration
- Status: Verified
- Priority: P0
- Requirement: All WaveSpeed SDK calls must go through the WaveSpeed adapter.
- Source evidence:
  - `app/services/wavespeed_adapter.py`.
  - `app/services/node_runner.py`.
  - `tests/test_v10_wavespeed_only_guard.py`.
- Acceptance criteria:
  - Given code outside the adapter, when imports are inspected, then no non-WaveSpeed AI clients are used.
  - Given a WaveSpeed model run is requested, when execution reaches the external API boundary, then the call goes through `WaveSpeedAdapter`.
  - Given WaveSpeed credentials are missing or invalid, when an adapter call needs credentials, then the error is returned through the API without hardcoding secrets.

### FR-012: Plan And Execute Workflows
- Status: Verified
- Priority: P1
- Requirement: Users must be able to preview and run selected-node, downstream/from-node, and whole-graph workflows.
- Source evidence:
  - `app/routers/workflows.py`.
  - `app/services/workflow_resolver.py`.
  - `tests/test_v4.py`, `tests/test_v6.py`, `tests/test_v7.py`.
  - `frontend/src/main.jsx`: workflow plan and run actions.
- Acceptance criteria:
  - Given a project graph, when `/api/workflows/{project_id}/plan` is called, then the response includes planned nodes, warnings, errors, estimated total cost, and cost guard status.
  - Given a valid selected-node request, when run-selected is executed, then only the selected runnable node is run.
  - Given a valid from-node request, when run-from-node is executed, then downstream runnable nodes are run in dependency order.
  - Given a valid whole graph, when run-all is executed, then runnable graph nodes are run in dependency order.
  - Given cycle, missing input, missing edge node reference, or cost guard block, when planning/running is requested, then the API returns a clear error before unsafe execution.

### FR-013: Queue Jobs And Track Progress
- Status: Verified
- Priority: P1
- Requirement: Node and workflow runs must be queueable through a local in-memory Run Manager.
- Source evidence:
  - `app/routers/jobs.py`.
  - `app/services/run_manager.py`.
  - `app/schemas.py`: `RunJob`.
  - `tests/test_v7.py`, `frontend/tests/ui-smoke.spec.js`.
- Acceptance criteria:
  - Given a saved project node, when `/api/jobs/node` is called, then a `RunJob` is returned.
  - Given a workflow queue request, when `/api/jobs/workflow/selected`, `/from-node/{node_id}`, or `/all` is called, then a workflow `RunJob` is returned.
  - Given a queued job, when cancelled, then it becomes cancelled.
  - Given a running workflow job with cancellation requested, when the workflow reaches a step boundary, then it stops according to current best-effort behavior.
  - Given a failed or cancelled job, when retried, then a new job ID is created.
  - Given terminal jobs exist, when completed jobs are cleared, then only clearable terminal jobs are removed from the in-memory job list.

### FR-014: Persist Terminal Run History
- Status: Verified
- Priority: P2
- Requirement: Terminal run/job results must be copied into project run history.
- Source evidence:
  - `app/services/run_manager.py`.
  - `app/routers/workflows.py`: `/api/workflows/{project_id}/runs`.
  - `tests/test_v7.py`.
- Acceptance criteria:
  - Given a queued node or workflow job reaches a terminal state, when the project is saved, then a run snapshot is inserted into `project.runs`.
  - Given run history grows, when new terminal runs are written, then history is capped to the latest 100 entries.
  - Given the server restarts, when the project is reloaded, then persisted terminal run history remains available even though in-memory jobs are gone.

### FR-015: Preview Outputs And Output Metadata
- Status: Verified
- Priority: P1
- Requirement: Users must be able to inspect node outputs and output metadata in the UI.
- Source evidence:
  - `frontend/src/main.jsx`: `OutputPreview`, `OutputItem`, `PreviewMedia`.
  - `app/services/model_output_normalizer.py`.
  - `tests/test_model_output_normalizer.py`, `frontend/tests/ui-smoke.spec.js`.
- Acceptance criteria:
  - Given a node has image, video, audio, text, or other output data, when the node card renders, then an appropriate preview or link is shown where possible.
  - Given an output URL exists, when the node card renders, then Open, Copy URL, and Download actions are available where applicable.
  - Given raw model output exists, when the user expands raw response details, then the raw output is visible.

### FR-016: Branch From Outputs And Artifacts
- Status: Verified
- Priority: P2
- Requirement: Users and API clients must be able to create downstream workflow nodes from compatible outputs/artifacts.
- Source evidence:
  - `frontend/src/main.jsx`: branch action on output cards.
  - `app/routers/artifacts.py`: `/branch`.
  - `app/services/branching.py`.
  - `tests/test_v10_branching.py`.
- Acceptance criteria:
  - Given a compatible image output in the UI, when the user clicks Branch, then a downstream node and edge are created.
  - Given an artifact and compatible branch request, when `/api/projects/{project_id}/artifacts/{asset_id}/branch` is called, then the API returns a new node and edge.
  - Given an incompatible artifact/target pair, when branching is requested, then the API returns a clear 400 error.

### FR-017: Configure Cost Guard And Model Overrides
- Status: Verified
- Priority: P1
- Requirement: Project settings must support compatible model overrides and local cost guard thresholds.
- Source evidence:
  - `app/routers/projects.py`: settings routes.
  - `app/schemas.py`: `ProjectSettings`, `CostGuardSettings`, `ProjectSettingsUpdate`.
  - `app/services/project_validation.py`, `app/services/cost_estimator.py`.
  - `tests/test_v4.py`.
- Acceptance criteria:
  - Given valid settings, when `PUT /api/projects/{project_id}/settings` is called, then settings persist.
  - Given invalid cost thresholds, when settings are updated, then validation rejects the update.
  - Given an incompatible model override, when settings are updated, then validation rejects the update.
  - Given a single-node or workflow estimate exceeds a blocking threshold, when run/queue is requested, then execution is blocked before model execution.
  - Given backend settings are stored, then cost values remain USD even if the frontend displays estimates in MYR.

### FR-018: Export, Import, And Duplicate Projects
- Status: Verified
- Priority: P1
- Requirement: Users must be able to export portable project JSON, import project JSON, and duplicate projects.
- Source evidence:
  - `app/routers/projects.py`: export/import/duplicate routes.
  - `app/services/portable_project.py`.
  - `tests/test_v5.py`.
  - `frontend/src/main.jsx`: export/import/duplicate calls.
- Acceptance criteria:
  - Given a project, when exported, then the response is a portable JSON envelope.
  - Given export options omit outputs or run history, when exported, then omitted data is not included.
  - Given local filesystem paths exist on assets, when exported, then local paths are stripped.
  - Given valid import JSON, when imported, then new project/node/edge/asset IDs are created and runtime state is reset according to options.
  - Given invalid node types or edges pointing to missing nodes, when imported, then the API rejects the import.
  - Given a project is duplicated, when duplication succeeds, then the response contains a new project with remapped IDs.

### FR-019: Manage Workflow Templates
- Status: Verified
- Priority: P2
- Requirement: Users must be able to list, create, update, delete, save from project, and create projects from workflow templates.
- Source evidence:
  - `app/routers/templates.py`.
  - `app/services/template_store.py`.
  - `tests/test_v5.py`.
  - `frontend/src/main.jsx`: template calls.
- Acceptance criteria:
  - Given templates exist, when `GET /api/templates` is called, then templates are returned.
  - Given a valid user template request, when `POST /api/templates` is called, then a user template is created.
  - Given a project, when `POST /api/templates/from-project/{project_id}` is called, then a reusable template is created from that project.
  - Given a template, when `POST /api/templates/{template_id}/create-project` is called, then a new project is created from it.
  - Given a built-in template, when deletion is requested, then the API rejects deletion.

### FR-020: Manage Workflow Recipes
- Status: Verified
- Priority: P2
- Requirement: Users must be able to list recipes, create projects from recipes, and apply recipes to existing projects.
- Source evidence:
  - `app/routers/recipes.py`.
  - `app/routers/project_recipes.py`.
  - `app/services/recipe_store.py`.
  - `tests/test_v10_recipes.py`.
  - `frontend/src/main.jsx`: recipe calls.
- Acceptance criteria:
  - Given recipes exist, when `GET /api/recipes` is called, then recipe definitions are returned.
  - Given a valid recipe ID, when `POST /api/recipes/{recipe_id}/create-project` is called, then a new project graph is created.
  - Given a valid project and recipe, when `POST /api/projects/{project_id}/apply-recipe/{recipe_id}` is called, then the project is updated with recipe graph parts.
  - Given an unknown recipe, when it is requested, then the API returns 404.

### FR-021: Inspect Model Catalog
- Status: Verified
- Priority: P1
- Requirement: API clients must be able to inspect WaveSpeed catalog metadata, capabilities, schemas, cheapest models, and excluded rows.
- Source evidence:
  - `app/routers/model_catalog.py`.
  - `app/services/catalog_repository.py`.
  - `app/data/wavespeed_catalog.normalized.json`.
  - `tests/test_model_catalog_api.py`, `tests/test_catalog_repository.py`.
- Acceptance criteria:
  - Given catalog data exists, when `/api/model-catalog/summary` is called, then counts and categories are returned.
  - Given filters are supplied to `/api/model-catalog`, then results are filtered by category, capability, query, limit, and offset.
  - Given an exact model ID exists, when `/api/model-catalog/models/{model_id}` is called, then the catalog model is returned.
  - Given an exact model ID exists, when `/api/model-catalog/models/{model_id}/schema` is called, then field schema is returned.
  - Given excluded rows exist, when `/api/model-catalog/excluded` is called, then excluded rows are returned.

### FR-022: Execute Generic Catalog Models
- Status: Verified
- Priority: P1
- Requirement: Enabled catalog models must be executable as generic WaveSpeed nodes using exact catalog model IDs and schema-prepared inputs.
- Source evidence:
  - `app/services/registry.py`.
  - `app/services/node_runner.py`.
  - `app/services/model_input_resolver.py`.
  - `tests/test_generic_wavespeed_runner.py`, `tests/test_registry_catalog_scaleout.py`, `tests/test_model_registry_contract.py`.
- Acceptance criteria:
  - Given an enabled generic catalog node, when it runs, then the exact `model_id` is sent to WaveSpeed.
  - Given catalog field schemas include media/list fields, when inputs are prepared, then values are coerced and asset references are resolved according to field metadata.
  - Given a catalog model is excluded or unknown, when execution is requested, then execution is blocked with a clear error.

### FR-023: Run Local Utility Nodes
- Status: Verified
- Priority: P2
- Requirement: Local utility nodes must support graph organization and local operations without WaveSpeed model cost unless explicitly runnable.
- Source evidence:
  - `app/services/utility_tools.py`.
  - `app/services/local_utility_runner.py`.
  - `tests/test_v10_utility_nodes.py`.
- Acceptance criteria:
  - Given non-runnable utility nodes such as Prompt Card, Asset Input, Note, or Reroute, when workflow planning occurs, then they provide graph data or organization and are not treated as WaveSpeed model runs.
  - Given `video_last_frame` has a valid video input, when it runs, then a local image asset is created.
  - Given `stitch_video` has at least two video inputs, when it runs, then a local stitched MP4 asset is created.
  - Given explicit stitch order is set, when `stitch_video` runs, then that order is honored.

### FR-024: Manage Artifacts
- Status: Verified
- Priority: P2
- Requirement: API clients must be able to inspect and update artifact metadata, lineage, role, pin/reject state, rating, and branching.
- Source evidence:
  - `app/routers/artifacts.py`.
  - `app/services/artifact_service.py`.
  - `tests/test_v10_artifact_lineage.py`, `tests/test_v10_branching.py`.
- Acceptance criteria:
  - Given a project artifact, when listed or fetched by ID, then artifact data is returned.
  - Given an artifact, when lineage is requested, then upstream lineage data is returned.
  - Given an artifact, when pin, unpin, reject, restore, role, or rating endpoints are called, then the artifact view state is updated and saved.
  - Given a compatible branch request, when artifact branch is called, then a new node and edge are returned.

### FR-025: Provide API-First Advanced Workflow Tools
- Status: Verified
- Priority: P3
- Requirement: The backend must expose API-first tools for variants, model comparisons, export packages, and run snapshots.
- Source evidence:
  - `app/routers/variants.py`.
  - `app/routers/comparisons.py`.
  - `app/routers/export_packages.py`.
  - `app/routers/run_snapshots.py`.
  - `tests/test_v10_variants.py`, `tests/test_v10_compare.py`, `tests/test_v10_export_package.py`.
- Acceptance criteria:
  - Given a valid node and variant request, when variants are created, then variant jobs and a `VariantSet` are created.
  - Given compatible models and a comparison request, when comparison is created, then a `ComparisonSet` is created and a winner can be selected from its artifacts.
  - Given selected assets, when an export package is created, then an `ExportPackageManifest` is stored and retrievable.
  - Given a run snapshot that references a node, when rerun is requested, then a new job is queued.
  - Given a run snapshot that references a node, when clone-node is requested, then a new canvas node is created from the run source node.

### FR-026: Return And Display Clear Errors
- Status: Verified
- Priority: P1
- Requirement: Backend errors and frontend status messages must be clear enough for users to correct invalid workflows.
- Source evidence:
  - `app/main.py`: request validation handler.
  - Router-level `HTTPException` handling across `app/routers/*`.
  - `frontend/src/main.jsx`: API wrapper, status text, node error display.
  - Error-path tests in `tests/test_v3.py`, `tests/test_v4.py`, `tests/test_v6.py`, `tests/test_v7.py`.
- Acceptance criteria:
  - Given invalid request validation, when FastAPI rejects the payload, then the response includes `detail: "Invalid request"` and validation errors.
  - Given invalid project ID, missing project, missing node, invalid import, invalid settings, missing required inputs, cost guard block, or model resolution failure, when requested, then the API returns an appropriate 400 or 404 with actionable detail.
  - Given a saved node run fails, when the project is saved, then node status and `error_message` reflect the failure.
  - Given the frontend receives an API error, when possible, then the visible status or node error shows the backend message.

### FR-027: Validate With Automated Tests
- Status: Verified
- Priority: P1
- Requirement: The project must maintain backend and browser smoke coverage for MVP workflows.
- Source evidence:
  - `tests/`.
  - `frontend/tests/ui-smoke.spec.js`.
  - `frontend/playwright.config.js`.
  - `AGENTS.md`.
- Acceptance criteria:
  - Given backend changes, when `python -m compileall app` and `python -m unittest discover -s tests -v` are run, then they pass before the change is considered complete.
  - Given frontend changes, when `npm run build --prefix frontend`, built JS syntax check, and `npm run test:e2e --prefix frontend` are run, then they pass before the change is considered complete.
  - Given UI smoke tests run, then they cover project loading, node creation, local asset upload, node dragging, manual edge creation/reload persistence, workflow queueing, output actions, and project deletion.

## 8. API Requirements

| Area | Methods and routes | Purpose | Source |
| --- | --- | --- | --- |
| Health | `GET /health` | Report basic app health. | `app/routers/health.py` |
| Registry | `GET /api/categories`, `GET /api/models`, `GET /api/tools` | Return categories, enabled/all model specs, and utility tools. | `app/routers/models.py` |
| Model catalog | `GET /api/model-catalog`, `/summary`, `/capabilities`, `/capabilities/{capability}`, `/models/{model_id}`, `/models/{model_id}/schema`, `/categories/{category}`, `/cheapest-by-capability`, `/excluded`, `/cheapest`, `/{node_type}` | Inspect catalog models, schemas, capabilities, cheapest rows, exclusions, and curated node-type defaults. | `app/routers/model_catalog.py` |
| Projects | `GET /api/projects`, `POST /api/projects`, `GET /api/projects/{project_id}`, `PUT /api/projects/{project_id}`, `DELETE /api/projects/{project_id}` | Project CRUD. | `app/routers/projects.py` |
| Project settings | `GET /api/projects/{project_id}/settings`, `PUT /api/projects/{project_id}/settings` | Get/update model overrides and cost guard. | `app/routers/projects.py` |
| Portability | `GET /api/projects/{project_id}/export`, `POST /api/projects/import`, `POST /api/projects/{project_id}/duplicate` | Export/import/duplicate portable projects. | `app/routers/projects.py` |
| Assets | `POST /api/assets/upload` | Upload local files and optionally upload to WaveSpeed. | `app/routers/assets.py` |
| Immediate runs | `POST /api/runs/estimate`, `POST /api/runs/node` | Estimate and run a node immediately. | `app/routers/runs.py` |
| Workflows | `GET /api/workflows/{project_id}/plan`, `POST /api/workflows/{project_id}/run-selected`, `POST /api/workflows/{project_id}/run-from-node/{node_id}`, `POST /api/workflows/{project_id}/run-all`, `GET /api/workflows/{project_id}/runs` | Plan and synchronously execute workflows; list run history. | `app/routers/workflows.py` |
| Jobs | `GET /api/jobs`, `GET /api/jobs/{job_id}`, `POST /api/jobs/{job_id}/cancel`, `POST /api/jobs/{job_id}/retry`, `DELETE /api/jobs/completed`, `POST /api/jobs/node`, `POST /api/jobs/workflow/selected`, `POST /api/jobs/workflow/from-node/{node_id}`, `POST /api/jobs/workflow/all` | Queue, inspect, cancel, retry, and clear local jobs. | `app/routers/jobs.py` |
| Templates | `GET /api/templates`, `POST /api/templates`, `POST /api/templates/from-project/{project_id}`, `GET /api/templates/{template_id}`, `PUT /api/templates/{template_id}`, `DELETE /api/templates/{template_id}`, `POST /api/templates/{template_id}/create-project` | Manage workflow templates and create projects from templates. | `app/routers/templates.py` |
| Recipes | `GET /api/recipes`, `GET /api/recipes/{recipe_id}`, `POST /api/recipes/{recipe_id}/create-project`, `POST /api/projects/{project_id}/apply-recipe/{recipe_id}` | List/apply recipes and create projects from recipes. | `app/routers/recipes.py`, `app/routers/project_recipes.py` |
| Artifacts | `GET /api/projects/{project_id}/artifacts`, `GET /api/projects/{project_id}/artifacts/{asset_id}`, `GET /api/projects/{project_id}/artifacts/{asset_id}/lineage`, `POST` pin/unpin/reject/restore/role/rating/branch subroutes | Inspect and update artifact metadata and branch artifacts. | `app/routers/artifacts.py` |
| Variants | `POST /api/projects/{project_id}/nodes/{node_id}/variants`, `GET /api/projects/{project_id}/variants`, `GET /api/projects/{project_id}/variants/{variant_set_id}`, `POST /api/projects/{project_id}/variants/{variant_set_id}/promote/{asset_id}`, `POST /api/projects/{project_id}/variants/{variant_set_id}/cancel` | API-first variant batch workflow. | `app/routers/variants.py` |
| Comparisons | `POST /api/projects/{project_id}/nodes/{node_id}/compare-models`, `GET /api/projects/{project_id}/comparisons`, `GET /api/projects/{project_id}/comparisons/{comparison_id}`, `POST /api/projects/{project_id}/comparisons/{comparison_id}/winner/{asset_id}` | API-first model comparison workflow. | `app/routers/comparisons.py` |
| Export packages | `POST /api/projects/{project_id}/export-package`, `GET /api/projects/{project_id}/export-package/{package_id}` | Create/read artifact export package manifests. | `app/routers/export_packages.py` |
| Run snapshots | `POST /api/projects/{project_id}/runs/{run_id}/rerun`, `POST /api/projects/{project_id}/runs/{run_id}/clone-node` | Rerun or clone from persisted run snapshots. | `app/routers/run_snapshots.py` |

## 9. Data Requirements

### 9.1 Configuration
- `app/core/config.py` must load settings from environment variables and `.env`.
- Required secret handling: `WAVESPEED_API_KEY` must not be hardcoded.
- Runtime directories must be created automatically.
- Default upload limit is `max_upload_mb`.
- Default import JSON limit is `max_import_json_mb`.

### 9.2 Project
Project data must follow `app/schemas.py` `Project`:

- `id`
- `name`
- `description`
- `nodes`
- `edges`
- `assets`
- `runs`
- `variant_sets`
- `comparison_sets`
- `export_packages`
- `settings`
- `created_at`
- `updated_at`

### 9.3 Node
Canvas nodes must include:

- `id`
- `type`
- `title`
- `model_id`
- `estimated_base_cost_usd`
- `x`
- `y`
- `inputs`
- `output_asset_ids`
- `output_urls`
- `last_run`
- `status`
- `error_message`
- timestamps

Supported status values: `idle`, `queued`, `running`, `success`, `error`, `skipped`.

### 9.4 Edge
Canvas edges must include source/target node and handle/input information and support backward-compatible aliases.

### 9.5 Asset
Assets must include:

- `id`
- `kind`
- `filename`
- `content_type`
- `local_path`
- `public_url`
- `wavespeed_url`
- `metadata`
- `lineage`
- `view`
- `versions`
- `created_at`

Supported asset kinds: `image`, `video`, `audio`, `other`.

### 9.6 Job
Run jobs are in-memory `RunJob` objects. Terminal results must be persisted into `project.runs`.

### 9.7 Catalog
Catalog data is stored in `app/data/wavespeed_catalog.normalized.json` and exclusion metadata in `app/data/model_exclusions.json`.

## 10. Non-Functional Requirements

- The application must run locally without a database.
- API and UI must preserve local MVP behavior.
- Secrets must not be committed, hardcoded, or printed.
- Cost estimates are approximate and not billing records.
- Backend cost and guard values must remain USD.
- Frontend may display cost estimates in MYR, but must not change backend cost units.
- In-memory jobs are allowed to disappear on server restart.
- Terminal run history must remain in project JSON.
- Upload and import size limits must be enforced.

## 11. Validation Commands

Run these before completing implementation work:

```powershell
python -m compileall app
npm run build --prefix frontend
$latestJs = Get-ChildItem web\assets\*.js | Sort-Object LastWriteTime -Descending | Select-Object -First 1
node --check $latestJs.FullName
python -m unittest discover -s tests -v
npm run test:e2e --prefix frontend
python -m uvicorn app.main:app --reload --port 8000
```

Manual smoke path:

1. Open `http://localhost:8000`.
2. Create or load a project.
3. Add Prompt Card and Text to Image nodes.
4. Connect Prompt Card output to the model prompt input.
5. Upload or select a local asset.
6. Save, refresh, and reload.
7. Preview a workflow plan.
8. Queue a node or workflow run only when cost guard allows it.
9. Confirm output preview, Open/Copy URL/Download actions, and run history.

## 12. Requirement Traceability Matrix

| Requirement | Summary | Backend evidence | Frontend evidence | Test evidence |
| --- | --- | --- | --- | --- |
| FR-001 | Serve local app | `app/main.py` | `web/index.html`, `web/assets/*`, `frontend/package.json` | Build/compile validation |
| FR-002 | Project CRUD | `app/routers/projects.py`, `app/services/project_store.py` | `frontend/src/main.jsx` | `tests/test_v4.py`, `tests/test_v5.py`, `frontend/tests/ui-smoke.spec.js` |
| FR-003 | Local project persistence | `app/schemas.py`, `app/services/project_store.py` | save/load UI | `tests/test_v3.py`, `tests/test_v4.py`, `tests/test_v5.py`, `tests/test_v6.py` |
| FR-004 | Canvas edit | project node schema | `frontend/src/main.jsx`, `frontend/src/styles.css` | `frontend/tests/ui-smoke.spec.js` |
| FR-005 | Add nodes | `app/routers/models.py`, `app/services/registry.py`, `app/services/utility_tools.py` | model/utility menus | `frontend/tests/ui-smoke.spec.js`, `tests/test_registry_catalog_scaleout.py` |
| FR-006 | Node input controls | `app/schemas.py`, model field schemas | `NodeSettingsPopover`, `NodeField` | `tests/test_node_runner_preparers.py`, `tests/test_model_input_resolver.py` |
| FR-007 | Edges | `CanvasEdge`, `workflow_resolver.py` | `onConnect`, `handleQuickConnect` | `tests/test_v6.py`, `frontend/tests/ui-smoke.spec.js` |
| FR-008 | Prompt source rule | `workflow_resolver.py` | prompt placeholders | `tests/test_v10_utility_nodes.py` |
| FR-009 | Assets | `app/routers/assets.py`, input resolvers | asset rail/upload controls | `tests/test_asset_resolution.py`, `tests/test_model_input_resolver.py`, UI smoke |
| FR-010 | Single-node run | `app/routers/runs.py`, `node_runner.py`, `local_utility_runner.py` | run buttons | `tests/test_v3.py`, `tests/test_node_runner_preparers.py`, `tests/test_generic_wavespeed_runner.py` |
| FR-011 | WaveSpeed adapter | `wavespeed_adapter.py`, `node_runner.py` | not applicable | `tests/test_v10_wavespeed_only_guard.py` |
| FR-012 | Workflow plan/run | `workflows.py`, `workflow_resolver.py` | workflow/run controls | `tests/test_v4.py`, `tests/test_v6.py`, `tests/test_v7.py` |
| FR-013 | Job queue | `jobs.py`, `run_manager.py`, `RunJob` | job polling/cancel/retry calls | `tests/test_v7.py`, UI smoke queue test |
| FR-014 | Run history | `run_manager.py`, `workflows.py` | runs panel | `tests/test_v7.py` |
| FR-015 | Output previews | `model_output_normalizer.py` | `OutputPreview`, `PreviewMedia` | `tests/test_model_output_normalizer.py`, UI smoke |
| FR-016 | Branching | `artifacts.py`, `branching.py` | branch button | `tests/test_v10_branching.py` |
| FR-017 | Cost guard/overrides | `projects.py`, `project_validation.py`, `cost_estimator.py` | settings UI | `tests/test_v4.py` |
| FR-018 | Portability | `projects.py`, `portable_project.py` | import/export/duplicate controls | `tests/test_v5.py` |
| FR-019 | Templates | `templates.py`, `template_store.py` | template controls | `tests/test_v5.py` |
| FR-020 | Recipes | `recipes.py`, `project_recipes.py`, `recipe_store.py` | recipe controls | `tests/test_v10_recipes.py` |
| FR-021 | Catalog inspection | `model_catalog.py`, `catalog_repository.py`, catalog data files | model menu consumes enabled models | `tests/test_model_catalog_api.py`, `tests/test_catalog_repository.py` |
| FR-022 | Generic catalog execution | `registry.py`, `node_runner.py`, `model_input_resolver.py` | catalog model cards | `tests/test_generic_wavespeed_runner.py`, `tests/test_registry_catalog_scaleout.py`, `tests/test_model_registry_contract.py` |
| FR-023 | Local utility nodes | `utility_tools.py`, `local_utility_runner.py` | utility menu/cards | `tests/test_v10_utility_nodes.py` |
| FR-024 | Artifacts | `artifacts.py`, `artifact_service.py` | partial UI reachability | `tests/test_v10_artifact_lineage.py`, `tests/test_v10_branching.py` |
| FR-025 | Advanced API tools | `variants.py`, `comparisons.py`, `export_packages.py`, `run_snapshots.py` | API-first; limited UI | `tests/test_v10_variants.py`, `tests/test_v10_compare.py`, `tests/test_v10_export_package.py` |
| FR-026 | Error handling | `app/main.py`, router `HTTPException`s | API wrapper/status/errors | `tests/test_v3.py`, `tests/test_v4.py`, `tests/test_v6.py`, `tests/test_v7.py` |
| FR-027 | Automated validation | test suite and Playwright config | UI smoke suite | `tests/`, `frontend/tests/ui-smoke.spec.js` |

## 13. Questions / Open Decisions

1. Should the long-term frontend contract remain React + React Flow, or should the project return to vanilla JS despite the current implementation?
2. Should advanced V10 APIs for variants, comparisons, export packages, artifact management, and run snapshots become full UI panels?
3. Which catalog models should be product-supported after live verification, versus schema-visible only?
4. Should local JSON remain the required MVP persistence layer, or should a database be introduced in a later milestone?
5. Should queued/running jobs become durable across server restarts?
6. What policy should control MYR/USD conversion if cost display becomes user-facing beyond local estimates?
7. Should asset cleanup, storage quotas, or upload management be prioritized next?
8. Should all text-like catalog fields use the prompt-source rule, or only known prompt/text inputs?
9. Should excluded catalog rows be visible in the frontend as inspect-only records?
