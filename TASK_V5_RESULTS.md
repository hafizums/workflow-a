# TASK_V5 Results

## Summary

TASK_V5 added Workflow Portability v1: portable project export/import, local project duplication, reusable workflow templates, a built-in starter template gallery, save-current-project-as-template, and vanilla frontend controls for those flows.

## Backend Changes

- Added `app/services/portable_project.py` for export/import/duplicate helpers, ID remapping, runtime reset, local path stripping, localhost URL warnings, and import limits.
- Added `app/services/template_store.py` for built-in templates and user template JSON storage under `data/templates`.
- Added `app/services/project_validation.py` so project settings/model override validation is shared by CRUD, import, and templates.
- Added `app/routers/templates.py` and registered it in `app/main.py`.
- Extended `app/schemas.py` with import/duplicate/template request and response models.
- Extended `app/core/config.py` with `template_dir` and `max_import_json_mb`.
- Extended `app/routers/projects.py` with:
  - `GET /api/projects/{project_id}/export`
  - `POST /api/projects/import`
  - `POST /api/projects/{project_id}/duplicate`

## Frontend Changes

- Added topbar controls:
  - Export Project
  - Import Project
  - Duplicate Project
  - Templates
  - Save as Template
- Added a simple templates panel with built-in/user labels, category/tags, node count, create-project, and delete-user-template actions.
- Added import warnings and duplicate/import result logging.
- Kept the frontend vanilla HTML/CSS/JS.

## Built-In Templates

- Basic Image Remix
- Product Cleanup
- Image to Short Video
- UGC Starter
- Voiceover Only

## Portability Rules

- Exports use schema `wavespeed_canvas_project_export` version `1`.
- Exports strip `local_path`.
- Localhost `public_url` values are removed and recorded as non-portable asset metadata.
- Import accepts full export envelopes or raw project-shaped JSON.
- Import creates a new project ID and remaps node, edge, and asset IDs.
- Import resets node status to `idle` and clears node errors.
- Import validates node types, edge references, settings, and model overrides.
- Import does not call WaveSpeed.
- Templates strip outputs/run history by default and do not call WaveSpeed.

## Validation Run

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
```

Result: all passed, including 34 unit tests.

Localhost smoke checks:

- `http://localhost:8000/` returned 200 and included V5 controls.
- `http://localhost:8000/docs` returned 200.
- `http://localhost:8000/api/templates` returned 200 and included built-in templates.

The in-app browser automation backend reported `iab` unavailable in this session, so visual testing used HTTP smoke checks instead.

## Manual Test Path

1. Start the server:

   ```powershell
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. Open `http://localhost:8000`.
3. Create a project.
4. Add a Text to Image node and save.
5. Click Export Project and confirm a JSON file downloads.
6. Click Import Project and choose the exported JSON.
7. Confirm the imported project appears as a new project and loads.
8. Click Duplicate Project and confirm the duplicate loads.
9. Click Templates.
10. Create a project from Basic Image Remix.
11. Save the current project as a template.
12. Reopen Templates and delete the user template.
13. Confirm built-in templates cannot be deleted through the API.
14. Confirm existing project settings, cost guard, single-node run, and workflow run flows still work.
