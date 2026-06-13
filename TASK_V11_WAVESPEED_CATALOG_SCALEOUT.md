# TASK V11 — WaveSpeed Catalog Scale-Out for Weave-Style Workflows

## Mission

Upgrade the current `workflow-a` repo from a hand-enabled model batch into a catalog-driven WaveSpeed tool engine.

Product goal: replicate Weave-style functional workflows — tool nodes, branching, variants, comparison, prompt/style/character helpers, artifact lineage, and export bundles — but every executable AI model/tool must come from WaveSpeed. Local utility nodes may orchestrate and organize, but must not call non-WaveSpeed AI APIs.

Assume these are already implemented and must be preserved:

- V9 model enablement and media asset support.
- V10 artifact lineage, branch-from-artifact, variants, model comparison, recipes, export packages, and run snapshots.
- Current FastAPI + vanilla static frontend structure.

Do not focus on UI polish in this task. Focus on enabling the full WaveSpeed catalog safely and maintainably.

---

## Current repo cross-reference

I inspected the latest repo state. The project is already beyond the old v8 UI task.

### Already implemented / do not redo

- `README.md` documents V9 model enablement and says the runner uses node-type preparers instead of the old tiny allowlist, with assets expanded to image/audio/video/other.
- `README.md` documents V10 Weave-style workflow features such as artifact lineage, variants, model comparison, branch-from-artifact, recipes, export packages, and run snapshots.
- `app/main.py` already includes V10 routers:
  - `artifacts`
  - `comparisons`
  - `export_packages`
  - `project_recipes`
  - `recipes`
  - `run_snapshots`
  - `variants`
- `app/services/utility_tools.py` already defines local utility nodes such as prompt cards, style cards, character cards, asset selector, compare board, variant batch, reroute, note, group frame, and export package.
- `app/services/wavespeed_adapter.py` already has:
  - `run_model(model_id, inputs)` using the WaveSpeed SDK.
  - `upload_file(path)`.
  - `run_llm_chat(model_id, inputs)` for WaveSpeed LLM endpoint.

### Current blockers for full catalog enablement

The current repo still cannot enable all WaveSpeed tools because it is still node-type-first and mostly hand-authored.

1. `app/services/model_catalog.py` still uses a handwritten `CHEAPEST_MODEL_BY_NODE_TYPE` map and a handwritten `MODEL_CATALOG` list.
2. `app/services/registry.py` still uses a handwritten `VERIFIED_FIELDS_BY_NODE_TYPE` map. This is good for curated nodes, but it cannot cover the full catalog.
3. `app/services/node_runner.py` removed the old `SUPPORTED_MODEL_IDS` set, but it still blocks unknown models indirectly through:
   - `node_type_for_model_id()` hardcoded model mapping.
   - `PREPARERS_BY_NODE_TYPE` requiring a runner preparer for each node type.
   - registry lookup through `get_model_for_node(node_type, model_id)`.
4. `app/routers/model_catalog.py` is still node-type-centric:
   - `GET /api/model-catalog`
   - `GET /api/model-catalog/cheapest`
   - `GET /api/model-catalog/{node_type}`
   It does not expose model-ID lookup, capabilities, schema, excluded models, or workbook-derived fields.
5. `app/routers/models.py` returns `[*MODELS, *UTILITY_TOOLS]`, where `MODELS` is still built from the handwritten registry.
6. `app/schemas.py` has a fixed `NodeType` enum. Do not add 1000 new enum values. Use `generic_wavespeed` plus model ID for catalog models outside the curated V9/V10 node types.
7. The uploaded workbook contains the actual catalog scale:
   - `Models_Full`: 1009 model records, range `A1:AF1010`.
   - `API_Schemas`: 1009 schema records, range `A1:J1010`.
   - `Schema_Fields`: 5226 field records, range `A1:S5227`.
   - `Capability_Summary`: 56 capability rows, range `A1:H57`.
   - `Cheapest_By_Capability`: 945 ranked cheapest rows, range `A1:J946`.

