# TASK_V3.md — Cost-Aware WaveSpeed Model Catalog + First Expanded Media Nodes

## Status

This is the next major task after `TASK_V2.md`.

Assume `TASK_V2.md` has already been completed and the app now has a working workflow execution engine, graph execution plan, run-from-node, run-whole-graph, node status updates, and project-level run history.

If any `TASK_V2` feature is missing, do **not** rewrite the app. Inspect the repo, identify what is missing, and make the smallest compatibility changes needed before continuing.

---

## High-level goal

Build **TASK V3: Cost-Aware Model Catalog + First Expanded WaveSpeed Nodes**.

The product should now move from only two executable image nodes to a controlled, cost-aware model system that can safely expand into image utilities, video, audio, avatar, and 3D later.

The goal is **not** to enable every model immediately.

The goal is to:

1. Add a centralized cost-aware model catalog.
2. Add `CHEAPEST_MODEL_BY_NODE_TYPE` as configuration.
3. Show estimated model cost and output type in the UI.
4. Support project/node-level model override.
5. Enable only a small safe batch of new models after verifying their official request parameters.
6. Keep all risky or unverified models disabled.
7. Preserve the existing FastAPI + vanilla HTML/CSS/JS architecture.

---

## Boss-provided model candidate list

Important: this list is useful, but treat it as **candidate metadata**, not final truth.

The boss note says the absolute cheapest model across every WaveSpeed model cannot be verified without the full live catalog/API response. It also says pricing is usually a starting/base price and final cost may change by model parameters such as duration, resolution, or character count.

Therefore:

- Do not present estimated cost as exact billing.
- Use `estimated_base_cost_usd` and `pricing_note` naming.
- Use `verification_status` values.
- Before enabling execution for a model, verify its model page or API docs and confirm required request fields.
- If request fields cannot be verified, keep the model in the catalog but disabled.

Candidate mapping:

| Node type | Candidate model ID | Estimated starts at | Implementation status for TASK V3 |
|---|---:|---:|---|
| `upload_image` | No model needed | `$0` | Already local app behavior |
| `text_to_image` | `wavespeed-ai/z-image/turbo` | `$0.005/run` | Already enabled; keep working |
| `image_to_image` | `wavespeed-ai/z-image-turbo/image-to-image` | `$0.005/run` | Already enabled; keep working |
| `reference_to_image` | `wavespeed-ai/z-image-turbo/image-to-image` | `$0.005/run` | Add as alias/planned; optional disabled unless UX is clear |
| `upscale_image` | `wavespeed-ai/image-upscaler` | `$0.010/run` | Enable only after verifying request fields |
| `remove_background` | `wavespeed-ai/image-background-remover` | `$0.010/image` | Enable only after verifying request fields |
| `remove_object` | `wavespeed-ai/z-image/turbo-inpaint` | `$0.020/run` | Keep disabled; requires mask/inpaint UX |
| `image_to_video` | `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast` | `$0.050/run` | Preferred first video node; enable only after verifying request fields |
| `start_end_to_video` | `wavespeed-ai/wan-2.2/i2v-480p-ultra-fast` | `$0.050/run` | Keep disabled unless `last_image` support is verified directly |
| `text_to_video` | `wavespeed-ai/wan-2.2/t2v-480p-ultra-fast` | `$0.050/run` | Keep disabled for now |
| `reference_to_video` | `alibaba/wan-2.6/reference-to-video-flash` | `$0.13/run` | Keep disabled for now |
| `video_extend` | `vidu/q2-turbo/extend-video` | `$0.20/run` | Keep disabled for now |
| `video_effect` | `vidu/template/halloween` | `$0.050/run` | Keep disabled for now |
| `text_to_speech` | `wavespeed-ai/qwen3-tts/text-to-speech` | `$0.005/run` | Enable only after verifying request fields |
| `text_to_audio` | `wavespeed-ai/qwen3-tts/text-to-speech` | `$0.005/run` | Keep disabled or alias to TTS only if product language is clear |
| `speech_to_text` | `wavespeed-ai/openai-whisper` | `$0.001/run` | Keep disabled for now |
| `generate_voice` | `wavespeed-ai/qwen3-tts/voice-design` | `$0.005/run` | Keep disabled for now |
| `talking_avatar` | `wavespeed-ai/infinitetalk` | `$0.150/run` | Keep disabled for now |
| `lip_sync` | `wavespeed-ai/latentsync` | `$0.050/run` | Keep disabled for now |
| `portrait_transfer` | `wavespeed-ai/image-body-swap` or `wavespeed-ai/video-face-swap` | `$0.050/run` | Keep disabled for now |
| `image_to_3d` | `wavespeed-ai/hunyuan3d-v2-multi-view` | `$0.010/run` | Keep disabled for now; multi-view input needed |
| `text_to_3d` | `wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid` | `$0.022/run` | Keep disabled for now |
| `generic_wavespeed` | No fixed model | `—` | Fallback/router concept only; do not expose as runnable model yet |

---

## Non-goals for TASK V3

Do **not** do these in this task:

- Do not convert to React.
- Do not add React Flow.
- Do not add Next.js.
- Do not add Tailwind.
- Do not add a database.
- Do not add authentication.
- Do not add billing.
- Do not add team/multi-user collaboration.
- Do not add professional editing tools.
- Do not add brush masks, vector drawing, Photoshop layers, crop studio, keyframes, or timeline editing.
- Do not enable every WaveSpeed model at once.
- Do not guess request parameters.
- Do not hardcode the WaveSpeed API key.
- Do not call WaveSpeed SDK outside `WaveSpeedAdapter`.

---

## Files to inspect first

Read these files before making edits:

```text
TASK_V2.md
PROJECT_SUMMARY.md
requirements.md
CODEX_TASKS.md
README.md
app/main.py
app/schemas.py
app/services/registry.py
app/services/node_runner.py
app/services/wavespeed_adapter.py
app/services/project_store.py
app/services/workflow_resolver.py
app/routers/models.py
app/routers/runs.py
app/routers/workflows.py
web/index.html
web/style.css
web/app.js
```

If file names differ because TASK V2 refactored them, inspect the repo and adapt without large rewrites.

---

## Checkpoint 1 — Add centralized model catalog

Create a dedicated model catalog module:

```text
app/services/model_catalog.py
```

This module should define:

```python
CHEAPEST_MODEL_BY_NODE_TYPE = {
    "text_to_image": "wavespeed-ai/z-image/turbo",
    "image_to_image": "wavespeed-ai/z-image-turbo/image-to-image",
    "reference_to_image": "wavespeed-ai/z-image-turbo/image-to-image",
    "upscale_image": "wavespeed-ai/image-upscaler",
    "remove_background": "wavespeed-ai/image-background-remover",
    "remove_object": "wavespeed-ai/z-image/turbo-inpaint",
    "image_to_video": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
    "start_end_to_video": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
    "text_to_video": "wavespeed-ai/wan-2.2/t2v-480p-ultra-fast",
    "reference_to_video": "alibaba/wan-2.6/reference-to-video-flash",
    "video_extend": "vidu/q2-turbo/extend-video",
    "video_effect": "vidu/template/halloween",
    "text_to_speech": "wavespeed-ai/qwen3-tts/text-to-speech",
    "text_to_audio": "wavespeed-ai/qwen3-tts/text-to-speech",
    "speech_to_text": "wavespeed-ai/openai-whisper",
    "generate_voice": "wavespeed-ai/qwen3-tts/voice-design",
    "talking_avatar": "wavespeed-ai/infinitetalk",
    "lip_sync": "wavespeed-ai/latentsync",
    "portrait_transfer": "wavespeed-ai/image-body-swap",
    "image_to_3d": "wavespeed-ai/hunyuan3d-v2-multi-view",
    "text_to_3d": "wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid",
}
```

Also define a richer catalog list or dictionary with this metadata for every node type:

```python
{
    "node_type": "image_to_video",
    "category": "video",
    "default_model_id": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
    "display_name": "Image to Video",
    "description": "Animate an image into a short video.",
    "output_kind": "video",
    "estimated_base_cost_usd": 0.05,
    "cost_unit": "run",
    "pricing_note": "Starting estimate only; final cost may depend on duration, resolution, and model parameters.",
    "docs_url": "https://wavespeed.ai/models/wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
    "verification_status": "candidate|verified|disabled|needs_params",
    "enabled": False,
    "enabled_reason": "Disabled until official request fields are verified."
}
```

Required verification status values:

```text
verified
candidate
needs_params
disabled
experimental
```

Rules:

- `text_to_image` and `image_to_image` should remain `enabled: true` and `verification_status: verified` only if they are already working in the app.
- New model candidates should start as `enabled: false` until their official fields are verified.
- `estimated_base_cost_usd` must be nullable.
- Never call an estimated price exact billing.

---

## Checkpoint 2 — Extend schemas and registry cleanly

Update schemas without breaking existing API responses.

Add or extend models in `app/schemas.py` as needed:

```python
class CostMetadata(BaseModel):
    estimated_base_cost_usd: float | None = None
    cost_unit: str | None = None
    pricing_note: str | None = None

class CatalogModelSpec(BaseModel):
    node_type: str
    category: str
    default_model_id: str | None = None
    display_name: str
    description: str | None = None
    output_kind: str
    estimated_base_cost_usd: float | None = None
    cost_unit: str | None = None
    pricing_note: str | None = None
    docs_url: str | None = None
    verification_status: str
    enabled: bool = False
    enabled_reason: str | None = None
```

If the existing `ModelSpec` can be safely extended instead, extend it. Do not duplicate conflicting schema shapes.

Update `app/services/registry.py` so:

1. Existing `/api/models` still works.
2. Existing enabled models still work.
3. Disabled models remain visible but cannot run.
4. Catalog metadata appears in model responses.
5. Existing frontend code does not break.

---

## Checkpoint 3 — Add model catalog API endpoints

Create or extend router:

```text
app/routers/model_catalog.py
```

Add endpoints:

```text
GET /api/model-catalog
GET /api/model-catalog/cheapest
GET /api/model-catalog/{node_type}
```

Expected behavior:

### `GET /api/model-catalog`

Returns all catalog entries grouped or flat.

### `GET /api/model-catalog/cheapest`

Returns the `CHEAPEST_MODEL_BY_NODE_TYPE` mapping plus cost metadata.

### `GET /api/model-catalog/{node_type}`

Returns the model candidate and metadata for one node type.

Error handling:

- Unknown node type should return 404 with a clear error.
- Catalog entries with `enabled: false` must say why.

Update `app/main.py` to include the router.

---

## Checkpoint 4 — Add project and node model override support

Add optional override data, but keep JSON backward compatible.

Project-level shape:

```json
{
  "settings": {
    "model_overrides": {
      "image_to_video": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast"
    },
    "cost_guard": {
      "enabled": true,
      "warn_at_usd_per_run": 0.05,
      "block_at_usd_per_run": null
    }
  }
}
```

Node-level shape:

```json
{
  "id": "node_123",
  "node_type": "image_to_video",
  "model_id": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
  "inputs": {},
  "estimated_base_cost_usd": 0.05
}
```

Rules:

- Node-level model ID wins over project-level override.
- Project-level override wins over catalog default.
- If model is disabled or unverified, do not run it.
- Return a clear error if an override points to an unknown model ID.
- Existing projects without `settings` must still load.

---

## Checkpoint 5 — Add estimated run cost guard

Add a lightweight local cost estimate system.

This is not real billing.

Implement helper functions, preferably in `model_catalog.py` or a small `cost_estimator.py`:

```python
def get_estimated_base_cost(node_type: str, model_id: str | None = None) -> dict:
    ...
```

Add optional endpoint:

```text
POST /api/runs/estimate
```

Input:

```json
{
  "project_id": "project_abc",
  "node_id": "node_abc",
  "node_type": "image_to_video",
  "model_id": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast"
}
```

Output:

```json
{
  "ok": true,
  "node_type": "image_to_video",
  "model_id": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
  "estimated_base_cost_usd": 0.05,
  "cost_unit": "run",
  "pricing_note": "Starting estimate only; final cost may depend on duration, resolution, and model parameters.",
  "warning": "This is an estimate, not exact billing."
}
```

Before running a node with estimated cost greater than or equal to `warn_at_usd_per_run`, frontend should show a simple confirmation.

Do not add real payment/billing logic.

---

## Checkpoint 6 — Enable a small safe batch of new executable nodes

Enable only after verifying official model request fields.

Preferred enable order:

1. `remove_background`
2. `upscale_image`
3. `image_to_video`
4. `text_to_speech`

Do not enable all four if you cannot verify the request fields.

If a model's official field names are unclear, add it to the catalog but leave `enabled: false` with `verification_status: needs_params`.

### 6.1 Remove Background

Candidate:

```text
wavespeed-ai/image-background-remover
```

Expected product behavior:

```text
image URL -> transparent/background-removed image URL
```

Implementation rules:

- Verify official request field names.
- Support selected project asset or public/WaveSpeed URL.
- If selected asset is local-only, upload to WaveSpeed before running.
- Store output as image asset.
- Show image preview.

### 6.2 Upscale Image

Candidate:

```text
wavespeed-ai/image-upscaler
```

Expected product behavior:

```text
image URL -> higher-resolution image URL
```

Implementation rules:

- Verify official request field names.
- Support selected project asset or public/WaveSpeed URL.
- If selected asset is local-only, upload to WaveSpeed before running.
- Store output as image asset.
- Show image preview.

### 6.3 Image to Video

Candidate:

```text
wavespeed-ai/wan-2.2/i2v-480p-ultra-fast
```

Expected product behavior:

```text
image URL + motion prompt -> video URL
```

Implementation rules:

- Verify official request field names.
- Do not guess duration/aspect ratio/seed field names.
- Support selected project image asset or upstream image output.
- If selected asset is local-only, upload to WaveSpeed before running.
- Store output as video asset.
- Show video preview with a `<video controls>` element.
- Allow workflow edge mapping from image output node to image input of this node.

### 6.4 Text to Speech

Candidate:

```text
wavespeed-ai/qwen3-tts/text-to-speech
```

Expected product behavior:

```text
text -> audio URL
```

Implementation rules:

- Verify official request field names.
- Store output as audio asset.
- Show audio preview with `<audio controls>`.
- Keep voice/language fields only if verified.

---

## Checkpoint 7 — Extend node runner without breaking existing models

Update `app/services/node_runner.py` so it supports output kinds:

```text
image
video
audio
```

Rules:

- Keep text-to-image working.
- Keep image-to-image working.
- Do not duplicate WaveSpeed SDK calls outside `WaveSpeedAdapter`.
- Add model-specific input preparation functions.
- Validate required fields before calling WaveSpeed.
- Return clear errors for missing image, missing text, missing prompt, unsupported model, disabled model, or missing upstream output.
- Preserve `output_urls`, `output_asset_ids`, `last_run`, `error_message`, and node status behavior.

Suggested internal structure:

```python
async def run_node(...):
    if node_type == "text_to_image":
        return await _run_text_to_image(...)
    if node_type == "image_to_image":
        return await _run_image_to_image(...)
    if node_type == "remove_background":
        return await _run_remove_background(...)
    if node_type == "upscale_image":
        return await _run_upscale_image(...)
    if node_type == "image_to_video":
        return await _run_image_to_video(...)
    if node_type == "text_to_speech":
        return await _run_text_to_speech(...)
```

If you choose a dispatch table instead, keep it readable.

---

## Checkpoint 8 — Improve frontend model library and previews

Update vanilla frontend only.

### Node library

Show each node with:

- Display name.
- Category.
- Enabled/disabled badge.
- Output kind badge: image/video/audio/3D.
- Estimated base cost badge.
- Verification status.

Example labels:

```text
Image to Video
video · from $0.050/run · needs verification
```

### Node cards

Add support for:

- Image preview.
- Video preview.
- Audio preview.
- Output URL copy button.
- Asset download/open button.
- Estimated cost note.
- Disabled reason.

### Forms

If model-specific forms are already present, extend them.

If not, add minimal field rendering from `ModelSpec.fields` and do not redesign the entire frontend.

Field types to support:

```text
string
textarea
number
integer
boolean
select
asset_url
url
```

### Workflow mapping

Add default workflow mappings:

```text
image output -> image input
image output -> start_image input
image output -> reference_image input
video output -> video input
audio output -> audio input
```

For V3, the most important mapping is:

```text
text_to_image.output_urls[0] -> image_to_video.inputs.image
image_to_image.output_urls[0] -> image_to_video.inputs.image
```

---

## Checkpoint 9 — Asset grid and media previews

If TASK V2 did not already add a good asset panel, add a simple one now.

Asset grid should show:

- Asset type.
- Original filename or generated label.
- Thumbnail for image.
- `<video controls>` for video.
- `<audio controls>` for audio.
- Copy URL button.
- Open in new tab button.
- Source node ID if available.
- Created timestamp.

Do not implement cloud object storage yet.

---

## Checkpoint 10 — Tests and validation

Add or update tests where the project already has a test setup.

Minimum test targets:

1. `CHEAPEST_MODEL_BY_NODE_TYPE` contains all planned node types.
2. Every catalog entry has `node_type`, `category`, `output_kind`, `verification_status`, and `enabled`.
3. Enabled models cannot have placeholder model IDs.
4. Disabled models cannot run.
5. Existing text-to-image and image-to-image registry entries still exist.
6. Unknown node type returns clear error.
7. Cost estimate endpoint returns an estimate for known models.
8. Node runner rejects missing required fields.
9. Project JSON loads when `settings` is missing.
10. Workflow resolver can map image output to image-to-video input if image-to-video is enabled.

Validation commands:

```bat
python -m compileall app
node --check web/app.js
python -m uvicorn app.main:app --reload --port 8000
```

Manual API checks:

```bat
curl http://localhost:8000/api/health
curl http://localhost:8000/api/models
curl http://localhost:8000/api/model-catalog
curl http://localhost:8000/api/model-catalog/cheapest
curl http://localhost:8000/api/model-catalog/image_to_video
```

Manual UI checks:

1. Start the server.
2. Open `http://localhost:8000`.
3. Load an existing project.
4. Confirm old text-to-image and image-to-image nodes still run.
5. Confirm node library shows cost/verification badges.
6. Confirm disabled nodes show disabled reason.
7. Add a text-to-image node and run it.
8. Branch or connect it to image-to-video if image-to-video is enabled.
9. Run image-to-video only if model params were verified.
10. Confirm video asset appears with preview.
11. Add text-to-speech only if enabled and verified.
12. Confirm audio asset appears with preview.
13. Save project.
14. Refresh and reload.
15. Confirm nodes, edges, outputs, asset grid, and run history persist.

---

## Done criteria

TASK V3 is complete when:

- `TASK_V2` workflow behavior still works.
- `/api/models` still works.
- `/api/model-catalog` works.
- `/api/model-catalog/cheapest` works.
- Catalog includes the boss-provided candidate model mapping.
- Estimated cost metadata is shown in API and UI.
- Disabled/unverified models cannot run.
- Existing `text_to_image` and `image_to_image` still run.
- At least one new model category is enabled only after official request params are verified.
- Preferably enabled: `remove_background`, `upscale_image`, `image_to_video`, and/or `text_to_speech`.
- Image, video, and audio output preview components exist.
- No secrets are committed.
- No React/React Flow/database/auth/billing/pro editor tools are added.
- `python -m compileall app` passes.
- `node --check web/app.js` passes.

---

## Codex instruction

Use this as the prompt to start:

```text
Read TASK_V3.md and implement it.

Start by inspecting the repo and telling me:
1. Whether TASK_V2 is fully implemented.
2. Which files need to change for TASK_V3.
3. Which new WaveSpeed model request parameters you can verify from existing docs or repo context.
4. Which models must remain disabled because parameters are not verified.

Do not edit files until you show the plan.

After I approve, implement Checkpoint 1 and Checkpoint 2 first only.
```

Then continue checkpoint by checkpoint.

Do not implement all checkpoints in one massive edit unless I explicitly approve that.
