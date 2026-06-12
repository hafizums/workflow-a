# TASK_V6 Results

## Summary

TASK_V6 added Visual Connector Editor v1 for the vanilla canvas. Users can manually drag from node output handles to compatible media input handles, see a ghost line while connecting, create validated edges, select edges, delete selected edges, and see connected-input badges on node cards.

## Backend/Test Changes

- Added `tests/test_v6.py`.
- Confirmed the existing `CanvasEdge` schema accepts the V6 edge shape:
  - `source_node_id`
  - `target_node_id`
  - `source_handle`
  - `target_handle`
  - `source_output`
  - `target_input`
- Confirmed old alias-based edges still normalize.
- Confirmed workflow planning preserves explicit inputs such as `last_image`.
- Confirmed cycle and missing-node plan errors.
- Confirmed duplicate edges do not crash planning.
- Confirmed V5 export/import/clone and templates preserve V6 edge fields.

No new backend endpoint was added for V6.

## Frontend Changes

- Added output handles to node cards.
- Added media input handles for inputs such as `image`, `reference_image`, `video`, `audio`, and `last_image`.
- Added drag-to-connect state and ghost connector line.
- Added frontend validation for:
  - self-loop
  - missing source/target
  - missing target input
  - exact duplicate edge
  - obvious cycles
  - known incompatible media kinds
- Improved SVG edge rendering:
  - lines start/end at handle positions
  - labels show target input names
  - edges and labels are clickable
  - selected edge style
- Added selected edge info and `Delete Selected Edge` button in the inspector.
- Added Delete/Backspace shortcut for selected edge deletion.
- Added connected input badges with source node title and disconnect action.
- Refactored branch-to-remix and branch-to-video shortcuts to use the same edge creation helper as manual wiring.

## Validation Run

```powershell
python -m compileall app
node --check web/app.js
python -m unittest discover -s tests -v
```

Result: all passed, including 42 unit tests.

## Manual Test Path

1. Start the server:

   ```powershell
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. Open `http://localhost:8000`.
3. Create a project.
4. Add a Text to Image node.
5. Add an Image to Image node.
6. Drag from the Text to Image output handle to the Image to Image `image` input handle.
7. Confirm an edge appears with label `image`.
8. Save, refresh, and load the project; confirm the edge remains.
9. Click the edge and delete it with `Delete Selected Edge`.
10. Reconnect the nodes and preview the workflow plan.
11. Confirm branch buttons still create remix/video nodes with edges.
12. Export/import the project and confirm V6 edges survive.
13. Save a project as a template and create a new project from it; confirm V6 edges survive.

## Remaining Limitations

- No zoom/pan/minimap.
- No multi-select edge editing.
- No advanced edge routing.
- Frontend validation is intentionally lightweight; backend workflow planning remains the final graph validation layer.
- Live WaveSpeed execution was not required for V6 validation.
