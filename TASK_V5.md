# TASK_V5.md — Workflow Portability: Project Import/Export, Project Duplication, and Reusable Templates

## Status

This task comes after `TASK_V2.md`, `TASK_V3.md`, and `TASK_V4.md`.

Assume the current project already has:

- FastAPI backend.
- Vanilla HTML/CSS/JS frontend.
- Local JSON project storage.
- Local upload storage.
- WaveSpeed execution behind `WaveSpeedAdapter`.
- Workflow planning/execution from `TASK_V2`.
- Cost-aware model catalog and expanded runnable nodes from `TASK_V3`.
- Project settings, model override UI, cost guard UI, workflow cost totals, and catalog-driven node library cleanup from `TASK_V4`.

Before coding, Codex must verify these assumptions from the current repo. If any assumption is wrong, do not rewrite the app. Report the mismatch and make the smallest compatible change.

---

## High-level goal

Build **Workflow Portability v1**.

The app should let a local single-user creator move, duplicate, reuse, and share workflows without adding a database, auth, billing, React, or production infrastructure.

The V5 goal is to add:

1. Project export as a portable JSON file.
2. Project import from a portable JSON file.
3. Project duplication.
4. Built-in workflow template gallery.
5. Save current project as a reusable local template.
6. Create new project from a template.
7. Safe validation/sanitization for imported projects and templates.
8. Frontend UI for import/export/duplicate/templates.
9. Tests and docs for portability behavior.

This task should not add more WaveSpeed models. It should make existing workflows easier to reuse.

---

## Why this is TASK V5

V2 made graph execution work.

V3 made models, media previews, and local cost estimates more useful.

V4 made project-level settings, model overrides, and cost guard controls usable.

The next useful product step is **portability**:

- Users should be able to export a workflow before experimenting.
- Users should be able to import a workflow shared by someone else.
- Users should be able to duplicate a project before modifying it.
- Users should be able to start from common templates instead of building every graph from scratch.
- Codex and future AI assistants should be able to generate valid workflow/template JSON that the app can import.

This is more useful now than React, database, auth, billing, or another large model batch.

---

## Read these files first

Read these files before making a plan:

- `FINAL_PROJECT_CONTEXT.md`
- `PROJECT_SUMMARY.md`
- `TASK_V2.md`
- `TASK_V3.md`
- `TASK_V4.md`
- `README.md`
- `requirements.md`
- `CODEX_TASKS.md`
- `AGENTS.md` if present
- `app/main.py`
- `app/schemas.py`
- `app/core/config.py`
- `app/core/storage.py`
- `app/services/project_store.py`
- `app/services/model_catalog.py`
- `app/services/registry.py`
- `app/services/cost_estimator.py`
- `app/services/node_runner.py`
- `app/services/workflow_resolver.py`
- `app/routers/projects.py`
- `app/routers/model_catalog.py`
- `app/routers/workflows.py`
- `app/routers/runs.py`
- `web/index.html`
- `web/app.js`
- `web/style.css`
- files under `tests/`

Also inspect:

- Current project JSON shape.
- Current project ID validation.
- Current default settings behavior.
- Current node/edge/asset schemas.
- Existing tests for V2/V3/V4.
- Whether `data/templates` already exists.
- Whether any import/export helpers already exist.

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
- Export secrets.
- Export absolute local machine paths in portable exports.
- Trust imported JSON without validation.
- Break existing project JSON files.
- Rewrite the whole frontend.
- Add binary ZIP asset bundling in V5 unless it is very small and optional.

Keep:

- FastAPI backend.
- Vanilla frontend.
- Local JSON storage.
- Existing endpoints working.
- Existing runnable models working.
- Existing V2/V3/V4 behavior working.
- WaveSpeed SDK usage only behind `WaveSpeedAdapter`.
- Backward compatibility with existing project JSON files.

---

## Scope decision for V5

V5 should implement **JSON portability first**.

### In scope

- Export/import project JSON.
- Duplicate projects locally.
- Built-in templates.
- User-saved templates.
- Create project from template.
- Validation/sanitization/migration of imported workflow data.
- UI controls for all of the above.

### Out of scope for V5

- ZIP export with binary assets.
- Cloud sharing links.
- Accounts.
- Public template marketplace.
- Database-backed templates.
- Collaborative templates.
- Real asset relinking wizard.
- React/React Flow conversion.

V5 exports should preserve remote URLs such as `wavespeed_url` and existing public output URLs where useful, but should strip unsafe local-only fields such as absolute `local_path` by default.

