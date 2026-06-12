# TASK_V2.md — Workflow Execution Engine v1

## Codex task title

Build **Workflow Execution Engine v1** for the existing WaveSpeed Canvas MVP.

This task turns the current visual node canvas into a functional connected workflow runner.

---

## 0. Read this first

Before editing code, inspect the current repository and read these files:

```text
PROJECT_SUMMARY.md
requirements.md
CODEX_TASKS.md
README.md
app/main.py
app/schemas.py
app/services/project_store.py
app/services/node_runner.py
app/services/wavespeed_adapter.py
app/services/registry.py
app/routers/runs.py
web/index.html
web/app.js
web/style.css
```

If these exact filenames differ because the summary files have suffixes from upload/download, read the equivalent files in the repo root.

---

## 1. Current project state

The app is already a working MVP scaffold with:

```text
FastAPI backend
Vanilla HTML/CSS/JavaScript frontend
Local JSON project storage
Local asset uploads
WaveSpeed text-to-image execution
WaveSpeed image-to-image/remix execution
Draggable node cards
Saved node positions
Saved edges
Generated image previews
Branch from generated output into remix node
```

Enabled executable WaveSpeed models:

```text
wavespeed-ai/z-image/turbo
wavespeed-ai/z-image-turbo/image-to-image
```

Existing single-node execution endpoint:

```text
POST /api/runs/node
```

Existing project storage:

```text
data/projects/*.json
```

Existing asset storage:

```text
data/uploads/*
```

---

## 2. This task supersedes conflicting older tasks

For this milestone, **do not follow older instructions that say to convert the frontend to React or React Flow**.

This task intentionally keeps:

```text
Vanilla JavaScript
Vanilla CSS
FastAPI
Local JSON storage
No database
No auth
No billing
No React
No React Flow
No Next.js
No Tailwind
```

Reason: the current MVP already has a vanilla draggable canvas and saved edges. The next useful upgrade is to make those edges drive execution.

---

## 3. Product goal

Make graph connections functional.

The user should be able to build and run this workflow:

```text
Text to Image node
  ↓
Image to Image / Remix node
```

The generated output URL from the first node should automatically become the `image` input of the connected remix node.

The user should be able to:

```text
Preview workflow plan
Run selected node
Run from selected node
Run whole graph
View run history
See node status updates
Save and reload workflow state
```

---

## 4. Non-goals for this task

Do **not** build:

```text
React migration
React Flow migration
Database persistence
Authentication
Billing
Multi-user collaboration
Professional editing tools
Photoshop layers
Mask or brush editor
Vector editor
Crop studio
Timeline editor
Keyframes
New WaveSpeed models
Image-to-video execution
Text-to-speech execution
Background removal execution
Upscale execution
```

Do not enable any disabled placeholder model unless the exact WaveSpeed model page and request fields have been verified separately.

---

## 5. Main deliverables

Implement these files and changes.

### 5.1 New backend service

Create:

```text
app/services/workflow_resolver.py
```

Responsibilities:

```text
Load project graph data
Normalize nodes and edges
Validate edges reference existing nodes
Validate runnable nodes use enabled models
Detect missing upstream outputs
Detect cycles
Build topological execution plan
Resolve connected source node output into target node input
Return clear plan/debug information
```

The resolver must not call WaveSpeed directly.

WaveSpeed calls must remain behind:

```text
app/services/wavespeed_adapter.py
```

Node execution must remain behind:

```text
app/services/node_runner.py
```

---

### 5.2 New backend router

Create:

```text
app/routers/workflows.py
```

Register it in:

```text
app/main.py
```

Add these endpoints:

```text
GET  /api/workflows/{project_id}/plan
POST /api/workflows/{project_id}/run-selected
POST /api/workflows/{project_id}/run-from-node/{node_id}
POST /api/workflows/{project_id}/run-all
GET  /api/workflows/{project_id}/runs
```

#### GET /api/workflows/{project_id}/plan

Query params:

```text
mode=selected|from_node|whole_graph
node_id=optional_node_id
```

Behavior:

```text
selected: plan only the selected node
from_node: plan selected node and all downstream runnable nodes
whole_graph: plan all runnable connected nodes in topological order
```

Response shape:

