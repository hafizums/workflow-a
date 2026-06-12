# TASK_V6.md — Visual Connector Editor: Manual Wiring, Edge UX, and Graph Validation

## Status

This task comes after `TASK_V2.md`, `TASK_V3.md`, `TASK_V4.md`, and `TASK_V5.md`.

Assume the current project already has:

- FastAPI backend.
- Vanilla HTML/CSS/JS frontend.
- Local JSON project storage.
- Local upload storage.
- WaveSpeed execution behind `WaveSpeedAdapter`.
- Workflow planning/execution from `TASK_V2`.
- Cost-aware model catalog and expanded runnable nodes from `TASK_V3`.
- Project settings, model override UI, cost guard UI, and catalog cleanup from `TASK_V4`.
- Workflow portability, project import/export, project duplication, and templates from `TASK_V5`.

Before coding, Codex must verify these assumptions from the current repo. If any assumption is wrong, do not rewrite the app. Report the mismatch and make the smallest compatible change.

---

## High-level goal

Build **Visual Connector Editor v1**.

The app should let users manually wire node outputs into node inputs on the canvas, without React, React Flow, or any heavy graph library.

Today, workflow connections mostly come from branch buttons. V6 should make the canvas feel like a real node workflow builder:

```text
Drag from source output handle
  ↓
Drop on target input handle
  ↓
Edge appears
  ↓
Workflow plan uses that edge
  ↓
Target node input is resolved from upstream output
```

V6 should not add new WaveSpeed models. It should make the existing models and workflow runner easier to compose.

---

## Why this is TASK V6

V2 made graph execution work.

V3 made model catalog, media previews, and cost estimates useful.

V4 made settings, model overrides, and cost guard usable.

V5 made workflows portable through export/import/duplicate/templates.

The next useful product step is **manual wiring**:

- Users should be able to connect any compatible output to any compatible input.
- Users should not rely only on `Branch from output` shortcuts.
- The visual canvas should show selected edges, edge labels, and connection state.
- Connected input fields should be visibly marked as coming from an upstream node.
- Invalid graph edges should be prevented or clearly explained.

This is more useful now than adding React, a database, auth, billing, or another large model batch.

---

## Read these files first

Read these files before making a plan:

- `FINAL_PROJECT_CONTEXT.md`
- `PROJECT_SUMMARY.md`
- `TASK_V2.md`
- `TASK_V3.md`
- `TASK_V4.md`
- `TASK_V5.md`
- `README.md`
- `requirements.md`
- `CODEX_TASKS.md`
- `AGENTS.md` if present
- `app/main.py`
- `app/schemas.py`
- `app/services/project_store.py`
- `app/services/project_validation.py`
- `app/services/model_catalog.py`
- `app/services/registry.py`
- `app/services/node_runner.py`
- `app/services/workflow_resolver.py`
- `app/routers/projects.py`
- `app/routers/workflows.py`
- `web/index.html`
- `web/app.js`
- `web/style.css`
- files under `tests/`

Also inspect:

- Current `CanvasEdge` shape.
- Current branch-from-output logic.
- Current SVG connection rendering.
- Current workflow plan response.
- Current node field rendering from model specs.
- Current project save/update behavior.
- Current tests for V2/V3/V4/V5.

---

## Important constraints

Do not add:

- React.
- React Flow.
- Next.js.
- Tailwind.
- SQLite/Postgres.
- Auth.
- Billing integration.
- Multi-user accounts.
- Background workers.
- Job queues.
- More WaveSpeed models.
- Professional editing tools.
- Layers, masks, brush editor, vector editor, timeline, crop studio, keyframes, or Photoshop-like panels.

Do not:

- Hardcode secrets.
- Commit `.env` or `WAVESPEED_API_KEY`.
- Break existing project JSON files.
- Break project import/export from V5.
- Remove branch buttons; keep them as shortcuts.
- Rewrite the whole frontend.
- Replace the canvas with a third-party graph library.

Keep:

- FastAPI backend.
- Vanilla frontend.
- Local JSON storage.
- Existing endpoints working.
- Existing V2/V3/V4/V5 behavior working.
- WaveSpeed SDK usage only behind `WaveSpeedAdapter`.
- Backward compatibility with existing project JSON files.

---

## Scope decision for V6

V6 should implement **manual edge creation and edge UX only**.

### In scope

- Output handles on node cards.
- Input handles on node cards.
- Drag-to-connect interaction.
- Ghost connector line while dragging.
- Click edge to select edge.
- Delete selected edge.
- Edge labels showing target input.
- Connected input badges in node cards.
- Validation for self-loop, duplicates, missing nodes, and obvious cycles.
- Compatibility checks between source output kind and target input kind.
- Save/load edges in project JSON.
- Keep workflow plan/run behavior working with newly created manual edges.
- Update import/export/template behavior if needed so manually created edges remain portable.
- Tests and docs.

### Out of scope for V6

- Freeform bezier editor with advanced routing.
- Minimap.
- Zoom/pan canvas.
- Multi-select box.
- Full keyboard command system.
- React Flow.
- Real-time collaboration.
- Background queue/progress/cancel.
- New model categories.
- ZIP asset bundling.

---

## Target feature set

## 1. Node handles

Each node card should show:

- One or more output handles on the right side.
- One or more input handles on the left side.

For V6, keep the handle model simple.

### Output handle

Every runnable or asset-producing node should expose one primary output handle:

```text
source_output = "output"
```

The output handle should visually show the output kind if known:

```text
image
video
audio
other
```

Examples:

```text
Text to Image output: image
Image to Image output: image
Image to Video output: video
Text to Speech output: audio
Upload Image output: image
```

### Input handles

Input handles should come from model fields where possible.

For V6, add handles only for fields that are likely asset/media inputs:

```text
image
reference_image
video
audio
last_image
```

If model field metadata is too limited, use node-type defaults:

```text
image_to_image       -> image
upscale_image        -> image
remove_background    -> image
image_to_video       -> image, last_image if supported
start_end_to_video   -> image, last_image if supported
speech_to_text       -> audio
lip_sync             -> image, audio if present in catalog
video_extend         -> video
```

Do not add handles for text fields like `prompt` or `text` in V6.

---

## 2. Drag-to-connect interaction

Implement vanilla JS interaction:

1. User presses mouse down on a source output handle.
2. App enters connecting mode.
3. A temporary ghost line follows the cursor.
4. User releases mouse on a compatible target input handle.
5. App creates an edge in `state.project.edges`.
6. UI re-renders SVG connection lines.
7. Project can be saved normally.

Suggested frontend state:

```js
state.connectingEdge = {
  source_node_id: 'node_abc',
  source_output: 'output',
  source_kind: 'image',
  start_x: 0,
  start_y: 0,
  current_x: 0,
  current_y: 0
};

state.selectedEdgeId = null;
```

Do not make connection creation depend on saving first. The edge can exist in local frontend state and then be persisted when the user clicks Save.

---

## 3. Edge shape

Use the current edge-compatible shape:

```json
{
  "id": "edge_xxx",
  "source_node_id": "node_source",
  "target_node_id": "node_target",
  "source_handle": "output",
  "target_handle": "image",
  "source_output": "output",
  "target_input": "image"
}
```

Rules:

- Always include `source_node_id` and `target_node_id`.
- Always include `source_output` and `target_input`.
- Keep `source_handle` and `target_handle` for UI compatibility.
- Do not rely only on aliases like `source` and `target` for new edges.
- Existing old edges must still load.

---

## 4. Edge validation

Add validation in frontend before creating an edge.

Must block:

- Self-loop: source node equals target node.
- Missing source node.
- Missing target node.
- Missing target input.
- Exact duplicate edge: same source node, target node, source output, and target input.
- Obvious cycle if the new edge would make the graph cyclic.
- Incompatible source/target media kinds when known.

Allowed compatibility for V6:

```text
image -> image
image -> reference_image
image -> last_image
video -> video
audio -> audio
other -> any known media input only with warning
unknown -> allow with warning, not block
```

If source output kind is unknown, allow the connection but show a warning.

If target input kind is unknown, allow the connection but show a warning.

Do not over-engineer compatibility.

---

## 5. Cycle detection

Add lightweight frontend cycle detection for new edge attempts.

Backend `workflow_resolver.py` already checks cycles during planning. V6 frontend should also prevent obvious cycles earlier.

Pseudo behavior:

```text
Before adding source -> target:
- Temporarily include the edge.
- Build adjacency from project edges.
- Run DFS or topological check.
- If cycle exists, reject and show clear message.
```

Error message example:

```text
Cannot connect these nodes because it would create a workflow cycle.
```

Keep backend cycle detection as the source of truth for workflow runs.

---

## 6. Edge rendering

Improve current SVG line rendering.

Each edge should:

- Start from the actual source output handle position.
- End at the actual target input handle position.
- Use a smooth path or simple line.
- Be clickable/selectable.
- Show selected style when clicked.
- Show a small label near the midpoint with the target input name.

Example label:

```text
image
last_image
audio
video
```

Keep rendering simple. This does not need advanced graph routing.

---

## 7. Edge deletion

Add at least one way to delete an edge.

Required:

- Click edge to select it.
- Show selected edge info in a small panel or log area.
- Add a `Delete selected edge` button.

Optional if small:

- Support pressing `Delete` or `Backspace` when an edge is selected.

Deleting an edge should:

- Remove it from `state.project.edges`.
- Clear `state.selectedEdgeId`.
- Re-render lines.
- Preserve node inputs. Do not automatically delete manually entered target input values.

---

## 8. Connected input UX

When a node input is fed by an edge, show it clearly in the node card.

For a connected target input:

```text
image ← connected from Text to Image
```

Behavior:

- The input field may remain editable, but show that workflow execution will override it with upstream output.
- Prefer adding a badge instead of disabling the field.
- Add a small `Disconnect` action beside the badge if simple.

If disconnect is implemented, it should remove only the corresponding edge.

Do not remove the stored input value when disconnecting.

---

## 9. Branch shortcut refactor

Keep existing branch actions:

- Branch image output to `image_to_image`.
- Branch image output to `image_to_video` if enabled.

But refactor them to use the same helper used by manual edge creation.

Branch behavior should still:

- Create the target node.
- Create a valid edge.
- Prefill the target input if current code already does this.
- Save after user clicks Save, same as before.

---

## 10. Workflow plan integration

After manual edges are created:

- `Preview Plan` should include those edges.
- `Run From Selected` should follow those edges downstream.
- `Run Whole Graph` should use those edges in topological order.
- Connected target inputs should resolve from upstream source outputs.

Do not change the workflow resolver API unless required.

If an edge target input is `last_image`, workflow resolver should preserve it as `last_image` instead of forcing it to `image`.

If current backend defaults accidentally overwrite explicit handles, fix that carefully while keeping old edges compatible.

---

## 11. Backend validation cleanup

Add or improve backend tests for edge validation behavior.

Preferred approach:

- Keep backend edge normalization in `workflow_resolver.py`.
- Keep shared project validation in `project_validation.py` if it exists.
- Add helper functions only if they make tests clearer.

Backend should verify:

- Old alias-based edges still normalize.
- New V6 edge shape normalizes.
- Explicit `target_input` is preserved.
- Missing source node creates a plan error.
- Missing target node creates a plan error.
- Cyclic graph creates a plan error.
- Duplicate edges do not crash planning.

Do not add a new backend endpoint unless there is a strong reason. Existing project save and workflow plan endpoints should be enough.

---

## 12. Tests

Add or update tests under `tests/`.

Suggested file:

```text
tests/test_v6.py
```

Backend tests should cover:

1. V6 edge shape is accepted by schemas.
2. Workflow plan preserves explicit target input like `last_image`.
3. Workflow plan reports cycle errors.
4. Workflow plan reports missing edge node references.
5. Import/export still preserves V6 edges.
6. Template creation/from-project still preserves V6 edges.