---

## Target feature set

## 1. Export project JSON

Add backend support to export a project in a portable format.

Preferred endpoint:

```text
GET /api/projects/{project_id}/export
```

Optional query parameters:

```text
include_outputs=true|false
include_settings=true|false
include_run_history=true|false
```

Recommended defaults:

```text
include_outputs=true
include_settings=true
include_run_history=false
```

The response should be a downloadable JSON response.

Suggested response media type:

```text
application/json
```

Suggested filename:

```text
wavespeed-workflow-{safe_project_name}-{project_id}.json
```

The exported JSON must include metadata:

```json
{
  "schema": "wavespeed_canvas_project_export",
  "version": 1,
  "exported_at": "2026-06-12T00:00:00Z",
  "app": "WaveSpeed Canvas MVP",
  "project": {}
}
```

Sanitization rules:

- Do not include secrets.
- Do not include `.env` values.
- Do not include `WAVESPEED_API_KEY`.
- Do not include absolute local file paths.
- Preserve `wavespeed_url` because it may be remotely reusable.
- Preserve `public_url` only if it is not a localhost-only URL, or mark it as non-portable in asset metadata.
- Optionally preserve output URLs if `include_outputs=true`.
- Optionally strip `runs` if `include_run_history=false`.
- Preserve project `settings` if `include_settings=true`.

The export should be human-readable with indentation.

---

## 2. Import project JSON

Add backend support to import a portable project JSON export.

Preferred endpoint:

```text
POST /api/projects/import
```

Accepted payload options:

1. Multipart file upload:

```text
file=@workflow.json
```

2. JSON body:

```json
{
  "import_data": {},
  "mode": "copy",
  "name": "Imported workflow"
}
```

If implementing both is too much, implement multipart file upload first.

Import behavior:

- Validate the top-level export schema.
- Accept both full export shape and raw project shape for developer convenience.
- Create a new project ID by default.
- Regenerate node IDs, edge IDs, asset IDs, and run IDs by default.
- Remap edges to the new node IDs.
- Remap node `output_asset_ids` to new asset IDs if outputs are imported.
- Keep node positions.
- Keep node inputs.
- Keep model IDs/settings only if valid against the current catalog.
- Reject disabled model overrides that would become active.
- Set unknown/invalid node types to rejected import errors, not silently accepted.
- Reset all node statuses to `idle` unless `preserve_status=true` is explicitly supported.
- Clear node `error_message` by default.
- Set project timestamps to now.
- Save the imported project to local JSON storage.

Suggested response:

```json
{
  "ok": true,
  "project": {},
  "warnings": [],
  "id_map": {
    "nodes": {},
    "edges": {},
    "assets": {}
  }
}
```

Import warnings should include:

- Asset URLs that are local-only and not portable.
- Output URLs that may be expired.
- Model IDs that were removed or replaced.
- Settings that were rejected or reset.
- Unsupported export version.

Do not call WaveSpeed during import.

---

## 3. Duplicate project

Add a simple local duplicate feature.

Preferred endpoint:

```text
POST /api/projects/{project_id}/duplicate
```

Request body:

```json
{
  "name": "Copy of My Workflow",
  "include_outputs": true,
  "include_run_history": false
}
```

Behavior:

- Load source project.
- Create a new project ID.
- Regenerate node/edge/asset IDs.
- Remap edges and node output asset references.
- Preserve node positions and inputs.
- Preserve settings.
- Optionally preserve output URLs/assets.
- Optionally strip run history.
- Save as a new project.
- Return the new project.

Frontend should add a `Duplicate Project` button.

---

## 4. Template data model

Add a reusable template model.

Suggested schema names:

```text
WorkflowTemplate
WorkflowTemplateCreate
WorkflowTemplateUpdate
TemplateNode
TemplateEdge
```

A template should be project-like but safer and lighter.

Suggested shape:

```json
{
  "id": "template_basic_image_remix",
  "name": "Basic Image Remix",
  "description": "Generate an image, then remix it.",
  "category": "image",
  "tags": ["image", "remix", "starter"],
  "version": 1,
  "builtin": true,
  "nodes": [],
  "edges": [],
  "settings": {},
  "created_at": "...",
  "updated_at": "..."
}
```

Template rules:

- Templates should not contain user secrets.
- Templates should not contain local absolute paths.
- Templates should usually not contain run history.
- Templates should usually not contain generated outputs.
- Templates may contain placeholder inputs and preset prompts.
- Templates should use only enabled/runnable model types unless intentionally marked as experimental.