```json
{
  "ok": true,
  "project_id": "project_xxx",
  "mode": "whole_graph",
  "node_ids": ["node_1", "node_2"],
  "steps": [
    {
      "index": 0,
      "node_id": "node_1",
      "node_type": "text_to_image",
      "model_id": "wavespeed-ai/z-image/turbo",
      "status": "ready",
      "resolved_inputs": {
        "prompt": "..."
      },
      "incoming_edges": [],
      "outgoing_edges": ["edge_1"]
    }
  ],
  "warnings": [],
  "errors": []
}
```

#### POST /api/workflows/{project_id}/run-selected

Request body:

```json
{
  "node_id": "node_xxx"
}
```

Behavior:

```text
Run exactly one node.
Use the workflow resolver to resolve connected incoming inputs before execution.
Append a run history item to the project JSON.
Update node status and outputs in the saved project.
```

#### POST /api/workflows/{project_id}/run-from-node/{node_id}

Behavior:

```text
Run the selected node and every downstream runnable node in topological order.
Resolve each node's inputs after upstream nodes finish.
Stop on first hard error.
Append a run history item to the project JSON.
```

#### POST /api/workflows/{project_id}/run-all

Behavior:

```text
Run all enabled/runnable nodes in topological order.
Skip disabled placeholder model nodes with clear warnings.
Stop on first hard error unless the error is a disabled planned node.
Append a run history item to the project JSON.
```

#### GET /api/workflows/{project_id}/runs

Behavior:

```text
Return project-level run history.
If the project has no runs array yet, return an empty list.
```

---

## 6. Input mapping contract

### 6.1 Edge shape

Use the existing edge shape from `app/schemas.py` and `web/app.js`.

If current edges only have source/target node IDs, keep backward compatibility.

Preferred edge shape for new edges:

```json
{
  "id": "edge_xxx",
  "source_node_id": "node_source",
  "target_node_id": "node_target",
  "source_output": "image",
  "target_input": "image"
}
```

If existing code uses different names, such as `source`, `target`, `from`, `to`, `sourceNodeId`, or `targetNodeId`, normalize internally in `workflow_resolver.py` instead of breaking existing saved projects.

### 6.2 Default mapping

For v1, support this default:

```text
source_node.output_urls[0] -> target_node.inputs.image
```

This is enough for:

```text
text_to_image -> image_to_image
```

### 6.3 Explicit mapping

If the edge has `target_input`, use it:

```text
source_node.output_urls[0] -> target_node.inputs[edge.target_input]
```

Example:

```json
{
  "source_node_id": "node_1",
  "target_node_id": "node_2",
  "source_output": "image",
  "target_input": "image"
}
```

### 6.4 Source output resolution order

When resolving a connected source node output, use the first available value from this order:

```text
1. source_node.output_urls[0]
2. source_node.data.output_urls[0]
3. source_node.outputs.image
4. source_node.inputs.image if it is an upload/source node
5. latest asset URL linked by source_node.output_asset_ids[0]
```

Use the actual project schema when implementing. Do not invent a parallel schema if the existing project model already defines fields.

### 6.5 Local asset handling

If a target model requires a public remote input and the resolved source is a local uploaded asset, reuse the existing backend logic that uploads local assets to WaveSpeed.

Do not pass `localhost` URLs directly to remote WaveSpeed inference when the existing app already has logic to upload local files to WaveSpeed.

---

## 7. Run history data model

Add a project-level `runs` array if missing.

Run history item shape:

```json
{
  "id": "run_xxx",
  "type": "single_node|from_node|whole_graph",
  "status": "running|success|error",
  "started_at": "2026-06-12T00:00:00Z",
  "finished_at": "2026-06-12T00:01:00Z",
  "node_ids": ["node_1", "node_2"],
  "asset_ids": ["asset_1"],
  "output_urls": ["https://..."],
  "errors": [],
  "warnings": []
}
```

Implementation requirements:

```text
Use UUID-style IDs or the existing project ID helper.
Use UTC ISO timestamps.
Keep the array small if needed; optional cap at latest 50 runs.
Save runs into the existing project JSON.
Do not add a database.
```

---

## 8. Node status contract

Use these node statuses:

```text
idle
queued
running
success
error
skipped
```

Behavior:

```text
Before execution plan starts: planned nodes become queued.
Current executing node becomes running.
Successful node becomes success.
Failed node becomes error and stores error_message.
Disabled/non-runnable planned nodes become skipped with a warning, not a crash.
```

