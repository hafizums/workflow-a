# TASK_V10.md — Weave-Style Functional Parity, WaveSpeed-Only

## Mission

Build v10 as the first **Weave-style production workflow layer** for `workflow-a`.

Assume `TASK_V9_MODEL_ENABLEMENT.md` is complete. That means the app now has:

- A registry-driven WaveSpeed model/tool manifest.
- Generic input preparation from model specs.
- Generic project asset resolution for image, video, audio, text/file, and 3D-like outputs.
- More WaveSpeed models enabled and runnable.
- Tests proving enabled models have fields, preparers, and normalized outputs.

V10 must stop treating the app as a simple node runner and start turning it into a **creative operating system**: users can explore, branch, compare, choose winners, preserve lineage, and package results — using only WaveSpeed.ai model APIs plus local orchestration utilities.

## Product intent

The long-term product target is to replicate the **functional workflow value** of Figma Weave / Weavy:

- AI models and editing tools live together on one canvas.
- Outputs can be branched, remixed, refined, and reused.
- One idea can fan out into multiple model runs or variations.
- Users can compare results side-by-side and promote the best one.
- Workflows are visible, repeatable, and exportable.

Do **not** copy Figma, Weave, or Weavy branding, exact UI, icons, names, trade dress, marketing copy, or proprietary interaction details. Build equivalent workflow capabilities under this app’s own identity.

## Product law: WaveSpeed-only execution

All AI generation/transformation/transcription capabilities must use WaveSpeed.ai model APIs only.

Allowed:

- WaveSpeed model runs.
- Local utility nodes: prompt, note, group, reroute, selector, compare, variant batch, asset input, export package, style guide, character/reference card.
- Local project persistence, run history, lineage metadata, compatibility checks, cost estimates, snapshots, and templates.

Not allowed:

- Direct calls to OpenAI, Anthropic, Google, Runway, Replicate, Fal, Figma, Weave, Weavy, or any other non-WaveSpeed model API.
- Adding non-WaveSpeed model SDKs.
- Runtime scraping of WaveSpeed pages.
- Copying Figma/Weave visual identity.
- Building a Photoshop/Figma-class editor before the workflow engine is mature.

## V10 outcome

At the end of v10, a user should be able to create workflows like:

```text
Product idea prompt
  -> 4 image variations
  -> compare grid
  -> choose winner
  -> remove background
  -> upscale
  -> animate selected image
  -> generate voiceover
  -> lip-sync/avatar video
  -> export final bundle
```

And:

```text
Audio upload
  -> speech-to-text
  -> edit transcript as text artifact
  -> voice design / TTS
  -> image/avatar to video
  -> compare multiple takes
  -> package outputs
```

And:

```text
Text prompt
  -> text-to-video variants
  -> choose best clip
  -> extend / enhance / branch if enabled by v9 manifest
  -> export project package with lineage
```

---

## Current baseline after V9

Treat these as true for v10 planning:

1. Enabled WaveSpeed tools run through a manifest/capability system.
2. Disabled tools remain visible only as unavailable candidates.
3. Normalized artifacts can represent URL outputs, text outputs, JSON/timestamp outputs, audio, video, image, and 3D/file outputs.
4. The app still uses local JSON storage under `data/projects`.
5. The app still uses FastAPI + vanilla frontend.
6. The local Run Manager already supports queueing, cancellation requests, retry, and workflow jobs.

V10 should build on these; do not redo v9 model enablement unless tests expose a regression.

---

# Phase 0 — Weave parity map and product guardrails

Create:

```text
docs/V10_WEAVE_PARITY_MAP.md
```

Include a feature parity map with these columns:

```text
Capability | Why it matters | V10 implementation | Uses WaveSpeed? | Status
```

Minimum rows:

- Tool/model nodes.
- Utility nodes.
- Branch from output.
- Fan-out variants.
- Multi-model compare.
- Seed/prompt variation compare.
- Pick winner / promote artifact.
- Artifact lineage.
- Prompt/style cards.
- Character/reference cards.
- Workflow recipes.
- Export bundle.
- Run snapshots.
- Cost snapshot.
- Reusable project templates.

Add a product guardrail section:

```text
We replicate workflow functionality, not Figma/Weave branding or proprietary UI.
All executable AI tools must be WaveSpeed-only.
```

Acceptance:

- The doc exists.
- The doc clearly defines what v10 will and will not replicate.
- Every planned executable capability maps to an enabled WaveSpeed model or a local utility node.

---

# Phase 1 — First-class artifacts and lineage

The current project model already has assets and runs. V10 needs stronger lineage so every artifact knows how it was produced and how it was used.

## 1.1 Extend project schema

Edit `app/schemas.py` without breaking old project JSON.

Add or extend models:

```python
class ArtifactRole(str, Enum):
    input = "input"
    output = "output"
    intermediate = "intermediate"
    winner = "winner"
    reference = "reference"
    export = "export"

class ArtifactLineage(BaseModel):
    source_project_id: str | None = None
    source_node_id: str | None = None
    source_run_id: str | None = None
    source_job_id: str | None = None
    source_model_id: str | None = None
    source_artifact_ids: list[str] = Field(default_factory=list)
    source_input_keys: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "system"

class ArtifactVersion(BaseModel):
    id: str = Field(default_factory=lambda: new_id("version"))
    artifact_id: str
    created_at: datetime = Field(default_factory=utc_now)
    url: str | None = None
    text: str | None = None
    json_value: dict[str, Any] | list[Any] | None = None
    filename: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class ArtifactViewState(BaseModel):
    pinned: bool = False
    role: ArtifactRole = ArtifactRole.intermediate
    label: str = ""
    notes: str = ""
    rating: int | None = None
    rejected: bool = False
    favorite: bool = False
```

Extend `Asset` safely:

```python
lineage: ArtifactLineage = Field(default_factory=ArtifactLineage)
view: ArtifactViewState = Field(default_factory=ArtifactViewState)
versions: list[ArtifactVersion] = Field(default_factory=list)
```

Rules:

- Existing projects with old assets must load.
- Generated outputs must set `lineage.source_node_id`, `lineage.source_run_id` or `source_job_id`, and `lineage.source_model_id`.
- Assets created by local upload should use `role=input` or `role=reference`.
- Assets chosen as final winners should use `role=winner`.

## 1.2 Add artifact service

Create:

```text
app/services/artifact_service.py
```

Functions:

```python
def get_artifact(project: Project, asset_id: str) -> Asset: ...
def list_artifacts(project: Project, kind: AssetKind | None = None, role: ArtifactRole | None = None) -> list[Asset]: ...
def set_artifact_role(project: Project, asset_id: str, role: ArtifactRole) -> Asset: ...
def pin_artifact(project: Project, asset_id: str, pinned: bool = True) -> Asset: ...
def reject_artifact(project: Project, asset_id: str, rejected: bool = True) -> Asset: ...
def rate_artifact(project: Project, asset_id: str, rating: int | None) -> Asset: ...
def artifact_lineage_tree(project: Project, asset_id: str) -> dict[str, Any]: ...
```

## 1.3 Add artifact API

Create:

```text
app/routers/artifacts.py
```

Register it in `app/main.py`.

Endpoints:

```text
GET    /api/projects/{project_id}/artifacts
GET    /api/projects/{project_id}/artifacts/{asset_id}
GET    /api/projects/{project_id}/artifacts/{asset_id}/lineage
POST   /api/projects/{project_id}/artifacts/{asset_id}/pin
POST   /api/projects/{project_id}/artifacts/{asset_id}/unpin
POST   /api/projects/{project_id}/artifacts/{asset_id}/reject
POST   /api/projects/{project_id}/artifacts/{asset_id}/restore
POST   /api/projects/{project_id}/artifacts/{asset_id}/role
POST   /api/projects/{project_id}/artifacts/{asset_id}/rating
```

Request examples:

```json
{ "role": "winner" }
```

```json
{ "rating": 5 }
```

Acceptance:

- A generated output can be pinned, rated, rejected, restored, and marked winner.
- Lineage tree returns upstream nodes/assets where known.
- Project export/import preserves artifact metadata.
- Old projects still load.

---

# Phase 2 — Utility nodes for Weave-like orchestration

