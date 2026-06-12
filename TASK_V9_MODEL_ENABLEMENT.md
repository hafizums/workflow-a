# TASK_V9.md — Functionality Upgrade: Model Enablement & Media Workflows

## Mission

V9 must **stop focusing on UI redesign** and focus on the core product problem: many useful WaveSpeed model categories are still disabled or blocked by the runner.

The goal is to safely enable more runnable models, make audio/video/3D/text assets usable inside workflows, and add tests so future model enablement is repeatable.

## Current repo facts to respect

The current app already has:

- A static FastAPI frontend and local JSON project storage.
- A model catalog with many candidate model IDs in `app/services/model_catalog.py`.
- A registry in `app/services/registry.py` that only exposes verified fields for enabled entries.
- A runner in `app/services/node_runner.py` that currently hard-blocks execution to a short allowlist of model IDs.
- An upload endpoint in `app/routers/assets.py` that already infers image, video, audio, or other assets from uploaded files.

The current bottleneck is not UI polish. It is that model execution is not generalized enough.

## Non-goals

Do **not** do another major UI redesign in V9.

Do **not** migrate to React.

Do **not** add auth, database, billing, or multi-user features.

Do **not** blindly enable every catalog entry.

Do **not** build complex Photoshop-style mask drawing in V9. For mask-based models, allow users to provide a mask image asset by upload or URL.

## Main deliverables

1. More disabled model nodes become safely runnable.
2. The runner supports model execution through a registry-driven capability map, not a tiny hardcoded model-id set.
3. Project assets can be image, audio, video, or other files, and those assets can be selected as model inputs.
4. Audio and video workflows work end-to-end.
5. Speech-to-text can return useful text even when the model does not return media URLs.
6. Tests and fixtures prove that each newly enabled model has verified fields and a working preparation function.
7. README and model docs are updated with the newly enabled model list.

---

## Phase 0 — Audit and lock current behavior

Create a short audit command or test that prints:

- Total catalog entries.
- Enabled entries.
- Disabled entries.
- Disabled entries grouped by `verification_status`.
- Enabled entries that have no fields and are not local upload nodes.
- Enabled entries that the runner still cannot execute.

Add this as either:

```text
scripts/audit_models.py
```

or a pytest test under:

```text
tests/test_model_catalog_audit.py
```

Acceptance:

- Running the audit clearly shows why V9 is needed.
- The audit must fail if an enabled WaveSpeed model has no registered fields.
- The audit must fail if an enabled WaveSpeed model has no runner/preparer support.

---

## Phase 1 — Expand model field schema

Edit `app/schemas.py`.

Current `ModelField` is too small for serious model support. Extend it while keeping backward compatibility.

Add optional fields:

```python
class ModelField(BaseModel):
    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str = ""

    # V9 additions
    options: list[Any] = Field(default_factory=list)
    asset_kind: AssetKind | None = None
    accept: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    placeholder: str | None = None
```

Allowed field types for V9:

```text
string
textarea
integer
number
boolean
select
asset_url
```

Rules:

- `asset_kind` must be set for `asset_url` fields whenever possible.
- `accept` should match upload input types such as `image/*`, `audio/*`, `video/*`.
- `options` should be used for known enumerations such as duration, resolution, task, language, output format, and video size.
- Existing projects must continue to load.

Acceptance:

- Existing V8 projects still deserialize.
- `/api/models` includes the new optional field metadata.
- Existing text-to-image, image-to-image, upscale, background removal, image-to-video, and TTS nodes still work.

---

## Phase 2 — Make asset input resolution generic

Edit `app/services/node_runner.py`.

Current resolver is image-specific. Replace the image-only resolver with generic asset resolution.

Add:

```python
async def resolve_asset_input(
    adapter: WaveSpeedAdapter,
    inputs: dict[str, Any],
    project: Project | None,
    field_name: str,
    expected_kinds: set[AssetKind] | None = None,
) -> str:
    ...
```

Behavior:

1. Accept project asset ID, `public_url`, `wavespeed_url`, `local_path`, or direct public URL.
2. If a project asset has `wavespeed_url`, use it.
3. If a project asset has local file path and no `wavespeed_url`, upload through `adapter.upload_file()` and save the returned URL back onto the asset.
4. Reject localhost URLs for remote WaveSpeed inputs.
5. Enforce expected asset kind when `expected_kinds` is provided.
6. Produce clear errors such as:
   - `audio is required.`
   - `Expected audio asset for audio, got image.`
   - `Localhost video URLs are not reachable by WaveSpeed. Upload the asset first.`