Storage:

- Built-in templates can live in code, for example `app/services/template_store.py`, or in JSON files under `app/templates/`.
- User-created local templates can live under `data/templates`.

Prefer a simple implementation that is easy to inspect.

---

## 5. Built-in starter templates

Add at least these built-in templates.

### Template 1 — Basic Image Remix

Flow:

```text
Text to Image
  ↓
Image to Image
```

Nodes:

- `text_to_image`
- `image_to_image`

Use placeholder prompt text and positions.

### Template 2 — Product Cleanup

Flow:

```text
Upload Image
  ↓
Remove Background
  ↓
Upscale Image
```

Nodes:

- `upload_image`
- `remove_background`
- `upscale_image`

This should not require any sample asset.

### Template 3 — Image to Short Video

Flow:

```text
Text to Image
  ↓
Image to Video
```

Nodes:

- `text_to_image`
- `image_to_video`

Use a simple motion prompt.

### Template 4 — UGC Starter

Flow:

```text
Upload Image
  ↓
Remove Background
  ↓
Image to Image
  ↓
Image to Video

Text to Speech
```

Nodes:

- `upload_image`
- `remove_background`
- `image_to_image`
- `image_to_video`
- `text_to_speech`

`text_to_speech` can be unconnected in V5, because the app does not yet have video composition/lip sync.

### Template 5 — Voiceover Only

Flow:

```text
Text to Speech
```

Nodes:

- `text_to_speech`

---

## 6. Template API endpoints

Add a new router if clean:

```text
app/routers/templates.py
```

Register it in:

```text
app/main.py
```

Preferred endpoints:

```text
GET    /api/templates
POST   /api/templates
GET    /api/templates/{template_id}
PUT    /api/templates/{template_id}
DELETE /api/templates/{template_id}
POST   /api/templates/from-project/{project_id}
POST   /api/templates/{template_id}/create-project
```

Endpoint behavior:

### `GET /api/templates`

Return built-in and user-created templates.

Support optional filters if simple:

```text
category=image|video|audio|ugc
builtin=true|false
```

### `POST /api/templates`

Create a user template from explicit template data.

Validate nodes and edges.

### `GET /api/templates/{template_id}`

Return one template.

### `PUT /api/templates/{template_id}`

Update only user-created templates.

Do not allow modifying built-in templates through this endpoint.

### `DELETE /api/templates/{template_id}`

Delete only user-created templates.

Do not allow deleting built-in templates.

### `POST /api/templates/from-project/{project_id}`

Create a reusable user template from an existing project.

Request body:

```json
{
  "name": "My UGC Template",
  "description": "Reusable product UGC workflow",
  "category": "ugc",
  "tags": ["product", "video"],
  "include_outputs": false,
  "include_settings": true
}
```

Default behavior:

- Strip outputs.
- Strip run history.
- Reset node statuses to idle.
- Keep node positions.
- Keep node inputs.
- Keep settings if requested.

### `POST /api/templates/{template_id}/create-project`

Create a new project from a template.

Request body:

```json
{
  "name": "New workflow from template",
  "description": "Optional description"
}
```

Behavior:

- Convert template nodes/edges into a new project.
- Generate new project/node/edge IDs.
- Reset statuses to idle.
- Save the project.
- Return the new project.

---

## 7. Import/export/template service layer

Keep logic out of routers where practical.

Suggested new files:

```text
app/services/portable_project.py
app/services/template_store.py
```

`portable_project.py` responsibilities:

- Export project to safe portable dict.
- Import project from safe portable dict.
- Duplicate project with ID remapping.
- Sanitize assets.
- Strip local absolute paths.
- Regenerate IDs.
- Remap node/edge/asset references.
- Reset runtime fields.
- Validate compatibility with current schemas/catalog.
- Return warnings.

`template_store.py` responsibilities:

- Provide built-in templates.
- Load user templates from `data/templates`.
- Save user templates.
- Delete user templates.
- Create template from project.
- Create project from template.

Keep `project_store.py` as the persistence owner for projects.

---

## 8. Frontend UI

Update the vanilla UI.

### Top bar buttons

Add buttons:

```text
Export Project
Import Project
Duplicate Project
Templates
Save as Template
```

Keep the design simple.

### Export Project

Behavior:

- Calls `/api/projects/{project_id}/export`.
- Downloads the returned JSON file.
- Shows a log message.