V10 must add non-model nodes that make the canvas feel like a production workspace, not just a model list.

## 2.1 Add utility node types

Extend `NodeType` or add a parallel utility type system that remains backward compatible.

Required local utility nodes:

```text
prompt_card          Text prompt block reusable by model nodes.
style_card           Reusable style/brand/camera/mood rules.
character_card       Reusable character/product/reference description.
asset_input          Select one existing project artifact as a graph input.
asset_selector       Select one artifact from a set of upstream outputs.
compare_board        Collect outputs for side-by-side comparison.
variant_batch        Generate parameter variations for a downstream model node.
reroute              Graph organization node; passes through artifacts or values.
note                 Non-executable canvas note.
group_frame          Canvas grouping/frame metadata.
export_package       Defines final deliverables to export.
```

Rules:

- Utility nodes do not call WaveSpeed.
- Utility nodes can emit text, json, or artifact references into downstream model inputs.
- Utility nodes must participate in workflow resolution.
- Utility nodes must not break existing topological execution.

## 2.2 Add utility model specs

Expose utility nodes through `/api/models` or a new `/api/tools` endpoint.

Create:

```text
app/services/utility_tools.py
```

Each utility tool should have:

```python
id
label
node_type
category="utility"
output_kind
fields
enabled=True
runnable=False or local_runnable=True
```

## 2.3 Workflow resolver support

Edit workflow planning/resolution logic so utility nodes can transform values:

- `prompt_card.output` -> text value.
- `style_card.output` -> text value appended or mapped into prompt/style fields.
- `character_card.output` -> structured JSON and text description.
- `asset_input.output` -> selected asset id / URL.
- `asset_selector.output` -> selected upstream artifact id.
- `variant_batch.output` -> list of parameter sets.
- `compare_board` -> does not run model; collects references.
- `export_package` -> collects final selected artifacts.

Acceptance:

- A text-to-image node can receive its prompt from a `prompt_card`.
- An image-to-video node can receive its image from an `asset_selector` or `asset_input`.
- A `compare_board` can collect outputs from at least two upstream nodes.
- Utility nodes are saved in project JSON and survive export/import.

---

# Phase 3 — Variant and fan-out engine

Weave-like tools are valuable because users can explore many options quickly. Add first-class variant sets.

## 3.1 Add variant schemas

Edit `app/schemas.py`:

```python
class VariantParameter(BaseModel):
    field: str
    values: list[Any] = Field(default_factory=list)
    strategy: Literal["list", "range", "seed", "prompt_suffix", "prompt_template"] = "list"

class VariantRunRequest(BaseModel):
    project_id: str
    node_id: str
    variant_count: int = 4
    parameters: list[VariantParameter] = Field(default_factory=list)
    save_to_project: bool = True
    label: str = ""

class VariantSet(BaseModel):
    id: str = Field(default_factory=lambda: new_id("variant"))
    project_id: str
    source_node_id: str
    label: str = ""
    status: str = "queued"
    job_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    parameters: list[VariantParameter] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

Store variant sets in project JSON or a local `data/variant_sets` store. Prefer project JSON for portability.

## 3.2 Add variant runner service

Create:

```text
app/services/variant_runner.py
```

Functions:

```python
def build_variant_payloads(node: CanvasNode, request: VariantRunRequest) -> list[dict[str, Any]]: ...
async def queue_variant_set(project: Project, request: VariantRunRequest) -> VariantSet: ...
def attach_variant_result(project: Project, variant_set_id: str, job_id: str, artifact_ids: list[str]) -> None: ...
```

Variant strategies:

- `seed`: generate `variant_count` different seeds.
- `prompt_suffix`: append each value to the prompt.
- `prompt_template`: render simple `{variable}` replacements.
- `list`: one run per provided value.
- `range`: numeric range where safe.

## 3.3 Add API

```text
POST /api/projects/{project_id}/nodes/{node_id}/variants
GET  /api/projects/{project_id}/variants
GET  /api/projects/{project_id}/variants/{variant_set_id}
POST /api/projects/{project_id}/variants/{variant_set_id}/promote/{asset_id}
```

Rules:

- Use the existing Run Manager queue, not blocking HTTP calls.
- Variant jobs should share a `variant_set_id` in metadata.
- Cost guard must evaluate total estimated variant cost before enqueue.
- User can cancel a variant set; cancel all queued/running jobs where possible.

Acceptance:

- A user can generate 4 image variants from one prompt node.
- A user can generate 4 video variants from one text-to-video node.
- Variant output artifacts are grouped and visible through API.
- A user can promote one variant as winner.
- Failed variants do not fail the entire set; the set records partial success.

---

# Phase 4 — Multi-model compare engine

After V9, the app should have multiple enabled WaveSpeed models over time. V10 must support comparing compatible models without changing the graph manually.

## 4.1 Add comparison schemas

```python
class ModelCompareRequest(BaseModel):
    project_id: str
    source_node_id: str
    model_ids: list[str] = Field(default_factory=list)
    output_kind: AssetKind | None = None
    label: str = ""
    save_to_project: bool = True