---

## Key design rule

Do not try to create one Python node type or preparer per WaveSpeed model.

Use this design instead:

```text
WaveSpeed model ID + normalized schema + generic field resolver + generic output normalizer
```

Keep curated node types for the existing friendly nodes. Use `generic_wavespeed` for the full catalog.

---

## Source workbook

Place the uploaded workbook at:

```text
docs/reference/wavespeed_model_catalog_drilldown.xlsx
```

The workbook sheets to parse are:

```text
README_Summary
Models_Full
Capability_Summary
Raw_Type_Summary
Cheapest_By_Capability
Provider_Summary
API_Schemas
Schema_Fields
```

The importer must primarily use:

```text
Models_Full
API_Schemas
Schema_Fields
Capability_Summary
Cheapest_By_Capability
```

Add to `requirements.txt`:

```text
openpyxl>=3.1.0
```

Use `openpyxl` for the importer. Do not use paid APIs or live WaveSpeed calls during import.

---

## Deliverable 1 — normalized catalog importer

Create:

```text
scripts/import_wavespeed_catalog.py
app/services/catalog_importer.py
app/data/wavespeed_catalog.normalized.json
app/data/model_exclusions.json
```

The script must be runnable as:

```bash
python scripts/import_wavespeed_catalog.py docs/reference/wavespeed_model_catalog_drilldown.xlsx
```

It must generate:

```text
app/data/wavespeed_catalog.normalized.json
```

Each normalized model record should look like this:

```json
{
  "model_id": "wavespeed-ai/z-image/turbo",
  "display_name": "Z Image Turbo",
  "provider": "wavespeed-ai",
  "family": "z-image",
  "slug_leaf": "turbo",
  "raw_type": "text-to-image",
  "primary_capability": "text_to_image",
  "capability_tags": ["text_to_image"],
  "category": "image",
  "output_kind": "image",
  "base_price": 0.005,
  "pricing_basis_guess": "per run",
  "pricing_formula_raw": null,
  "pricing_text_from_description": null,
  "api_path": "/api/v3/wavespeed-ai/z-image/turbo",
  "method": "POST",
  "server": "https://api.wavespeed.ai",
  "schema_type": "model_run",
  "required_fields": ["prompt"],
  "fields": [
    {
      "name": "prompt",
      "type": "textarea",
      "raw_type": "string",
      "required": true,
      "default": null,
      "options": [],
      "asset_kind": null,
      "accept": null,
      "min_value": null,
      "max_value": null,
      "min_items": null,
      "max_items": null,
      "description": ""
    }
  ],
  "supports_prompt": true,
  "supports_negative_prompt": false,
  "supports_image_input": false,
  "supports_video_input": false,
  "supports_audio_input": false,
  "supports_seed": true,
  "supports_prompt_expansion": false,
  "supports_base64_output": true,
  "sort_order": 100,
  "docs_url": "https://wavespeed.ai/models/wavespeed-ai/z-image/turbo",
  "enabled": true,
  "enabled_reason": "Loaded from WaveSpeed catalog workbook",
  "excluded": false,
  "exclusion_reason": ""
}
```

### Field type inference

Map workbook schema fields into these normalized field types:

```text
string
textarea
integer
number
boolean
select
asset_url
asset_url_list
json
file_url
unknown
```

Rules:

- Use `enum_options` from `Schema_Fields` to create `select` options.
- `field_type=boolean` becomes `boolean`.
- integer-like fields become `integer`.
- numeric fields become `number`.
- `prompt`, `negative_prompt`, `style_prompt`, `lyrics`, `text`, `description`, `voice_description`, `instructions`, `query`, and `caption` become `textarea` unless enum options exist.
- `image`, `source_image`, `target_image`, `last_image`, `first_frame`, `reference_image`, `mask`, `mask_image`, `body_image`, `front_image_url`, `back_image_url`, `left_image_url`, `right_image_url` become `asset_url` with `asset_kind="image"`.
- `images`, `source_images`, `target_images`, `reference_images`, `image_urls`, `reference_urls` become `asset_url_list` with `asset_kind="image"`.
- `video`, `source_video`, `target_video`, `video_url`, `input_video` become `asset_url` with `asset_kind="video"`.
- `audio`, `source_audio`, `target_audio`, `audio_url`, `music`, `voice_audio` become `asset_url` with `asset_kind="audio"`, except text-only voice fields like `voice`, `voice_id`, `voice_name`, and `voice_description`.
- `enable_base64_output`, `enable_sync_mode`, `prompt_enhancer`, `enable_prompt_expansion`, `face_enhance`, `bgm`, and similar boolean flags become `boolean`.
- `ui_component=uploader` / `uploaders` and `accept` should override field inference when present.
- Preserve raw field metadata in each normalized record under `raw_schema` if useful.

### Category inference

Map workbook capabilities into these app categories:

```text
image
video
audio
avatar
3d
llm
utility
training
moderation
other
```

Use the workbook `primary_capability`, `capability_tags`, and `raw_type` to determine the category.

---

## Deliverable 2 — schema and data model updates

Modify `app/schemas.py` without breaking existing saved projects.

### Keep these existing structures

- `NodeType` enum.
- Curated V9/V10 node types.
- Utility nodes.
- Existing `Asset`, `CanvasNode`, `Project`, `VariantSet`, `ComparisonSet`, and export/package models.

### Add or extend these models

Add a richer catalog model such as:

```python
class WaveSpeedCatalogField(BaseModel):
    name: str
    type: str
    raw_type: str | None = None
    required: bool = False
    default: Any = None
    options: list[Any] = Field(default_factory=list)
    asset_kind: AssetKind | None = None
    accept: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    min_items: int | None = None
    max_items: int | None = None
    description: str = ""
    disabled: bool = False
```

Add:

```python
class WaveSpeedCatalogModel(BaseModel):
    model_id: str
    display_name: str
    provider: str | None = None
    family: str | None = None
    raw_type: str | None = None
    primary_capability: str
    capability_tags: list[str] = Field(default_factory=list)
    category: str = "other"
    output_kind: AssetKind = AssetKind.other
    base_price: float | None = None
    pricing_basis_guess: str | None = None
    pricing_formula_raw: str | None = None
    api_path: str | None = None
    method: str = "POST"
    server: str | None = None
    schema_type: str | None = None
    required_fields: list[str] = Field(default_factory=list)
    fields: list[WaveSpeedCatalogField] = Field(default_factory=list)
    supports_prompt: bool = False
    supports_negative_prompt: bool = False
    supports_image_input: bool = False
    supports_video_input: bool = False
    supports_audio_input: bool = False
    supports_seed: bool = False
    docs_url: str | None = None
    enabled: bool = True
    enabled_reason: str | None = None
    excluded: bool = False
    exclusion_reason: str = ""
```

Extend `ModelSpec` if needed with:

```python
model_id: str | None = None
primary_capability: str | None = None
capability_tags: list[str] = Field(default_factory=list)
raw_type: str | None = None
source: Literal["curated", "catalog", "utility"] = "curated"
```

Backward compatibility rule:

- Curated models keep their old `node_type`.
- Catalog-scale models use `node_type=NodeType.generic_wavespeed` unless they map cleanly to an existing curated node type.
- Do not add hundreds of `NodeType` enum values.

---

## Deliverable 3 — catalog repository service

Create:

```text
app/services/catalog_repository.py
```

Responsibilities:

```python
list_catalog_models(include_excluded: bool = False) -> list[WaveSpeedCatalogModel]
get_catalog_model(model_id: str) -> WaveSpeedCatalogModel | None
list_capabilities() -> list[dict]
list_models_by_capability(capability: str, include_excluded: bool = False) -> list[WaveSpeedCatalogModel]
list_models_by_category(category: str, include_excluded: bool = False) -> list[WaveSpeedCatalogModel]
get_default_model_for_capability(capability: str) -> WaveSpeedCatalogModel | None
get_cheapest_model_for_capability(capability: str) -> WaveSpeedCatalogModel | None
get_model_fields(model_id: str) -> list[WaveSpeedCatalogField]
```

Load data from:

```text
app/data/wavespeed_catalog.normalized.json
app/data/model_exclusions.json
```

`model_exclusions.json` should have records like:

```json
{
  "model_id": "example/model",
  "excluded": true,
  "reason": "Requires unsupported private setup or unsupported schema field."
}
```

Do not silently drop models. If a model is excluded, keep it visible when `include_excluded=true`.

---

## Deliverable 4 — registry refactor

Modify:

```text
app/services/model_catalog.py
app/services/registry.py
```

Current handwritten catalog entries may remain as curated fallbacks, but the normalized workbook catalog must become the primary source of truth.

### Required registry behavior

- `/api/models` should include:
  - curated friendly models,
  - catalog-derived WaveSpeed models,
  - local utility nodes.
- Every non-excluded normalized workbook model should appear either as:
  - a curated node model if it maps to existing V9/V10 node type, or
  - a `generic_wavespeed` model with `model_id` set to the actual WaveSpeed model ID.
- `get_model(model_id)` must work by exact model ID.
- `get_model_for_node(node_type, model_id)` must still work for existing saved projects.
- Add `get_model_by_id(model_id)` for direct catalog lookup.
- Add `get_models_for_capability(capability)`.
- Add `get_compatible_models(model_or_node, output_kind=None, capability=None)` for V10 comparison/variant features.

Do not make existing projects fail because their node type is one of:

```text
text_to_image
image_to_image
reference_to_image
upscale_image
remove_background
remove_object
image_to_video
start_end_to_video
text_to_video
reference_to_video
video_extend
video_effect
text_to_speech
speech_to_text
generate_voice
lip_sync
talking_avatar
text_to_3d
image_to_3d
llm_text
llm_vision
```

---

## Deliverable 5 — model catalog API upgrade

Modify:

```text
app/routers/model_catalog.py
```

Keep the old endpoints for compatibility, but add these:

```text
GET /api/model-catalog?include_excluded=false&category=&capability=&q=&limit=&offset=
GET /api/model-catalog/summary
GET /api/model-catalog/capabilities
GET /api/model-catalog/capabilities/{capability}
GET /api/model-catalog/models/{model_id:path}
GET /api/model-catalog/models/{model_id:path}/schema
GET /api/model-catalog/categories/{category}
GET /api/model-catalog/cheapest-by-capability
GET /api/model-catalog/excluded
```

Return model IDs exactly as WaveSpeed expects, including slashes.

`/api/model-catalog/models/{model_id:path}` must support model IDs like:

```text
alibaba/happyhorse-1.0/text-to-video
wavespeed-ai/z-image/turbo
openai/gpt-5-nano
```

---

## Deliverable 6 — generic input resolver

Create:

```text
app/services/model_input_resolver.py
```

This replaces one-off preparers for catalog-scale models.

Required API:

```python
async def prepare_model_inputs(
    *,
    adapter: WaveSpeedAdapter,
    model: WaveSpeedCatalogModel | ModelSpec,
    inputs: dict[str, Any],
    project: Project | None,
) -> dict[str, Any]:
    ...
```

Features:

- Validate required fields before calling WaveSpeed.
- Convert booleans, integers, numbers, selects, and JSON.
- Resolve `asset_url` fields from:
  - project asset ID,
  - asset `wavespeed_url`,
  - asset `public_url`,
  - asset `local_path`, uploaded via `adapter.upload_file`,
  - external HTTPS URL,
  - existing local file path.