### Import Project

Behavior:

- Opens a file picker for `.json`.
- Uploads to `/api/projects/import`.
- Shows import warnings.
- Loads the imported project.
- Refreshes project list.

### Duplicate Project

Behavior:

- Calls `/api/projects/{project_id}/duplicate`.
- Loads the duplicated project.
- Refreshes project list.

### Templates panel

Add a simple template modal/panel.

The template panel should show:

- Template name.
- Description.
- Category.
- Tags.
- Built-in/user label.
- Node count.
- Output kinds if easy.
- Create Project button.
- Delete button for user templates only.

### Save as Template

Behavior:

- Opens a simple prompt/modal for name, description, category, tags.
- Calls `/api/templates/from-project/{project_id}`.
- Refreshes template list.

### UX notes

- Show warnings returned from import.
- Do not hide validation errors.
- Do not make disabled models runnable through templates.
- Do not require WaveSpeed API key for import/export/template operations.
- Do not call WaveSpeed while importing or creating from template.

---

## 9. Validation and security rules

Imported JSON is untrusted input.

Validate:

- Maximum file size for import.
- JSON parses successfully.
- Top-level object is valid.
- Project name/description are strings within reasonable lengths.
- Node list length is reasonable.
- Edge list length is reasonable.
- Asset list length is reasonable.
- Node types exist in `NodeType`.
- Edge source/target nodes exist.
- Model IDs are registered and compatible if present.
- Project settings are valid.
- Cost guard fields are valid.
- Asset URLs are strings and not local absolute paths.

Suggested limits:

```text
max import JSON size: 2 MB
max nodes: 100
max edges: 200
max assets: 200
max runs imported: 100 only if explicitly supported
```

Safety behavior:

- Reject malformed imports with clear errors.
- Return warnings for non-fatal portability issues.
- Do not execute imported workflows automatically.
- Reset runtime status fields to `idle` by default.
- Clear errors by default.
- Do not trust imported local paths.

---

## 10. Tests

Add tests for V5 behavior.

Suggested file:

```text
tests/test_v5.py
```

Test at least:

1. Export endpoint returns valid portable export shape.
2. Export strips absolute `local_path` values.
3. Export can omit run history.
4. Import endpoint accepts a valid exported project.
5. Import creates a new project ID.
6. Import regenerates node IDs and remaps edges.
7. Import resets node statuses to `idle` by default.
8. Import rejects invalid node types.
9. Import rejects edges pointing to missing nodes.
10. Import warns about localhost asset URLs.
11. Duplicate endpoint creates a new project with remapped IDs.
12. Duplicate can omit run history.
13. Built-in templates are listed.
14. Built-in template can create a new project.
15. User template can be created from a project.
16. User template can be deleted.
17. Built-in template cannot be deleted.
18. Existing V2/V3/V4 tests still pass.

Do not require a real WaveSpeed API key for V5 tests.

---

## 11. Documentation

Update or create:

- `FINAL_PROJECT_CONTEXT.md`
- `PROJECT_SUMMARY.md`
- optionally `TASK_V5_RESULTS.md`
- optionally update `README.md`

Document:

- New import/export endpoints.
- New duplicate endpoint.
- New template endpoints.
- Export file shape.
- Import safety behavior.
- Template behavior.
- What is not portable in V5.
- Manual test path.
- Remaining non-goals.

If `AGENTS.md` exists, update it only if needed.

---

## Implementation checkpoints

## Checkpoint 0 — Inspect and plan only

Codex must first inspect the repo and report:

1. Whether V2 appears implemented.
2. Whether V3 appears implemented.
3. Whether V4 appears implemented.
4. Current project schema shape.
5. Current project store behavior.
6. Current frontend project controls.
7. Proposed files to change.
8. Any risks around import/export/template validation.

Do not edit files during Checkpoint 0.

---

## Checkpoint 1 — Portable project service

Implement the backend service helpers.

Expected files may include:

- `app/schemas.py`
- `app/services/portable_project.py`
- `app/services/project_store.py`
- tests

Deliverables:

- Export helper.
- Import helper.
- Duplicate helper.
- ID remapping.
- Sanitization.
- Warnings.

Validation:

```bat
python -m compileall app
python -m unittest discover -s tests -v
```

---

## Checkpoint 2 — Project import/export/duplicate API

Add project endpoints.

Expected files may include:

- `app/routers/projects.py`
- `app/main.py` only if needed
- tests