class ComparisonSet(BaseModel):
    id: str = Field(default_factory=lambda: new_id("compare"))
    project_id: str
    source_node_id: str
    label: str = ""
    model_ids: list[str] = Field(default_factory=list)
    job_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    winner_asset_id: str | None = None
    status: str = "queued"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

## 4.2 Add compatibility logic

Create:

```text
app/services/tool_compatibility.py
```

Functions:

```python
def compatible_models_for_node(source_node: CanvasNode, all_models: list[ModelSpec]) -> list[ModelSpec]: ...
def can_compare_models(models: list[ModelSpec]) -> tuple[bool, str]: ...
def can_connect_output_to_input(source_output_kind, target_input_spec) -> tuple[bool, str]: ...
```

Rules:

- Models are comparable if they share equivalent required inputs and output kind.
- If inputs differ, the compare endpoint must explain the mismatch.
- Compare should be mostly for models within the same capability tag, but allow advanced override if inputs are compatible.

## 4.3 Add compare API

```text
POST /api/projects/{project_id}/nodes/{node_id}/compare-models
GET  /api/projects/{project_id}/comparisons
GET  /api/projects/{project_id}/comparisons/{comparison_id}
POST /api/projects/{project_id}/comparisons/{comparison_id}/winner/{asset_id}
```

Acceptance:

- If two compatible image generation models are enabled, one source prompt can run both and group outputs.
- If only one model is enabled for a capability, the endpoint returns a helpful message and suggests variant runs instead.
- Comparison result records all model IDs, job IDs, artifacts, status, and chosen winner.

---

# Phase 5 — Winner promotion and branch-from-any-output

Branching should not only work from the latest node output. It must work from any artifact.

## 5.1 Add branch service

Create:

```text
app/services/branching.py
```

Functions:

```python
def create_branch_from_artifact(
    project: Project,
    artifact_id: str,
    target_node_type: NodeType,
    target_input_name: str | None = None,
    title: str | None = None,
) -> tuple[CanvasNode, CanvasEdge]: ...
```

Rules:

- Pick a compatible target input automatically when possible.
- If more than one compatible input exists, require `target_input_name`.
- Preserve lineage from source artifact.
- New child node should be placed near source node if coordinates exist.
- Source artifact should be recorded in child node inputs by asset id, not local URL.

## 5.2 Add API

```text
POST /api/projects/{project_id}/artifacts/{asset_id}/branch
```

Request:

```json
{
  "target_node_type": "image_to_video",
  "target_input_name": "image",
  "title": "Animate winner"
}
```

Acceptance:

- Branch image artifact -> image_to_video.
- Branch video artifact -> lip_sync or video_extend if enabled and compatible.
- Branch audio artifact -> speech_to_text or lip_sync/talking_avatar if enabled and compatible.
- Branch text artifact -> text_to_image, text_to_video, text_to_speech, or text_to_3d if enabled and compatible.
- Incompatible branch requests return clear errors.

---

# Phase 6 — Prompt, style, character, and reference system

Weave-style workflows rely on reusable creative intent. Add local reusable cards that can feed model inputs.

## 6.1 Prompt cards

A prompt card stores:

```python
text
negative_prompt
variables: dict[str, str]
tags
```

It can connect to:

- `prompt`
- `text`
- `style_instruction`
- `voice_description`
- any field tagged as prompt-like in the model manifest

## 6.2 Style cards

A style card stores:

```python
style_name
visual_style
camera
lighting
color_palette
mood
quality_rules
negative_rules
```

It can be appended to prompt fields through workflow resolution.

## 6.3 Character/reference cards

A character card stores:

```python
name
description
appearance
voice_description
reference_asset_ids
consistency_notes
```

It can feed:

- image prompts
- video prompts
- voice design fields
- avatar/talking-head nodes
- reference image fields when compatible

Acceptance:

- A prompt card plus style card can resolve into a text-to-image prompt.
- A character card can feed both visual prompt and voice description fields.
- These cards are local utilities and do not call non-WaveSpeed APIs.

---

# Phase 7 — Workflow recipes and production templates

The existing template system is project-level. V10 needs production-ready recipes that create useful WaveSpeed-only graphs.

## 7.1 Add recipe schema

```python
class WorkflowRecipe(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = "workflow"
    tags: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    optional_capabilities: list[str] = Field(default_factory=list)
    nodes: list[CanvasNode] = Field(default_factory=list)
    edges: list[CanvasEdge] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
```

Create:

```text
app/services/recipe_store.py
app/routers/recipes.py
```

Endpoints:

```text
GET  /api/recipes
GET  /api/recipes/{recipe_id}
POST /api/recipes/{recipe_id}/create-project
POST /api/projects/{project_id}/apply-recipe/{recipe_id}
```

## 7.2 Built-in recipes

Add at least these built-in recipes:

### Product Ad Image to Video

```text
Upload/Product image
-> Remove Background
-> Image Remix or Text-to-Image scene
-> Compare Board
-> Upscale Winner
-> Image-to-Video
-> Export Package
```

### UGC Avatar Clip

```text
Prompt Card / Script
-> Voice Design or Text-to-Speech
-> Upload Portrait/Image
-> Talking Avatar or Lip Sync
-> Compare Board
-> Export Package
```

### Storyboard Shot Explorer

```text
Prompt Card
-> Text-to-Image variants
-> Compare Board
-> Pick Winner
-> Image-to-Video variants
-> Export Package
```

### Video Voiceover / Dubbing

```text
Upload Video
-> Upload Audio or TTS
-> Lip Sync if compatible
-> Compare Board
-> Export Package
```

### Audio Transcript to Creative Assets

```text
Upload Audio
-> Speech-to-Text
-> Prompt Card from transcript
-> Text-to-Image or Text-to-Video
-> Export Package
```

### 3D Asset Ideation

```text
Prompt Card
-> Text-to-3D
-> Compare Board
-> Export Package
```

Rules:

- A recipe must check enabled capabilities before creating nodes.
- If a capability is unavailable, recipe creation should insert a disabled placeholder node with a clear note.
- Recipe graph must be useful immediately after creation.

Acceptance:

- User can create a new project from each recipe.
- Recipe creation does not crash when optional capabilities are unavailable.
- Recipes use only enabled WaveSpeed models and local utility nodes.

---

# Phase 8 — Export package and deliverable manifest

V10 should make final outputs portable and understandable.

## 8.1 Export package node

The `export_package` utility node collects chosen artifacts and produces a local manifest.

Manifest shape:

```json
{
  "schema": "wavespeed_canvas_export_package",
  "version": 1,
  "project_id": "project_...",
  "created_at": "...",
  "artifacts": [
    {
      "asset_id": "asset_...",
      "role": "winner",
      "kind": "video",
      "filename": "...",
      "url": "...",
      "source_node_id": "node_...",
      "source_model_id": "wavespeed-ai/...",
      "lineage": {}
    }
  ]
}
```

## 8.2 API

```text
POST /api/projects/{project_id}/export-package
GET  /api/projects/{project_id}/export-package/{package_id}
```

For local MVP, it is acceptable to produce a JSON manifest rather than physically downloading remote URLs.

Acceptance:

- Export package includes selected winner artifacts.
- Export package includes lineage and model IDs.
- Export package can be regenerated after new winners are selected.
- Project export still works separately.

---

