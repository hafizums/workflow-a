# WaveSpeed Canvas MVP - Current Project Summary

## Project Purpose

This project is a FastAPI plus vanilla HTML/CSS/JavaScript MVP for a lightweight AI canvas workflow app inspired by Figma Weave-style node workflows.

The app is intentionally not a professional editor. It focuses on simple AI media workflow building:

- Create and load projects.
- Add nodes to a canvas.
- Upload image assets.
- Generate images with WaveSpeed.
- Remix images with WaveSpeed image-to-image.
- Branch from generated image outputs.
- Drag nodes around the canvas.
- Save node data, output data, edges, and node positions to local JSON.

## Current Architecture

### Backend

The backend is Python FastAPI.

Important files:

- `app/main.py` - FastAPI app entrypoint, CORS setup, routers, static file serving.
- `app/schemas.py` - Pydantic models for projects, nodes, edges, assets, model specs, and run requests.
- `app/core/config.py` - Environment/config settings, including `WAVESPEED_API_KEY`.
- `app/core/storage.py` - Async JSON read/write helpers.
- `app/routers/health.py` - Health endpoint.
- `app/routers/models.py` - Model registry and category endpoints.
- `app/routers/projects.py` - Local JSON project CRUD endpoints.
- `app/routers/assets.py` - Asset upload endpoint.
- `app/routers/runs.py` - Generic node run endpoint.
- `app/services/project_store.py` - Project JSON persistence service.
- `app/services/registry.py` - WaveSpeed model registry and planned category registry.
- `app/services/wavespeed_adapter.py` - Single wrapper around the WaveSpeed SDK.
- `app/services/node_runner.py` - Execution logic for supported WaveSpeed image nodes.

### Frontend

The frontend is deliberately simple vanilla web code.

Important files:

- `web/index.html` - Static page shell.
- `web/style.css` - Canvas, node card, asset list, and layout styles.
- `web/app.js` - Project loading, node rendering, drag behavior, branching, upload, run, save, and preview logic.

No React, Next.js, Tailwind, database, or canvas graph library is currently used.

## Storage

The MVP uses local filesystem storage:

- Projects are saved as JSON under `data/projects`.
- Uploaded files are stored under `data/uploads`.
- Generated WaveSpeed output URLs are stored as project assets and also on node data.

There is no database yet.

## Environment and Secrets

WaveSpeed credentials are read from environment variables only.

Expected setting:

```env
WAVESPEED_API_KEY=your_real_key_here
```

The app does not hardcode API keys.

`.env`, virtualenv files, uploaded files, and generated project JSON are ignored by `.gitignore`.

## Current API Endpoints

### Health

```text
GET /api/health
```

Returns app health and whether a WaveSpeed API key is configured.

### Registry

```text
GET /api/categories
GET /api/models
GET /api/models?enabled_only=true
```

`/api/models` currently returns 20 model entries:

- 2 enabled executable models.
- 18 disabled planned models.

### Projects

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
PUT    /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

Projects include:

- `id`
- `name`
- `description`
- `nodes`
- `edges`
- `assets`
- timestamps

### Assets

```text
POST /api/assets/upload?upload_to_wavespeed=true|false
```

Uploads a local file and optionally uploads it to WaveSpeed.

For image-to-image runs, localhost URLs are not treated as remotely reachable. The backend can upload a selected local asset to WaveSpeed and then use the returned WaveSpeed URL.

### Runs

```text
POST /api/runs/node
```

Runs a single supported WaveSpeed node.

The backend updates the target node status and stores:

- `output_asset_ids`
- `output_urls`
- `last_run`
- `error_message`

## Enabled WaveSpeed Execution

Only these model types are currently enabled for real execution:

### Text to Image

Node type:

```text
text_to_image
```

WaveSpeed model:

```text
wavespeed-ai/z-image/turbo
```

Supported fields:

- `prompt`
- `size`
- `seed`
- `output_format`

### Image to Image / Remix

Node type:

```text
image_to_image
```

WaveSpeed model:

```text
wavespeed-ai/z-image-turbo/image-to-image
```

Supported fields:

- `prompt`
- `image`
- `size`
- `strength`
- `seed`
- `output_format`

The `image` input can be:

- A public URL.
- A WaveSpeed uploaded URL.
- A project asset reference.
- A local path that the backend can upload to WaveSpeed.

## Planned Disabled Registry Categories

The registry is prepared for future expansion, but these are disabled until real WaveSpeed model IDs and request fields are verified.

### Image

- `reference_to_image`
- `upscale_image`
- `remove_background`
- `remove_object`

### Video

- `image_to_video`
- `text_to_video`
- `start_end_to_video`
- `reference_to_video`
- `video_extend`
- `video_effect`

### Audio

- `text_to_speech`
- `text_to_audio`
- `speech_to_text`

### Avatar

- `talking_avatar`
- `lip_sync`
- `portrait_transfer`

### 3D

- `image_to_3d`
- `text_to_3d`

## Current Frontend Behavior

The app currently supports:

- Creating a new project.
- Loading saved projects from a top dropdown.
- Editing project name and description.
- Adding an upload node.
- Adding enabled WaveSpeed image nodes.
- Viewing disabled planned nodes in the node library.
- Editing node inputs directly in node cards.
- Uploading image assets.
- Running text-to-image nodes.
- Running image-to-image/remix nodes.
- Showing generated image previews.
- Dragging node cards with a move handle.
- Saving node `x` and `y` positions.
- Loading saved node positions.
- Creating visual connection lines between branched nodes.
- Branching from a generated image output into a remix node.

## Branching Behavior

Generated image nodes show a `Branch from output` action after they have an output URL.

Branching creates:

- A new `image_to_image` remix node.
- A simple edge from source node to remix node.
- A prefilled remix image input using the source output URL.

The edge is saved in the existing project `edges` array.

## Error Handling State

The backend returns useful errors for:

- Missing project.
- Invalid project ID.
- Missing node in project.
- Missing prompt.
- Missing remix source image.
- Placeholder or unsupported model IDs.
- Missing WaveSpeed SDK.
- Missing WaveSpeed API key.
- WaveSpeed upload/run failures.
- WaveSpeed responses without output URLs.

Frontend node cards show node-level error messages when runs fail.

## How To Run

From the project root:

```powershell
.\.venv\Scripts\activate
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

## Useful Validation Commands

Compile backend:

```powershell
python -m compileall app
```

Check frontend JavaScript syntax:

```powershell
node --check web/app.js
```

Check model registry:

```text
http://localhost:8000/api/models
```

Check category registry:

```text
http://localhost:8000/api/categories
```

## Manual Test Path

1. Start the server.
2. Open `http://localhost:8000`.
3. Create a project.
4. Add `Z Image Turbo`.
5. Enter a prompt.
6. Run the node.
7. Confirm an output image preview appears.
8. Click `Branch from output`.
9. Confirm a remix node appears with a connection line.
10. Drag both nodes.
11. Save the project.
12. Refresh the page.
13. Load the project.
14. Confirm node positions and connection lines remain.
15. Upload an image asset.
16. Add or use a remix node.
17. Select the uploaded image as source.
18. Run remix.
19. Confirm the remix output preview appears.

## Non-Goals Still In Effect

The MVP should not add professional editing tools yet.

Do not add:

- Photoshop-style layers.
- Brush or mask editors.
- Vector editing.
- Crop studio.
- Timeline editing.
- Keyframes.
- React Flow.
- React or Next.js.
- Tailwind.
- Database persistence.
- Auth, billing, or multi-user collaboration.

## Next Reasonable Steps

Good follow-up phases would be:

1. Improve project import/export.
2. Add run history UI.
3. Add asset copy/download buttons.
4. Add form controls for select-style fields such as output format and image size.
5. Verify and enable one additional WaveSpeed model category at a time.
6. Add tests for registry shape, node runner validation, project persistence, and asset upload.
7. Add SQLite only after the JSON MVP workflow is stable.

## Current Status

The project is now a working MVP scaffold with real WaveSpeed execution for two image workflows and a visual vanilla canvas experience.

The architecture is intentionally small and extendable:

- New verified models should be added through `app/services/registry.py`.
- Model execution should remain behind `WaveSpeedAdapter`.
- Node-specific input preparation should stay in `app/services/node_runner.py`.
- The frontend should remain vanilla until there is a clear reason to introduce a graph library.