Add:

```text
GET  /api/projects/{project_id}/export
POST /api/projects/import
POST /api/projects/{project_id}/duplicate
```

Validation:

```bat
python -m compileall app
python -m unittest discover -s tests -v
```

Manual API smoke tests:

```bat
curl http://localhost:8000/api/projects
```

Use browser `/docs` for multipart import if easier.

---

## Checkpoint 3 — Template backend

Implement template model/store/router.

Expected files may include:

- `app/schemas.py`
- `app/services/template_store.py`
- `app/routers/templates.py`
- `app/main.py`
- tests

Add:

```text
GET    /api/templates
POST   /api/templates
GET    /api/templates/{template_id}
PUT    /api/templates/{template_id}
DELETE /api/templates/{template_id}
POST   /api/templates/from-project/{project_id}
POST   /api/templates/{template_id}/create-project
```

Validation:

```bat
python -m compileall app
python -m unittest discover -s tests -v
```

---

## Checkpoint 4 — Frontend import/export/duplicate/templates UI

Update the vanilla frontend.

Expected files may include:

- `web/index.html`
- `web/app.js`
- `web/style.css`

Add UI for:

- Export Project.
- Import Project.
- Duplicate Project.
- Templates panel.
- Save as Template.
- Create Project from Template.
- Delete user template.
- Import warnings display.

Validation:

```bat
node --check web/app.js
python -m uvicorn app.main:app --reload --port 8000
```

Manual browser validation:

1. Open app.
2. Create project.
3. Export project.
4. Import exported JSON.
5. Confirm imported project is new and loads.
6. Duplicate project.
7. Open Templates panel.
8. Create project from built-in template.
9. Save current project as template.
10. Delete user template.

---

## Checkpoint 5 — Docs and final validation

Update docs and run all validations.

Validation commands:

```bat
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8000
```

Manual full test path:

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
5. Add a Text to Image node and an Image to Image node.
6. Connect/branch them.
7. Save the project.
8. Export the project.
9. Import the exported project.
10. Confirm imported project has new IDs but same workflow shape.
11. Duplicate the project.
12. Confirm duplicate has new IDs but same workflow shape.
13. Open Templates.
14. Create project from Basic Image Remix template.
15. Save a custom template from the current project.
16. Delete the custom template.
17. Confirm built-in templates cannot be deleted.
18. Confirm existing node run, workflow run, cost guard, and project settings still work.
19. Open:

```text
http://localhost:8000/docs
http://localhost:8000/api/templates
http://localhost:8000/api/projects
```

20. Confirm no secrets are present in exported JSON.

---

## Definition of done

TASK V5 is done when:

- Existing V2 workflow execution still works.
- Existing V3 catalog/runnable models still work.
- Existing V4 project settings/cost guard UI still works.
- Project export endpoint works.
- Exported JSON is portable and sanitized.
- Project import endpoint works.
- Imported projects get new IDs and remapped edges.
- Project duplicate endpoint works.
- Built-in templates are available from the API.
- User templates can be created from projects.
- Projects can be created from templates.
- Frontend supports export, import, duplicate, templates, and save-as-template.
- Import warnings are visible to the user.
- Tests cover import/export/duplicate/templates.
- Validation commands pass.
- Documentation is updated.
- No secrets are committed.

---

## Suggested Codex prompt

Use this prompt after placing `TASK_V5.md` in the repo root:

```text
Read TASK_V5.md and implement it.

Start with Checkpoint 0 only:
1. Inspect the repo.
2. Verify current V2, V3, and V4 status from code.
3. Identify current project schema and storage behavior.
4. Identify current frontend project controls.
5. Propose a short implementation plan for V5.

Do not edit files until I approve the plan.
```

After approving the plan, continue with:

```text
Proceed with Checkpoint 1 only.

Make the smallest compatible backend service changes for portable project export/import/duplicate helpers.
Run the validation commands listed in TASK_V5.md.
Report changed files, test results, and any risk.
```

Then continue checkpoint by checkpoint.

---

## Notes for future tasks

After TASK V5 is stable, good next tasks could be:

1. `TASK_V6 — Visual Connector Editor Without React`
2. `TASK_V6 — Local Job Queue, Run Progress, and Cancellation`
3. `TASK_V6 — Start-End Video Node After Official Parameter Verification`
4. `TASK_V6 — Asset Cleanup and Storage Management`

Do not jump to database/auth/billing/React until the local single-user product is stable and pleasant to use.