Do not remove existing status fields if they already exist. Extend them safely.

---

## 9. Backend validation and error handling

Return clear API errors for:

```text
Missing project
Missing node
Invalid edge source node
Invalid edge target node
Cycle detected
Disabled model
Placeholder model
Missing prompt
Missing required source image
Missing upstream output URL
WaveSpeed API key missing
WaveSpeed SDK failure
WaveSpeed returned no output URL
Project save failure
```

Recommended error shape:

```json
{
  "ok": false,
  "error": {
    "code": "missing_upstream_output",
    "message": "Source node node_1 has no output URL yet. Run it first.",
    "details": {
      "source_node_id": "node_1",
      "target_node_id": "node_2"
    }
  }
}
```

Use the existing project error style if one already exists. Keep it consistent.

---

## 10. Workflow execution algorithm

Implement a simple deterministic algorithm.

### 10.1 Build graph

```text
1. Load project.
2. Build node index by node ID.
3. Normalize edges.
4. Remove or warn about edges pointing to missing nodes.
5. Build adjacency list and incoming-edge map.
```

### 10.2 Detect cycles

Use DFS or Kahn's algorithm.

If a cycle is detected:

```text
Do not run workflow.
Return a clear cycle_detected error.
```

### 10.3 Select nodes to run

Modes:

```text
selected:
  only node_id

from_node:
  node_id plus all downstream nodes reachable through edges

whole_graph:
  all runnable/enabled nodes in the project, ordered topologically
```

### 10.4 Resolve inputs

Before each node runs:

```text
1. Start with node.inputs.
2. For each incoming edge into the node, find source output URL.
3. Write resolved URL into target input field.
4. Validate required fields using existing node_runner/model registry validation.
5. Pass resolved inputs into node_runner.
```

### 10.5 Execute

```text
1. Save workflow run history item as running.
2. Set planned nodes to queued.
3. For each step:
   - set node status running
   - resolve inputs
   - call existing node_runner logic
   - update node output fields
   - save project
4. On success, mark run history success.
5. On failure, mark current node error and run history error.
6. Save project at the end and after each successful node.
```

Do not duplicate WaveSpeed execution logic in the workflow router.

---

## 11. Frontend changes

Modify only vanilla frontend files:

```text
web/index.html
web/app.js
web/style.css
```

Add simple UI controls:

```text
Preview workflow plan
Run selected node
Run from selected node
Run whole graph
Refresh run history
```

Add simple panels:

```text
Workflow Plan panel
Run History panel
Workflow Errors/Warnings panel
```

Do not redesign the entire UI.

Do not replace the existing canvas.

Do not add a frontend build step.

### 11.1 Selected node behavior

Use the existing selected node state if available.

If no node is selected and the user clicks `Run selected node`, show a frontend error:

```text
Select a node first.
```

### 11.2 Plan preview behavior

When user clicks `Preview workflow plan`:

```text
Call GET /api/workflows/{project_id}/plan?mode=whole_graph
Render ordered node list
Show warnings
Show errors
```

### 11.3 Run from selected behavior

When user clicks `Run from selected node`:

```text
Call POST /api/workflows/{project_id}/run-from-node/{selectedNodeId}
Update nodes from returned project/run response
Refresh previews
Refresh run history
```

### 11.4 Run whole graph behavior

When user clicks `Run whole graph`:

```text
Call POST /api/workflows/{project_id}/run-all
Update nodes from returned project/run response
Refresh previews
Refresh run history
```

### 11.5 Loading states

While a workflow is running:

```text
Disable workflow run buttons
Show running message
Keep node cards visible
Show statuses on each node card
```

---

## 12. Response shapes

Use these shapes unless the existing API style strongly suggests a different structure.

### 12.1 Workflow plan response

```json
{
  "ok": true,
  "project_id": "project_xxx",
  "mode": "whole_graph",
  "node_ids": ["node_1", "node_2"],
  "steps": [
    {
      "index": 0,
      "node_id": "node_1",
      "node_type": "text_to_image",
      "model_id": "wavespeed-ai/z-image/turbo",
      "display_name": "Z Image Turbo",
      "status": "ready",
      "resolved_input_keys": ["prompt", "size", "seed", "output_format"],
      "incoming_edges": [],
      "outgoing_edges": ["edge_1"]
    }
  ],
  "warnings": [],
  "errors": []
}
```

### 12.2 Workflow run response