- Reject localhost/private-network URLs unless they map to a saved local file path that can be uploaded.
- Support `asset_url_list` from:
  - list values,
  - comma-separated string,
  - newline-separated string,
  - project asset IDs.
- Enforce `asset_kind` when known.
- Add default `enable_base64_output=false` unless the user explicitly sets it.
- Add default `enable_sync_mode=false` unless the user explicitly sets it.
- Drop optional empty values.
- Preserve non-empty unknown fields as strings only when the field is not required.
- Fail fast with a clear message for unsupported required field types.

Keep existing hand-tuned preparers for curated nodes only when they are safer than the generic resolver.

---

## Deliverable 7 — generic output normalizer

Create:

```text
app/services/model_output_normalizer.py
```

Required API:

```python
def normalize_model_output(
    *,
    model: WaveSpeedCatalogModel | ModelSpec,
    model_id: str,
    raw_output: dict[str, Any],
    target_node: CanvasNode | None = None,
) -> tuple[list[str], list[Asset], str | None, dict[str, Any]]:
    ...
```

It must support:

- URL outputs:
  - `outputs`
  - `output`
  - `data.outputs`
  - `data.output`
  - nested `url`, `uri`, `file`, `image`, `video`, `audio`.
- Text outputs:
  - `text`
  - `transcript`
  - `transcription`
  - `data.text`
  - LLM `choices[].message.content`.
- Structured JSON-only output.

Asset kind inference:

- Use catalog `output_kind` first.
- If output kind is `other`, infer from URL suffix:
  - image: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`
  - video: `.mp4`, `.mov`, `.webm`, `.mkv`
  - audio: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`
  - 3D/other: `.glb`, `.gltf`, `.obj`, `.fbx`, `.stl`, `.usdz`, `.zip`

For text-only outputs, do not fail just because no URL exists. Store text in:

```text
node.last_run.text_output
node.last_run.structured_output
```

For JSON-only outputs, store:

```text
node.last_run.structured_output
```

---

## Deliverable 8 — node runner refactor

Modify:

```text
app/services/node_runner.py
app/routers/runs.py
app/services/run_manager.py
```

Current repo already removed `SUPPORTED_MODEL_IDS`, but still has hardcoded `node_type_for_model_id()` and `PREPARERS_BY_NODE_TYPE` limitations.

Required changes:

- `run_wavespeed_node()` should resolve the model by exact `model_id` first.
- If `node_type == generic_wavespeed`, use catalog model schema and generic resolver.
- If the model maps to a curated node type and has a tuned preparer, that preparer may be used.
- Unknown but normalized catalog models must run through `model_input_resolver.prepare_model_inputs()`.
- Remove or soften `node_type_for_model_id()` so it does not block catalog models.
- Keep `DENYLISTED_MODEL_IDS`, but populate it from `model_exclusions.json` instead of code.
- Use `model_output_normalizer.normalize_model_output()` for all models.
- Preserve V10 artifact lineage in created assets.
- Run snapshots must store:
  - `model_id`
  - `primary_capability`
  - `category`
  - `input_summary`
  - `raw_output`
  - `text_output`
  - `structured_output`
  - `output_urls`
  - `asset_ids`

Do not break existing direct calls such as:

```json
{
  "node_type": "text_to_image",
  "model_id": "wavespeed-ai/z-image/turbo",
  "inputs": {"prompt": "..."},
  "save_to_project": false
}
```

Add support for direct generic calls:

```json
{
  "node_type": "generic_wavespeed",
  "model_id": "alibaba/happyhorse-1.0/text-to-video",
  "inputs": {"prompt": "...", "duration": 5, "resolution": "720p"},
  "save_to_project": false
}
```

---

## Deliverable 9 — V10 workflow integration

V10 model comparison and variants must become model-ID/capability aware.

Modify as needed:

```text
app/services/model_compare.py
app/services/variant_runner.py
app/services/recipes.py
app/services/project_recipes.py
app/services/artifact_service.py
app/services/run_snapshots.py
```

Rules:

- Model comparison should allow comparing any enabled model with compatible:
  - `output_kind`, and/or
  - `primary_capability`, and/or
  - compatible required input fields.
- Do not only compare models with the same old `NodeType`.
- Variant generation should work for generic catalog nodes.
- Recipe creation should select models by capability using `get_default_model_for_capability()` or `get_cheapest_model_for_capability()`.
- Artifact branch should suggest target models by accepted input kind and capability, not only old node type.
- Export packages and lineage must keep working for catalog model outputs.

---

## Deliverable 10 — frontend functional changes only

Modify:

```text
web/app.js
web/index.html
web/style.css
```

Do not spend effort on visual redesign. Minimal functional changes only.

Required behavior:

1. Model browser / selector
   - Search by model ID, provider, capability, raw type, category.
   - Filter by category and capability.
   - Show enabled/excluded status.
   - Show base price and pricing basis when known.

2. Add generic catalog node
   - User can choose a model from the catalog.
   - Node is created with:

```json
{
  "type": "generic_wavespeed",
  "model_id": "actual/provider/model-id"
}
```

3. Existing curated nodes still work.

4. `modelResolution(node)` must prefer exact `node.model_id` lookup across all models before filtering by `node.type`.

5. `renderNodeFields()` must use the selected model schema for generic catalog nodes.

6. Field renderer must support:

```text
string -> input
textarea -> textarea
integer -> number input step 1
number -> number input
boolean -> checkbox
select -> select
asset_url -> kind-aware asset picker + manual URL input
asset_url_list -> multi-select or newline textarea
json -> textarea with JSON validation
file_url -> asset picker / URL input
unknown -> text input with warning
```

7. Asset pickers must filter by `asset_kind`:
   - image fields show image assets
   - video fields show video assets
   - audio fields show audio assets
   - other/generic fields show all assets

8. Output preview must show:
   - image/video/audio assets as today,
   - text output from `last_run.text_output`,
   - JSON output from `last_run.structured_output`.

9. Node library must not render 1000+ models as a long unfiltered list by default. Use category/capability/search and pagination or collapsed groups.

---

## Deliverable 11 — cost guard integration

Modify:

```text
app/services/cost_estimator.py
```

Use workbook fields:

```text
base_price
pricing_basis_guess
pricing_formula_raw
pricing_text_from_description
```

Do not try to evaluate every formula in V11.

Required behavior:

- Use `base_price` as starting estimate when known.
- Preserve existing local cost guard behavior.
- If `pricing_formula_raw` mentions duration, seconds, video length, audio length, resolution, or number of outputs, show an estimate warning.
- If cost is unknown, keep current unknown-cost guard behavior.
- Include `pricing_basis_guess` and `pricing_formula_raw` in model details and run snapshots.

---

## Deliverable 12 — tests

Add or update tests. Use mocked WaveSpeed calls. Do not call paid APIs in unit tests.

Required tests:

```text
tests/test_catalog_importer.py
tests/test_catalog_repository.py
tests/test_registry_catalog_scaleout.py
tests/test_model_input_resolver.py
tests/test_model_output_normalizer.py
tests/test_generic_wavespeed_runner.py
tests/test_model_catalog_api.py
tests/test_v10_catalog_integration.py
```

Test cases:

- Importer reads workbook and produces at least 900 normalized model records.
- Importer reads at least 5000 schema field records.
- Every non-excluded enabled model has:
  - `model_id`
  - `primary_capability`
  - `category`
  - `output_kind`
  - `fields`