Keep wrappers:

```python
resolve_image_input(...)
resolve_audio_input(...)
resolve_video_input(...)
```

Add helper:

```python
def resolve_asset_kind_from_url(url: str) -> AssetKind:
    ...
```

Update suffix support in `url_suffix()`:

```text
Images: .png .jpg .jpeg .webp .gif
Video:  .mp4 .mov .webm .mkv
Audio:  .mp3 .wav .m4a .ogg .flac
3D/other: .glb .gltf .obj .fbx .stl .usdz .zip
Text/other: .txt .json .srt .vtt
```

Acceptance:

- Existing image inputs still work.
- Audio assets can be uploaded once, reused, and sent to WaveSpeed.
- Video assets can be uploaded once, reused, and sent to WaveSpeed.
- Localhost URLs are still blocked for remote WaveSpeed calls.
- When an asset is uploaded to WaveSpeed during preparation, the project is saved so the upload URL is reused.

---

## Phase 3 — Replace hardcoded model runner allowlist

Edit `app/services/node_runner.py`.

Current `SUPPORTED_MODEL_IDS` blocks many registry models even if they are enabled. Replace it with a node-type preparer registry.

Add a map like:

```python
PREPARERS_BY_NODE_TYPE = {
    NodeType.text_to_image: prepare_text_to_image_inputs,
    NodeType.image_to_image: prepare_image_to_image_inputs,
    NodeType.reference_to_image: prepare_reference_to_image_inputs,
    NodeType.upscale_image: prepare_upscale_image_inputs,
    NodeType.remove_background: prepare_remove_background_inputs,
    NodeType.remove_object: prepare_inpaint_inputs,
    NodeType.image_to_video: prepare_image_to_video_inputs,
    NodeType.start_end_to_video: prepare_start_end_to_video_inputs,
    NodeType.text_to_video: prepare_text_to_video_inputs,
    NodeType.text_to_speech: prepare_text_to_speech_inputs,
    NodeType.generate_voice: prepare_voice_design_inputs,
    NodeType.speech_to_text: prepare_speech_to_text_inputs,
    NodeType.lip_sync: prepare_lip_sync_inputs,
    NodeType.talking_avatar: prepare_talking_avatar_inputs,
    NodeType.text_to_3d: prepare_text_to_3d_inputs,
}
```

Rules:

- `run_wavespeed_node()` must resolve the model through the registry first.
- A model is runnable if:
  - It is enabled in the registry.
  - Its node type has a preparer.
  - The registry model ID matches the node type.
- Do not use a global tiny allowlist of model IDs as the main gate.
- It is acceptable to keep a denylist for known-broken models, but that denylist must include a reason.

Acceptance:

- Adding an enabled model with a supported node type no longer requires editing `SUPPORTED_MODEL_IDS`.
- Tests prove enabled models have preparers.
- Disabled catalog entries still cannot run.

---

## Phase 4 — Support uploadable audio/video/other assets

The backend upload endpoint already accepts many content types. The app workflow needs to expose this functionality.

Minimum required changes:

### Backend

No major backend route needed unless validation is missing.

Confirm `/api/assets/upload` supports:

```text
image/*
video/*
audio/*
application/octet-stream
model/ or zip-like files as other
```

### Frontend minimal functional changes

Do not redesign the UI. Make only functional changes in `web/app.js` and existing HTML.

Change the upload node from image-only to generic asset upload:

- Display name may become `Upload Asset`.
- File input should accept:
  ```text
  image/*,video/*,audio/*,.glb,.gltf,.obj,.fbx,.stl,.usdz,.zip,.txt,.json,.srt,.vtt
  ```
- Keep backward compatibility with node type `upload_image` unless you add a migration for a new `upload_asset` node type.
- After upload, node output kind should be dynamic based on the actual uploaded asset kind.

Update `sourceOutputKind(node)`:

1. If the node has output assets, return the first output asset kind.
2. Else fall back to the model output kind.
3. Else fall back to node type.

Update asset selectors:

- `asset_url` field with `asset_kind=image` shows image assets.
- `asset_url` field with `asset_kind=audio` shows audio assets.
- `asset_url` field with `asset_kind=video` shows video assets.
- `asset_url` field with no `asset_kind` shows all assets with usable URLs.
- The label should say `Choose audio asset`, `Choose video asset`, etc.

Acceptance:

- User can upload audio and connect/select it for speech-to-text, voice/avatar, or lip-sync nodes.
- User can upload video and connect/select it for lip-sync nodes.
- Existing image upload workflows still work.

---