Frontend validation is harder to unit test without a browser. At minimum:

```text
node --check web/app.js
```

Optional if easy:

- Extract small pure JS helpers for edge compatibility and cycle checking.
- Add a simple JS test script only if the project already has JS tests.
- Do not add a heavy JS test framework for V6.

---

## 13. Documentation updates

Update:

- `PROJECT_SUMMARY.md`
- `FINAL_PROJECT_CONTEXT.md`
- `README.md` if needed

Docs should mention:

- V6 visual connector editor implemented.
- Users can manually drag from output handles to input handles.
- Edge selection/deletion exists.
- Branch buttons remain available as shortcuts.
- Connections are saved in project JSON and included in export/import/templates.
- Remaining limitations.

Do not overclaim.

If live WaveSpeed generation was not tested, say so.

---

## Checkpoint build plan

Codex should implement V6 in checkpoints.

### Checkpoint 0 — Inspect and plan only

Do not edit files.

Inspect current code and report:

1. Whether V2/V3/V4/V5 are implemented.
2. Current edge shape in schemas.
3. Current branch logic in `web/app.js`.
4. Current SVG connection rendering.
5. Current backend edge normalization behavior.
6. Files that need to change for V6.
7. Risks.

Then propose a short implementation plan.

---

### Checkpoint 1 — Backend edge compatibility tests

Goal:

Make sure backend already supports V6 edge shape or patch it minimally.

Tasks:

1. Add `tests/test_v6.py`.
2. Test V6 edge shape.
3. Test explicit target input preservation.
4. Test cycle plan error.
5. Test import/export/template preservation if helper functions are accessible.
6. Make the smallest backend fixes required.

Validation:

```powershell
python -m compileall app
python -m unittest discover -s tests -v
```

---

### Checkpoint 2 — Frontend handles and ghost line

Goal:

Add visual handles and drag-to-connect state.

Tasks:

1. Add output handles to node cards.
2. Add input handles for media input fields.
3. Add pointer/mouse event handlers.
4. Render ghost line while connecting.
5. Cancel connection on Escape or invalid drop.
6. Do not create edges yet if validation is not complete.

Validation:

```powershell
node --check web/app.js
python -m uvicorn app.main:app --reload --port 8000
```

Manual test:

- Open app.
- See handles on node cards.
- Drag from output handle and see ghost line.
- Release on empty canvas and confirm no edge is created.

---

### Checkpoint 3 — Edge creation validation

Goal:

Create valid edges manually.

Tasks:

1. Implement `createEdgeFromHandles` or equivalent helper.
2. Block self-loops.
3. Block exact duplicates.
4. Block obvious cycles.
5. Check media compatibility.
6. Show clear warnings/errors in log area.
7. Add edge to `state.project.edges` when valid.
8. Re-render connections immediately.

Validation:

```powershell
node --check web/app.js
```

Manual test:

- Connect Text to Image output to Image to Image `image` input.
- Try duplicate connection and confirm it is blocked.
- Try self-loop and confirm it is blocked.
- Try cycle and confirm it is blocked.

---

### Checkpoint 4 — Edge selection, labels, and deletion

Goal:

Make edges manageable.

Tasks:

1. Render edge labels.
2. Make edges clickable.
3. Store `state.selectedEdgeId`.
4. Add selected edge style.
5. Add `Delete selected edge` button or panel action.
6. Optional: Delete/Backspace keyboard shortcut.
7. Re-render connected input badges after deletion.

Validation:

```powershell
node --check web/app.js
```

Manual test:

- Create edge.
- Click edge.
- Confirm selected style and info.
- Delete edge.
- Confirm workflow plan no longer includes the connection.

---

### Checkpoint 5 — Connected input UX and branch refactor

Goal:

Make connected inputs obvious and keep branch shortcuts working.

Tasks:

1. Show badge beside connected target input fields.
2. Show upstream source node title.
3. Add `Disconnect` action if simple.
4. Refactor branch actions to use shared edge creation helper.
5. Preserve current branch-to-remix and branch-to-video behavior.
6. Confirm workflow resolver uses manual and branch-created edges equally.

Validation:

```powershell
node --check web/app.js
python -m unittest discover -s tests -v
```

Manual test:

- Run Text to Image.
- Manually connect output to Image to Image image input.
- Preview plan.
- Run from source node.
- Confirm remix uses source output.
- Branch from output and confirm shortcut still works.

---

### Checkpoint 6 — Docs and final context

Goal:

Update docs for V6.

Tasks:

1. Update `PROJECT_SUMMARY.md`.
2. Update `FINAL_PROJECT_CONTEXT.md`.
3. Update `README.md` only if useful.
4. Mention V6 status and limitations.
5. Do not include secrets or local `.env` values.

Validation:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
```

---

## Acceptance criteria

V6 is complete when:

1. User can add at least two compatible nodes.
2. User can drag from a source output handle to a target input handle.
3. A valid edge appears immediately.
4. Edge is saved in project JSON.
5. Edge reloads after refresh/load.
6. Edge is included in exported project JSON.
7. Imported project preserves V6 edges.
8. Template created from project preserves V6 edges.
9. User can select and delete an edge.
10. Connected target input shows a badge/source hint.
11. `Preview Plan` sees manually created edges.
12. `Run From Selected` follows manually created edges.
13. Self-loop is blocked.
14. Duplicate exact edge is blocked.
15. Obvious cycle is blocked.
16. Existing branch buttons still work.
17. Existing V2/V3/V4/V5 tests pass.
18. No React, React Flow, database, auth, billing, or new model category is added.

---

## Manual test path

Run:

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8000
```

Then open:

```text
http://localhost:8000
```

Test path:

1. Create a new project.
2. Add `Text to Image` node.
3. Add `Image to Image` node.
4. Drag from `Text to Image` output handle to `Image to Image` image input handle.
5. Confirm edge appears with label `image`.
6. Save project.
7. Refresh page.
8. Reload project.
9. Confirm edge remains.
10. Run `Text to Image`.
11. Click `Preview Plan`.
12. Confirm plan shows `Image to Image` receives `image` from upstream output.
13. Run from source node.
14. Confirm downstream remix runs after source output is available.
15. Click edge.
16. Delete selected edge.
17. Confirm edge disappears and plan no longer uses it.
18. Export project.
19. Import the exported project.
20. Confirm imported edge remains if export happened before deletion.
21. Save current project as template.
22. Create project from template.
23. Confirm template edge remains.

Also test invalid cases:

1. Try connecting node to itself.
2. Try creating exact duplicate edge.
3. Try creating a cycle.
4. Try connecting incompatible known kinds such as audio to image if both node types are available.

---

## Suggested Codex prompt

Use this prompt after placing `TASK_V6.md` in the repo root:

```text
Read TASK_V6.md and implement it.

Start with Checkpoint 0 only:
1. Inspect the repo.
2. Verify current V2, V3, V4, and V5 status from code.
3. Inspect current edge shape, branch logic, SVG connection rendering, and workflow resolver behavior.
4. Propose a short implementation plan for V6.

Do not edit files until I approve the plan.
```

After Codex gives the plan:

```text
Proceed with Checkpoint 1 only.

Make the smallest compatible backend/test changes for V6 edge compatibility.
Run the validation commands listed in TASK_V6.md.
Report changed files, test results, and any risk.
```

Then continue checkpoint by checkpoint.

---

## What not to do yet

Do not use V6 to add:

- More WaveSpeed models.
- Queue/progress/cancellation system.
- React Flow.
- Database.
- Auth.
- Billing.
- ZIP exports with binary assets.
- Collaboration.

Recommended future task after V6:

```text
TASK_V7 — Local Run Manager: queue, retry, cancellation UX, and run progress/history cleanup
```

Only start V7 after manual wiring is stable.
