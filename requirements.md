# Requirements — WaveSpeed Canvas MVP

## 1. Product summary

Build a web app that works like a simple AI canvas workflow builder. The user can create nodes, connect outputs to future nodes, run WaveSpeed models, view outputs, branch from outputs, and save workflows.

The product should feel inspired by node-based creative tools, but it must stay simple. It is not a professional editor.

## 2. MVP name

Working name:

```text
WaveSpeed Canvas MVP
```

Alternative names:

```text
Weave-lite
Prompt Canvas
AI Media Canvas
```

## 3. Target user

Primary users:

- Indie builders creating AI media apps.
- Marketers creating ad images and short video assets.
- UGC creators creating product visuals.
- Developers testing WaveSpeed model workflows.

## 4. Main user workflow

Basic image workflow:

```text
Prompt
  ↓
Generate Image
  ↓
Remix Image
  ↓
Upscale / Enhance
  ↓
Export
```

Basic video workflow:

```text
Image
  ↓
Animate Image
  ↓
Extend / Transition
  ↓
Export Video
```

UGC workflow:

```text
Product Image
  ↓
Remove Background
  ↓
Generate Lifestyle Scene
  ↓
Animate Image
  ↓
Generate Voice
  ↓
Lip Sync / Avatar
```

Storyboard workflow:

```text
Scene Prompt
  ↓
Generate Start Frame
  ↓
Generate End Frame
  ↓
Start-End Video
  ↓
Stitch Clips
```

## 5. Core MVP features

### 5.1 Projects

A user can:

- Create a project.
- Rename a project.
- Save a project.
- Reopen a project.
- Delete a project.

Project data includes:

- Project ID.
- Name.
- Description.
- Nodes.
- Edges.
- Assets.
- Created timestamp.
- Updated timestamp.

MVP storage:

```text
Local JSON files under data/projects
```

Later storage:

```text
SQLite for local/dev
PostgreSQL for production
Object storage for assets
```

### 5.2 Canvas

Canvas must support:

- Add node from node library.
- Select node.
- Move node.
- Connect node output to another node input.
- Save node positions.
- Show node status: idle, running, success, error.
- Show output thumbnail or output link.

MVP scaffold can use a simple DOM canvas.

Production direction:

```text
React + React Flow
```

### 5.3 Node library

The left sidebar must show categories:

- Upload Image.
- Text to Image.
- Image to Image / Remix.
- Reference to Image.
- Upscale Image.
- Remove Background.
- Image to Video.
- Start-End Video.
- Text to Video.
- Generate Voice.
- Lip Sync / Avatar.

Each node type must define:

- Node type ID.
- Display name.
- Description.
- Input fields.
- Output type.
- Default model ID.
- Whether enabled for MVP.

### 5.4 Inspector

When a node is selected, inspector must show:

- Node title.
- Model ID.
- Input fields.
- Run button.
- Last output.
- Error message.

MVP may use raw JSON input editor.

Codex should replace raw JSON with model-specific forms.

### 5.5 Asset system

An asset can be:

- Image.
- Video.
- Audio.
- Other file.

Asset fields:

- Asset ID.
- Kind.
- Original filename.
- Content type.
- Local path.
- Public local URL.
- WaveSpeed uploaded URL.
- Created timestamp.
- Metadata.

Important rule:

Localhost URLs are not normally reachable by a remote inference API. For any WaveSpeed model that needs an input image/video/audio, upload the file to WaveSpeed first and use the returned WaveSpeed URL.

### 5.6 Model runner

Backend must expose a generic runner:

```text
POST /api/runs/node
```

Request shape:

```json
{
  "project_id": "project_abc",
  "node_id": "node_abc",
  "node_type": "text_to_image",
  "model_id": "wavespeed-ai/z-image/turbo",
  "inputs": {
    "prompt": "A product poster",
    "size": "1024*1024",
    "seed": -1,
    "output_format": "jpeg"
  },
  "save_to_project": true
}
```

Response shape:

```json
{
  "ok": true,
  "model_id": "wavespeed-ai/z-image/turbo",
  "node_id": "node_abc",
  "raw_output": {},
  "output_urls": [],
  "asset_ids": [],
  "error": null
}
```

### 5.7 WaveSpeed adapter

Create a single service class:

```text
WaveSpeedAdapter
```

Responsibilities:

- Validate that API key exists.
- Run any model by ID.
- Upload local file to WaveSpeed.
- Extract output URLs from WaveSpeed responses.
- Return clear errors to FastAPI routes.

The rest of the app should not import the WaveSpeed SDK directly.

## 6. API requirements

### 6.1 Health

```text
GET /api/health
```

Returns:

```json
{
  "ok": true,
  "app": "WaveSpeed Canvas MVP",
  "env": "local",
  "wavespeed_key_configured": true
}
```

### 6.2 Model categories

```text
GET /api/categories
GET /api/models
GET /api/models?enabled_only=true
```

### 6.3 Projects

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
PUT    /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

### 6.4 Assets

```text
POST /api/assets/upload
```

Query parameter:

```text
upload_to_wavespeed=true|false
```

### 6.5 Runs

```text
POST /api/runs/node
```

## 7. Suggested backend structure

```text
app/
  main.py
  schemas.py
  core/
    config.py
    storage.py
  routers/
    health.py
    models.py
    projects.py
    assets.py
    runs.py
  services/
    registry.py
    wavespeed_adapter.py
    node_runner.py        TODO
    workflow_resolver.py  TODO
```

## 8. Suggested frontend structure

Current scaffold:

```text
web/index.html
web/style.css
web/app.js
```

Production direction:

```text
frontend/
  package.json
  src/
    main.tsx
    App.tsx
    api/client.ts
    components/
      Canvas.tsx
      NodeLibrary.tsx
      Inspector.tsx
      AssetPanel.tsx
      OutputPreview.tsx
    nodes/
      TextToImageNode.tsx
      ImageToImageNode.tsx
      ImageToVideoNode.tsx
```

Recommended library:

```text
React Flow
```

## 9. Node type requirements

### 9.1 Upload Image

Inputs:

- File.

Outputs:

- Image asset.
- Local URL.
- Optional WaveSpeed URL.

### 9.2 Text to Image

Inputs:

- prompt: string, required.
- size: string, optional.
- seed: integer, optional.
- output_format: string, optional.

Output:

- Image URL.

Initial enabled model:

```text
wavespeed-ai/z-image/turbo
```

### 9.3 Image to Image / Remix

Inputs:

- image: string URL, required.
- prompt: string, required.
- strength: number 0.0 to 1.0.
- size: string.
- seed: integer.
- output_format: string.

Output:

- Image URL.

Initial enabled model:

```text
wavespeed-ai/z-image-turbo/image-to-image
```

### 9.4 Reference to Image

Inputs:

- reference image URL.
- prompt.
- optional strength / guidance fields depending on model.

Output:

- Image URL.

MVP status:

```text
Disabled placeholder until model ID is verified.
```

### 9.5 Upscale Image

Inputs:

- image URL.
- scale or target size.

Output:

- Image URL.

MVP status:

```text
Disabled placeholder until model ID is verified.
```

### 9.6 Remove Background

Inputs:

- image URL.

Output:

- Transparent image URL or image URL.

MVP status:

```text
Disabled placeholder until model ID is verified.
```

### 9.7 Image to Video

Inputs:

- image URL.
- motion prompt.
- duration.
- aspect ratio.

Output:

- Video URL.

MVP status:

```text
Disabled placeholder until model ID is verified.
```

### 9.8 Start-End Video

Inputs:

- start image URL.
- end image URL.
- motion prompt.
- duration.

Output:

- Video URL.

MVP status:

```text
Disabled placeholder until model ID is verified.
```

### 9.9 Generate Voice

Inputs:

- text.
- voice.
- speed.
- language.

Output:

- Audio URL.

MVP status:

```text
Disabled placeholder until model ID is verified.
```

### 9.10 Lip Sync / Avatar

Inputs:

- portrait image URL.
- audio URL.
- optional prompt.

Output:

- Video URL.

MVP status:

```text
Disabled placeholder until model ID is verified.
```

## 10. Non-goals

The app must not become a professional editing suite in MVP.

Do not build:

- Photoshop layers.
- Vector drawing.
- Mask painting.
- Timeline editing.
- Keyframes.
- Pro color grading.
- Multi-user collaborative editing.
- Plugin marketplace.

## 11. Error handling requirements

The backend must return clear errors for:

- Missing WaveSpeed API key.
- Placeholder model ID.
- Disabled model.
- Invalid project ID.
- Invalid upload type or upload too large.
- WaveSpeed SDK errors.
- No output URL returned.

Frontend must show:

- Node status.
- Error message.
- Raw response for debugging in dev mode.

## 12. Security requirements for later

Before public launch, add:

- User authentication.
- Per-user project ownership.
- File type allowlist.
- File size limits.
- Rate limiting.
- API key stored only server-side.
- Usage tracking.
- Cost controls.
- Basic content moderation for user prompts/uploads.

## 13. Acceptance criteria for MVP scaffold

The scaffold is acceptable when:

- `python -m uvicorn app.main:app --reload --port 8000` starts without syntax errors.
- `/api/health` returns OK.
- `/api/models` returns node registry.
- User can create project from UI.
- User can add a Text to Image node.
- User can run Text to Image node when WaveSpeed API key is valid.
- User can save project JSON.
- User can upload an asset.
- Disabled placeholder models cannot run until verified and enabled.

## 14. Codex implementation instruction

Use this file as the build source of truth.

Implement in phases:

1. Stabilize existing scaffold.
2. Add proper graph canvas.
3. Add model-specific inspector forms.
4. Add edge connection and automatic input mapping.
5. Add previews and run history.
6. Add more verified WaveSpeed model IDs.
7. Add persistent DB.
8. Add auth and deployment.