## Phase 5 — Enable priority model batch

Enable this first batch because the required fields are straightforward and fit the current workflow product.

For each model below:

1. Update `app/services/model_catalog.py`.
2. Update `VERIFIED_FIELDS_BY_NODE_TYPE` in `app/services/registry.py`.
3. Add/verify the preparer in `app/services/node_runner.py`.
4. Add unit tests.
5. Add one mocked run fixture.
6. Run one real manual dry-run only after tests pass and API key is available.
7. Mark `verification_status="verified"` only after docs and dry-run are confirmed.

### 5.1 Start-End Video

Node type:

```text
start_end_to_video
```

Model:

```text
wavespeed-ai/wan-2.2/i2v-480p-ultra-fast
```

Fields:

```python
[
    ModelField(name="image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Start frame image."),
    ModelField(name="last_image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="End frame image."),
    ModelField(name="prompt", type="textarea", required=True, description="Motion prompt."),
    ModelField(name="negative_prompt", type="textarea", required=False, default="", description="Things to avoid."),
    ModelField(name="duration", type="select", required=False, default=5, options=[5, 8], description="Duration in seconds."),
    ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
]
```

Preparer:

```text
prepare_start_end_to_video_inputs
```

Rules:

- Require both `image` and `last_image`.
- Resolve both as image assets.
- Convert `duration` and `seed` to integers.
- Reuse the existing I2V model ID.
- Output kind: video.

### 5.2 Text to Video

Node type:

```text
text_to_video
```

Model:

```text
wavespeed-ai/wan-2.2/t2v-480p-ultra-fast
```

Fields:

```python
[
    ModelField(name="prompt", type="textarea", required=True, description="Video prompt."),
    ModelField(name="negative_prompt", type="textarea", required=False, default="", description="Things to avoid."),
    ModelField(name="size", type="select", required=False, default="832*480", options=["832*480", "480*832"], description="Video size."),
    ModelField(name="duration", type="select", required=False, default=5, options=[5, 8], description="Duration in seconds."),
    ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
]
```

Preparer:

```text
prepare_text_to_video_inputs
```

Output kind: video.

### 5.3 Speech to Text

Node type:

```text
speech_to_text
```

Model:

```text
wavespeed-ai/openai-whisper
```

Fields:

```python
[
    ModelField(name="audio", type="asset_url", asset_kind=AssetKind.audio, required=True, accept="audio/*", description="Audio file or public URL."),
    ModelField(name="language", type="string", required=False, default="auto", description="Language code or auto."),
    ModelField(name="task", type="select", required=False, default="transcribe", options=["transcribe", "translate"], description="Transcribe original language or translate to English."),
    ModelField(name="enable_timestamps", type="boolean", required=False, default=False, description="Generate word-level timestamps when supported."),
    ModelField(name="prompt", type="textarea", required=False, default="", description="Optional transcription guidance."),
    ModelField(name="enable_sync_mode", type="boolean", required=False, default=False, description="Use sync mode only if supported by API."),
]
```

Preparer:

```text
prepare_speech_to_text_inputs
```

Special output handling:

- Do not fail just because there are no media URLs.
- Extract transcript text from likely response keys:
  ```text
  text
  transcript
  transcription
  output.text
  data.text
  outputs[0].text
  ```
- Store transcript in:
  ```python
  target_node.last_run["text_output"]
  ```
- Optionally create a text asset later, but not required for V9.

Output kind: other.

### 5.4 Generate Voice / Voice Design

Node type:

```text
generate_voice
```

Model:

```text
wavespeed-ai/qwen3-tts/voice-design
```

Fields:

```python
[
    ModelField(name="text", type="textarea", required=True, description="Text to speak."),
    ModelField(name="voice_description", type="textarea", required=True, description="Natural-language voice description."),
    ModelField(name="language", type="select", required=False, default="auto", options=["auto", "Chinese", "English", "German", "Italian", "Portuguese", "Spanish", "Japanese", "Korean", "French", "Russian"], description="Language."),
]
```

Preparer:

```text
prepare_voice_design_inputs
```

Output kind: audio.

### 5.5 Lip Sync

Node type:

```text
lip_sync
```

Model:

```text
wavespeed-ai/latentsync
```

Fields:

```python
[
    ModelField(name="video", type="asset_url", asset_kind=AssetKind.video, required=True, accept="video/*", description="Source talking-head video."),
    ModelField(name="audio", type="asset_url", asset_kind=AssetKind.audio, required=True, accept="audio/*", description="Speech audio."),
]
```

Preparer:

```text
prepare_lip_sync_inputs
```

Output kind: video.

### 5.6 Talking Avatar

Node type:

```text
talking_avatar
```

Model:

```text
wavespeed-ai/infinitetalk
```

Fields:

```python
[
    ModelField(name="image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Person image to animate."),
    ModelField(name="audio", type="asset_url", asset_kind=AssetKind.audio, required=True, accept="audio/*", description="Speech or singing audio."),
    ModelField(name="mask_image", type="asset_url", asset_kind=AssetKind.image, required=False, accept="image/*", description="Optional mask image."),
    ModelField(name="prompt", type="textarea", required=False, default="", description="Optional expression, style, or pose guidance."),
    ModelField(name="resolution", type="select", required=False, default="480p", options=["480p", "720p"], description="Output resolution."),
    ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
]
```

Preparer:

```text
prepare_talking_avatar_inputs
```

Safety/cost note:

- Default to `480p`.
- Warn through existing cost guard because this model can be more expensive than image models.
- Do not require `mask_image`.

Output kind: video.

### 5.7 Text to 3D

Node type:

```text
text_to_3d
```

Model:

```text
wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid
```

Fields:

```python
[
    ModelField(name="prompt", type="textarea", required=True, description="Text description of the 3D asset."),
]
```

Preparer:

```text
prepare_text_to_3d_inputs
```

Output kind: other.

Output handling:

- Accept URLs ending in `.glb`, `.gltf`, `.obj`, `.fbx`, `.stl`, `.usdz`, `.zip`, or any HTTP URL returned by the model.
- Asset kind can remain `other` for V9.

### 5.8 Remove Object / Inpaint

Node type:

```text
remove_object
```

Model:

```text
wavespeed-ai/z-image/turbo-inpaint
```

Fields:

```python
[
    ModelField(name="prompt", type="textarea", required=True, description="Describe what to remove, repair, or replace."),
    ModelField(name="image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Source image."),
    ModelField(name="mask_image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Mask image where white/marked area is edited."),
    ModelField(name="size", type="string", required=False, default="1024*1024", description="Output size if supported."),
]
```

Preparer:

```text
prepare_inpaint_inputs
```

Rules:

- No browser mask editor in V9.
- User must upload/select a mask image.
- If this model fails dry-run, keep it disabled and document why.

Output kind: image.

### 5.9 Reference to Image

Node type:

```text
reference_to_image
```

Model:

```text
wavespeed-ai/z-image-turbo/image-to-image
```

Fields:

```python
[
    ModelField(name="reference_image", type="asset_url", asset_kind=AssetKind.image, required=True, accept="image/*", description="Reference image."),
    ModelField(name="prompt", type="textarea", required=True, description="Prompt guided by the reference image."),
    ModelField(name="size", type="string", required=False, default="1024*1024", description="Output size."),
    ModelField(name="strength", type="number", required=False, default=0.6, min_value=0, max_value=1, step=0.05, description="How strongly to transform the reference."),
    ModelField(name="seed", type="integer", required=False, default=-1, description="-1 means random seed."),
    ModelField(name="output_format", type="select", required=False, default="jpeg", options=["jpeg", "png", "webp"], description="Output format."),
]
```

Preparer:

```text
prepare_reference_to_image_inputs
```

Rules:

- Map `reference_image` to the model's expected `image` input before calling WaveSpeed.
- Output kind: image.

---

## Phase 6 — Keep remaining models disabled until verified

Keep these disabled unless Codex verifies docs, request fields, response shape, and one dry-run:

```text
text_to_audio
reference_to_video
video_extend
video_effect
portrait_transfer
image_to_3d
```

For each skipped model, update `enabled_reason` with a useful reason, not only "fields not verified."

Examples:

```text
image_to_3d: Disabled until multi-image input UX and output file handling are verified.
video_extend: Disabled until source video field, duration/extension controls, and cost behavior are verified.
reference_to_video: Disabled until required reference media fields and response shape are verified.
```

Acceptance:

- Disabled entries are intentionally disabled with specific reasons.
- The UI no longer feels like broken buttons; disabled nodes explain what is missing.

---

## Phase 7 — Registry and catalog consistency rules

Add tests that enforce these rules:

1. Every enabled WaveSpeed model must have at least one `ModelField`.
2. Every enabled WaveSpeed model must have:
   - `default_model_id`
   - `estimated_base_cost_usd` or a documented unknown-cost reason
   - `docs_url`
   - `verification_status == "verified"`
   - non-empty `enabled_reason`
3. Every enabled node type must have a runner preparer.
4. Every `asset_url` field should have `asset_kind` unless the input genuinely accepts any media.
5. Every field with `type="select"` should have non-empty `options`.
6. Every catalog model ID should resolve through `get_model_for_node()`.

Suggested test files:

```text
tests/test_model_registry_contract.py
tests/test_node_runner_preparers.py
tests/test_asset_resolution.py
```

Acceptance:

```bash
pytest
```

passes.

---

## Phase 8 — Add mocked WaveSpeed fixtures

Do not rely only on live API tests.

Add fixture responses for each enabled model:

```text
tests/fixtures/wavespeed/text_to_video.json
tests/fixtures/wavespeed/speech_to_text.json
tests/fixtures/wavespeed/generate_voice.json
tests/fixtures/wavespeed/lip_sync.json
tests/fixtures/wavespeed/talking_avatar.json
tests/fixtures/wavespeed/text_to_3d.json
tests/fixtures/wavespeed/inpaint.json
```

Mock `WaveSpeedAdapter.run_model()` in unit tests.

Example expected output shapes:

```json
{
  "outputs": ["https://example.com/output.mp4"]
}
```

```json
{
  "text": "This is the transcript."
}
```

```json
{
  "outputs": ["https://example.com/model.glb"]
}
```

Acceptance:

- Unit tests validate input preparation without spending API credits.
- Unit tests validate output extraction.
- Speech-to-text success does not require a URL output.

---

## Phase 9 — Minimal API smoke commands

Add or document curl commands for the new runnable models.

Create:

```text
docs/V9_MODEL_ENABLEMENT.md
```

Include examples for:

- `/api/models`
- `/api/assets/upload?upload_to_wavespeed=true`
- `/api/runs/node` for:
  - text_to_video
  - speech_to_text
  - generate_voice
  - lip_sync
  - talking_avatar
  - text_to_3d
  - remove_object
  - reference_to_image
  - start_end_to_video

Use placeholder URLs and mention that local file URLs are not reachable by WaveSpeed.

Acceptance:

- A developer can verify every new node by following the doc.
- No secrets are committed.

---

## Phase 10 — README update

Update README:

- Change V8 section to say V8 was UI organization.
- Add V9 section:
  ```text
  V9 focuses on model enablement and media workflow functionality.
  ```
- Update enabled model list.
- Add note that upload node now supports image, audio, video, and other assets.
- Add warning that mask-based models require a supplied mask image in V9.
- Add warning that some disabled nodes remain disabled until docs and dry-run are verified.

---

## Manual verification checklist

Run:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

Check:

- `/api/health` returns OK.
- `/api/models` shows the newly enabled nodes.
- Existing image generation still works.
- Upload image still works.
- Upload audio works.
- Upload video works.
- Text-to-video queues and completes.
- Start-end video queues and completes with two image assets.
- Speech-to-text queues and stores transcript in node last run.
- Generate voice queues and returns audio.
- Lip sync queues and returns video using uploaded video + audio.
- Talking avatar queues and returns video using image + audio.
- Text-to-3D queues and stores returned model URL as an `other` asset.
- Remove-object/inpaint works with source image + mask image, or remains disabled with a clear reason if dry-run fails.
- Workflow run modes still work:
  - selected
  - from selected
  - whole graph
- Run Manager still supports:
  - queue
  - poll
  - cancel queued
  - request cancel running
  - retry failed/cancelled

---

## Final acceptance criteria

V9 is complete when:

1. At least **six previously disabled model nodes** are enabled and runnable after verification.
2. Audio and video assets can be uploaded and used as model inputs.
3. Speech-to-text can succeed without media URL outputs.
4. The runner is no longer blocked by the old tiny `SUPPORTED_MODEL_IDS` pattern.
5. Enabled model entries have field schemas, preparers, tests, and docs.
6. Disabled models have specific actionable reasons.
7. Existing V8 UI functionality still works.
8. `pytest` passes.
9. README and `docs/V9_MODEL_ENABLEMENT.md` are updated.
10. No API keys, generated media, local uploads, or secrets are committed.

---

## Suggested implementation order for Codex

1. Add tests that expose the current blockers.
2. Extend `ModelField`.
3. Generalize asset resolution.
4. Replace `SUPPORTED_MODEL_IDS` with preparer registry.
5. Make upload asset generic.
6. Enable Start-End Video and Text-to-Video first.
7. Enable Speech-to-Text and Generate Voice.
8. Enable Lip Sync and Talking Avatar.
9. Enable Text-to-3D.
10. Enable Remove Object and Reference-to-Image only after the above is stable.
11. Update docs and README.