```json
{
  "ok": true,
  "project_id": "project_xxx",
  "run": {
    "id": "run_xxx",
    "type": "whole_graph",
    "status": "success",
    "started_at": "...",
    "finished_at": "...",
    "node_ids": ["node_1", "node_2"],
    "asset_ids": ["asset_1", "asset_2"],
    "output_urls": ["https://..."],
    "errors": [],
    "warnings": []
  },
  "project": {}
}
```

Returning the updated project is useful so the frontend can refresh without a second request.

---

## 13. Tests and validation

Add tests where practical, but do not block the MVP if the current project has no test harness yet.

Minimum backend validation:

```powershell
python -m compileall app
```

Minimum frontend syntax validation:

```powershell
node --check web/app.js
```

Server validation:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Browser validation:

```text
http://localhost:8000
http://localhost:8000/docs
http://localhost:8000/api/health
http://localhost:8000/api/models
```

---

## 14. Manual acceptance test

Use this exact path after implementation.

```text
1. Start the server.
2. Open http://localhost:8000.
3. Create a new project.
4. Add a text_to_image node.
5. Enter a prompt.
6. Run the text_to_image node.
7. Confirm an output image preview appears.
8. Click Branch from output.
9. Confirm an image_to_image/remix node appears.
10. Confirm an edge exists from text_to_image to image_to_image.
11. Clear the remix node image input if needed, so connection mapping is tested.
12. Enter a remix prompt.
13. Click Preview workflow plan.
14. Confirm the plan shows text_to_image before image_to_image.
15. Select the text_to_image node.
16. Click Run from selected node.
17. Confirm text_to_image runs or reuses/generates output.
18. Confirm image_to_image receives the upstream output URL as its image input.
19. Confirm the remix node runs successfully.
20. Confirm both nodes show success.
21. Confirm run history contains a from_node run.
22. Save the project.
23. Refresh the browser.
24. Load the project.
25. Confirm nodes, edges, outputs, statuses, and run history remain.
```

---

## 15. Windows CMD commands for the developer

Use Windows CMD commands in final notes.

```bat
cd path\to\project
.venv\Scripts\activate.bat
python -m compileall app
node --check web/app.js
python -m uvicorn app.main:app --reload --port 8000
```

If `py` is preferred:

```bat
py -m compileall app
py -m uvicorn app.main:app --reload --port 8000
```

---

## 16. Implementation checkpoints

Work in small checkpoints.

### Checkpoint 1 — backend plan only

```text
Create workflow_resolver.py.
Implement graph normalization.
Implement cycle detection.
Implement execution plan building.
Add GET plan endpoint.
No frontend changes yet.
Validate compileall.
```

### Checkpoint 2 — backend execution

```text
Add workflow run endpoints.
Reuse node_runner.
Resolve upstream outputs into target inputs.
Save run history.
Update node statuses.
Validate compileall.
```

### Checkpoint 3 — frontend controls

```text
Add workflow buttons.
Add plan panel.
Add run history panel.
Wire API calls.
Validate node --check web/app.js.
```

### Checkpoint 4 — manual workflow test

```text
Run text_to_image -> image_to_image.
Confirm connection mapping works.
Confirm save/reload preserves state.
Fix only blocking bugs.
```

---

## 17. Required final response from Codex

After implementing, report:

```text
1. Files changed
2. New API endpoints
3. How workflow planning works
4. How connected input mapping works
5. How run history is stored
6. Validation commands run
7. Manual test results
8. Any known limitations
```

Do not claim live WaveSpeed generation was tested unless it was actually tested with a valid `WAVESPEED_API_KEY`.

---

## 18. Known limitations accepted for v1

These are acceptable for this milestone:

```text
Only first output URL is used.
Only image-style edge mapping is fully supported.
No parallel execution.
No cancellation UI.
No retry queue.
No background jobs.
No database.
No React canvas.
No multi-user support.
```

---

## 19. Stop condition

Stop when all of these are true:

```text
Backend compiles successfully.
Frontend JS syntax check passes.
Server starts successfully.
Workflow plan endpoint returns ordered steps.
Run selected node works.
Run from selected node works.
Run whole graph works for text_to_image -> image_to_image.
Connected source output maps into target image input.
Run history persists in project JSON.
Existing single-node run behavior still works.
No secrets are committed.
No React/database/pro-editor scope was added.
```

