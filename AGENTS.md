# AGENTS

## Project Rules

- Keep the backend on Python FastAPI.
- The current frontend is a React + React Flow app in `frontend/`, built to static assets in `web/` and served by FastAPI.
- Do not add Next.js, Tailwind, a database, auth, billing, background workers, or professional editing tools yet.
- Do not hardcode secrets.
- Keep `WAVESPEED_API_KEY` in environment variables or `.env` only.
- Do not print or commit `.env` contents.

## Architecture Rules

- HTTP routers should stay thin: parse requests, map responses, and translate application errors to FastAPI errors.
- Application orchestration belongs in `app/application/use_cases/`.
- DTOs shared by use cases and executors belong in `app/application/dto/`.
- Domain validation and guardrail rules belong in `app/domain/policies/`.
- Ports belong in `app/ports/`; local JSON, local queue, storage, and external gateway adapters belong in `app/infrastructure/`.
- WaveSpeed SDK usage must stay behind `app/services/wavespeed_adapter.py`.
- `app/services/wavespeed_adapter.py`, `app/services/node_runner.py`, `app/services/run_manager.py`, `app/services/project_store.py`, `app/services/template_store.py`, `app/services/recipe_store.py`, and `app/services/workflow_resolver.py` remain compatibility facades while orchestration moves into use cases.
- Model execution semantics must stay behind `app/services/node_runner.py`; executor strategies may delegate to it.
- Model/category metadata should come from `app/services/model_catalog.py` and `app/services/registry.py`.
- Workflow planning and input mapping should stay in `app/services/workflow_resolver.py`.
- Project storage must remain backward compatible with older local JSON files.

## Run Commands

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Open:

- `http://localhost:8000`
- `http://localhost:8000/docs`

## Validation Commands

```powershell
python -m compileall app
npm run build --prefix frontend
$latestJs = Get-ChildItem web\assets\*.js | Sort-Object LastWriteTime -Descending | Select-Object -First 1
node --check $latestJs.FullName
python -m unittest discover -s tests -v
npm run test:e2e --prefix frontend
```

## Manual Smoke Path

1. Create or load a project.
2. Add a catalog node.
3. Open Project Settings.
4. Save cost guard/model override settings.
5. Preview a workflow plan.
6. Run a node or workflow only when cost guard allows it.
7. Save, refresh, and reload the project.


## Requirements Maintenance

When asked to update requirements:
- Do not invent product behavior.
- Derive requirements from source docs, code, API routes, schemas, frontend behavior, and tests.
- Label requirements as Verified, Inferred, Proposed, or Unknown.
- Keep functional requirement IDs stable.
- Include acceptance criteria for every requirement.
- Include traceability from requirement to code and tests.
- Do not overwrite requirements.md without first creating or reviewing a generated draft.