- Required fields are present in normalized fields.
- Enum fields become select options.
- Image/audio/video fields become asset fields with correct `asset_kind`.
- `asset_url_list` handles list/comma/newline inputs.
- Local asset paths are uploaded through mocked `adapter.upload_file()`.
- Localhost/private URLs are rejected.
- Text-only outputs do not fail.
- Nested URL outputs become project assets.
- `/api/model-catalog/models/{model_id:path}` works for model IDs with slashes.
- `/api/models?enabled_only=true` includes utility models and catalog models.
- `generic_wavespeed` run calls WaveSpeed with exact selected model ID.
- Old curated node runs still pass.
- V10 comparison can compare catalog models with compatible capabilities.
- V10 variants can clone and run a generic catalog node.

---

## Deliverable 13 — docs

Update:

```text
README.md
CODEX_TASKS.md
requirements.md
docs/V9_MODEL_ENABLEMENT.md
docs/V10_WEAVE_PARITY_MAP.md
```

Add:

```text
docs/WAVESPEED_CATALOG_IMPORT.md
docs/WAVESPEED_CATALOG_RUNTIME.md
docs/MODEL_EXCLUSIONS.md
docs/V11_CATALOG_SCALEOUT.md
```

Fix the current documentation mismatch:

- `docs/V9_MODEL_ENABLEMENT.md` still says some nodes are disabled, but the latest `model_catalog.py` marks many of those nodes enabled. Update the doc to match reality.

Docs must explain:

- where the workbook goes,
- how to regenerate normalized JSON,
- how exclusions work,
- how model ID lookup works,
- how to run a generic catalog model,
- how to add custom overrides for weird schemas,
- how to run tests,
- how to run live smoke tests without accidental credit spend.

---

## Manual verification checklist

Run:

```bash
python scripts/import_wavespeed_catalog.py docs/reference/wavespeed_model_catalog_drilldown.xlsx
python -m pytest
python -m uvicorn app.main:app --reload --port 8000
```

Check:

```text
GET /api/health
GET /api/models?enabled_only=true
GET /api/model-catalog/summary
GET /api/model-catalog/capabilities
GET /api/model-catalog/capabilities/text_to_image
GET /api/model-catalog/capabilities/image_to_video
GET /api/model-catalog/models/wavespeed-ai/z-image/turbo
GET /api/model-catalog/models/alibaba/happyhorse-1.0/text-to-video
GET /api/model-catalog/models/akool/video-face-swap/schema
GET /api/model-catalog/excluded
```

Direct run smoke with mocked or real key:

```bash
curl -X POST http://localhost:8000/api/runs/node \
  -H "Content-Type: application/json" \
  -d '{
    "node_type": "generic_wavespeed",
    "model_id": "alibaba/happyhorse-1.0/text-to-video",
    "inputs": {
      "prompt": "A clean product reveal on a studio table",
      "duration": 5,
      "resolution": "720p",
      "seed": -1
    },
    "save_to_project": false
  }'
```

Asset input smoke:

```bash
curl -X POST "http://localhost:8000/api/assets/upload?upload_to_wavespeed=true" \
  -F "file=@sample.mp4"
```

Then run a catalog model that needs `video` or `audio` using the returned asset ID or WaveSpeed URL.

---

## Acceptance criteria

- The workbook imports successfully into normalized JSON.
- At least 900 WaveSpeed catalog models are visible through `/api/model-catalog`.
- At least 900 model schemas are available through model-ID endpoints.
- `/api/models` includes catalog-derived models plus local utility tools.
- No giant handwritten Python list of 1000 models is added.
- Existing V9 curated models still run.
- Existing V10 workflow endpoints still run.
- Generic `generic_wavespeed` nodes can run non-curated catalog models through the WaveSpeed model ID and schema.
- Text-only and JSON-only outputs are handled without failure.
- Catalog model comparison and variants work for generic catalog nodes.
- Excluded models are visible with reasons when requested.
- Unit tests do not spend WaveSpeed credits.

---

## Codex execution note

This is not a UI redesign task. Do the backend/model architecture first, then minimal frontend support for choosing and rendering catalog models.

Do not delete the existing V9/V10 code paths. Convert them into the curated compatibility layer on top of the new catalog-driven runtime.