# Phase 9 — Run snapshots and reproducibility

Every run should be reproducible as much as WaveSpeed allows.

## 9.1 Add run snapshot metadata

For every node run, variant run, and compare run, persist:

```text
project_id
node_id
job_id
run_id
model_id
model_display_name
model_version if available
input_snapshot
resolved_input_snapshot
output_artifact_ids
raw_output_summary
estimated_cost_snapshot
started_at
finished_at
status
error/warnings
```

Avoid storing giant raw output blobs inside every asset if they become too large. Use summary plus raw output reference if needed.

## 9.2 Add rerun support

API:

```text
POST /api/projects/{project_id}/runs/{run_id}/rerun
POST /api/projects/{project_id}/runs/{run_id}/clone-node
```

Rules:

- Rerun uses the same model and input snapshot unless the model is disabled/unavailable.
- Clone node creates a new node with the same inputs/model settings.
- Cost guard must apply again.

Acceptance:

- A successful run can be rerun.
- A failed run can be cloned for editing.
- Run snapshots survive project reload/export/import.

---

# Phase 10 — Minimal frontend glue, not a redesign

Do not redesign the UI in v10. Add only the minimum UI hooks needed to access functionality.

Required frontend hooks in `web/app.js` / `web/index.html` / `web/style.css`:

- Artifact actions: Pin, Winner, Reject, Branch.
- Node actions: Run Variants, Compare Models when available.
- Recipe panel: Create Project from Recipe, Apply Recipe.
- Compare board rendering: show grouped artifact cards and winner button.
- Variant set rendering: show grouped outputs and partial failures.
- Lineage view: simple expandable text/tree panel.
- Export package action.

Rules:

- Preserve existing DOM IDs and existing workflow actions.
- No React migration.
- No major CSS rewrite.
- UI can be plain but must be usable.

Acceptance:

- The new endpoints can be exercised from the browser without manual curl.
- Existing v8/v9 UI still works.

---

# Phase 11 — Tests and quality gates

Add tests under `tests/`.

Required test files:

```text
tests/test_v10_artifact_lineage.py
tests/test_v10_utility_nodes.py
tests/test_v10_variants.py
tests/test_v10_compare.py
tests/test_v10_branching.py
tests/test_v10_recipes.py
tests/test_v10_export_package.py
tests/test_v10_wavespeed_only_guard.py
```

## Required tests

### Artifact lineage

- Generated artifact includes source node/model/run metadata.
- Pinned/winner/rejected metadata persists.
- Lineage tree returns upstream asset/node references.

### Utility nodes

- Prompt card resolves into prompt input.
- Asset input resolves into selected artifact id.
- Compare board collects upstream artifacts without calling WaveSpeed.

### Variants

- Seed variant request creates N run payloads.
- Prompt suffix variant request modifies prompt safely.
- Variant cost guard evaluates total cost.
- Partial failures are recorded.

### Compare

- Compatible models can be compared.
- Incompatible models return clear mismatch errors.
- Winner selection persists.

### Branching

- Image artifact branches to image-to-video.
- Audio artifact branches to speech-to-text or avatar/lip-sync if available.
- Text artifact branches to prompt-like models.
- Incompatible branches fail clearly.

### Recipes

- Built-in recipes load.
- Recipe creates valid project graph.
- Recipe gracefully handles unavailable optional capabilities.

### Export package

- Export package includes winner artifacts and lineage.
- Export package uses stable schema/version.

### WaveSpeed-only guard

- No new non-WaveSpeed model API client imports are added.
- No route calls non-WaveSpeed AI APIs.
- Utility nodes are local-only.

Suggested guard:

```python
FORBIDDEN_IMPORTS = [
    "openai",
    "anthropic",
    "google.generativeai",
    "replicate",
    "fal_client",
    "runwayml",
]
```

It is acceptable to use test-time string scanning for this guard.

---

# Manual acceptance workflows

Run these manually after tests pass.

## Workflow 1 — Product ad pipeline

1. Create project from Product Ad recipe.
2. Upload product image.
3. Remove background.
4. Generate or remix 4 image variants.
5. Pick one winner.
6. Upscale winner.
7. Animate winner.
8. Export package.

