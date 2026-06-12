# WaveSpeed Canvas MVP — FastAPI Codex Build Pack

This is a **Codex-ready scaffold**, not a finished production app.

Goal: build a lightweight node-canvas creative workflow app using Python FastAPI and WaveSpeed. It should feel like a simple "Weave-lite" workflow builder: generate, branch, remix, animate, and export AI media without professional editing tools.

## What is included

```text
app/
  main.py                    FastAPI app entrypoint
  schemas.py                 Pydantic API/data models
  core/config.py             .env settings
  core/storage.py            JSON file persistence helpers
  routers/health.py          Health endpoint
  routers/models.py          Node category + model registry endpoints
  routers/projects.py        Project CRUD using local JSON files
  routers/assets.py          Local upload + optional WaveSpeed upload
  routers/runs.py            Generic WaveSpeed node runner
  services/registry.py       Node categories and starter model specs
  services/wavespeed_adapter.py
web/
  index.html                 Minimal canvas UI scaffold
  style.css                  Basic layout styling
  app.js                     Minimal front-end logic
requirements.txt             Python dependencies
requirements.md              Product + technical requirements for Codex
CODEX_TASKS.md               Step-by-step implementation tasks
.env.example                 Environment template
```

## Windows CMD setup

Open **Command Prompt** in the project folder.

```bat
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

Set your key in `.env`:

```env
WAVESPEED_API_KEY=your_real_wavespeed_key_here
```

Run the app:

```bat
python -m uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

## Fast test commands

Health check:

```bat
curl http://localhost:8000/api/health
```

List model registry:

```bat
curl http://localhost:8000/api/models
```

Run text-to-image from CMD:

```bat
curl -X POST http://localhost:8000/api/runs/node ^
  -H "Content-Type: application/json" ^
  -d "{\"model_id\":\"wavespeed-ai/z-image/turbo\",\"node_type\":\"text_to_image\",\"inputs\":{\"prompt\":\"A clean futuristic product poster, studio lighting\",\"size\":\"1024*1024\",\"seed\":-1,\"output_format\":\"jpeg\"},\"save_to_project\":false}"
```

## Current MVP behavior

The scaffold already supports:

1. Creating local projects.
2. Adding model nodes to a simple canvas.
3. Editing a selected node's JSON inputs.
4. Running enabled WaveSpeed model nodes.
5. Uploading files locally.
6. Optionally uploading local files to WaveSpeed so image/video models can consume them.
7. Saving project JSON under `data/projects`.

## Important implementation notes

Localhost file URLs are usually not reachable by remote AI APIs. For image-to-image or image-to-video nodes, use the upload endpoint with `upload_to_wavespeed=true`, then copy the returned `wavespeed_url` into the node input field.

The only enabled model IDs in the initial registry are:

```text
wavespeed-ai/z-image/turbo
wavespeed-ai/z-image-turbo/image-to-image
```

Other categories are represented as disabled placeholders. Check the WaveSpeed model page and replace the placeholder IDs before enabling those models.

## What Codex should build next

Use `requirements.md` as the product/technical spec and `CODEX_TASKS.md` as the implementation sequence.

Main next steps:

1. Replace the basic DOM canvas with React Flow or another node graph library.
2. Add real node linking and automatic input mapping.
3. Add model-specific forms instead of raw JSON.
4. Add SQLite/Postgres persistence.
5. Add run history and asset previews.
6. Add image-to-video, start-end-video, text-to-speech, and lip-sync models after verifying model IDs.
7. Add auth and billing controls before public launch.

## Out of scope for MVP

Do not build professional edit tools yet:

- No Photoshop-style layer system.
- No vector editor.
- No timeline editor.
- No brush masking UI.
- No advanced inpainting canvas.
- No keyframe editor.
- No multi-user real-time collaboration.

Build the AI workflow first.
