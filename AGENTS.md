# AGENTS

## Project Rules

- Keep the backend on Python FastAPI.
- Keep the frontend vanilla HTML/CSS/JS.
- Do not add React, React Flow, Next.js, Tailwind, a database, auth, billing, background workers, or professional editing tools yet.
- Do not hardcode secrets.
- Keep `WAVESPEED_API_KEY` in environment variables or `.env` only.
- Do not print or commit `.env` contents.

## Architecture Rules

- WaveSpeed SDK usage must stay behind `app/services/wavespeed_adapter.py`.
- Model execution must stay in `app/services/node_runner.py`.
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
node --check web/app.js
python -m unittest discover -s tests -v
```

## Manual Smoke Path

1. Create or load a project.
2. Add a catalog node.
3. Open Project Settings.
4. Save cost guard/model override settings.
5. Preview a workflow plan.
6. Run a node or workflow only when cost guard allows it.
7. Save, refresh, and reload the project.