Expected:

- All outputs are grouped by lineage.
- Winner is visible in artifacts.
- Export package includes final image/video and source model IDs.

## Workflow 2 — Storyboard explorer

1. Create project from Storyboard recipe.
2. Fill prompt card.
3. Run image variants.
4. Pick 2 favorite frames.
5. Run image-to-video variants from each frame.
6. Compare videos.
7. Mark winner.

Expected:

- Variant sets and comparison sets are saved.
- Branches are visible and reproducible.

## Workflow 3 — Voice/avatar

1. Create project from UGC Avatar recipe.
2. Add script prompt card.
3. Generate voice with TTS or voice design.
4. Upload portrait/image.
5. Run talking avatar or lip-sync if enabled.
6. Export package.

Expected:

- Audio artifact feeds avatar/video node correctly.
- Final video is marked winner.

## Workflow 4 — Audio transcript repurposing

1. Upload audio.
2. Run speech-to-text.
3. Create prompt card from transcript text.
4. Generate image or video variations.
5. Export package.

Expected:

- Text artifacts are usable, not discarded because they are not media URLs.

## Workflow 5 — 3D asset ideation

1. Create project from 3D recipe.
2. Enter object prompt.
3. Run text-to-3D.
4. Mark best artifact winner.
5. Export package.

Expected:

- 3D/file output is stored as an artifact and exportable by URL/manifest.

---

# Definition of done

V10 is complete when:

1. Existing v9 model execution still works.
2. Project assets have lineage and winner/reject/pin metadata.
3. Users can run variants from a node.
4. Users can compare compatible models or receive a clear reason when comparison is unavailable.
5. Users can branch from any compatible artifact, not only latest node output.
6. Prompt/style/character/asset utility nodes work in workflow resolution.
7. Built-in recipes create usable WaveSpeed-only workflows.
8. Export package produces a stable manifest of selected deliverables and lineage.
9. Run snapshots support rerun/clone behavior.
10. Tests prove all new functionality and WaveSpeed-only constraints.
11. No non-WaveSpeed AI model APIs are called.

---

# Suggested implementation order for Codex

1. Add schemas with backward-compatible defaults.
2. Add artifact service and router.
3. Add utility tools and workflow resolver support.
4. Add branching service.
5. Add variant service and queue integration.
6. Add comparison service and compatibility checks.
7. Add recipe store and built-in recipes.
8. Add export package service.
9. Add run snapshot rerun/clone endpoints.
10. Add minimal frontend hooks.
11. Add tests.
12. Update README.

---

# README update required

Add a section:

```markdown
## V10 Weave-style workflow layer

V10 adds artifact lineage, utility nodes, variant batches, model comparison, winner promotion, branch-from-any-artifact, production recipes, export packages, and run snapshots. AI execution remains WaveSpeed-only; local utility nodes only orchestrate prompts, assets, selection, comparison, and export metadata.
```

Also add examples for:

```text
POST /api/projects/{project_id}/nodes/{node_id}/variants
POST /api/projects/{project_id}/nodes/{node_id}/compare-models
POST /api/projects/{project_id}/artifacts/{asset_id}/branch
POST /api/projects/{project_id}/export-package
```

---

# Source references for implementation planning

Use these only as planning references. Do not scrape them at runtime.

Figma/Weave concept references:

- https://www.theverge.com/news/809909/figma-weave-weavy-acquisition-ai-design-canvas
- https://www.techradar.com/pro/software-services/figma-boosts-its-ai-editing-tools-as-it-combines-forces-with-popular-ai-platform-weavy

WaveSpeed model/tool references:

- https://wavespeed.ai/models/wavespeed-ai/wan-2.2/t2v-480p-ultra-fast
- https://wavespeed.ai/models/wavespeed-ai/wan-2.2/i2v-480p-ultra-fast
- https://wavespeed.ai/models/wavespeed-ai/openai-whisper
- https://wavespeed.ai/models/wavespeed-ai/qwen3-tts/voice-design
- https://wavespeed.ai/models/wavespeed-ai/latentsync
- https://wavespeed.ai/models/wavespeed-ai/infinitetalk
- https://wavespeed.ai/models/wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid

