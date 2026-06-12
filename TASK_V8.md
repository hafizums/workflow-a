# TASK_V8.md — WaveSpeed Canvas v8 UI Upgrade

## Goal

Upgrade the current `workflow-a` v7 interface into **WaveSpeed Studio v8**: a cleaner, more modern, easier-to-use node workflow UI while preserving the existing FastAPI backend, local JSON project model, vanilla JavaScript frontend, and all current API routes.

This task is for Codex to implement directly in the existing repository:

```text
https://github.com/hafizums/workflow-a
```

Do not create a ZIP file. Do not create a second app. Modify the existing repo in place.

---

## Current app context

The current app is a FastAPI local MVP with a static vanilla frontend under:

```text
web/index.html
web/style.css
web/app.js
```

The current v7 frontend already supports:

- Project select/load/create/save/import/export/duplicate.
- Templates and save-as-template.
- Project settings and model overrides.
- Node library.
- DOM canvas nodes.
- Manual node wiring with SVG edges.
- Node forms generated from model fields.
- Asset list and previews.
- Workflow plan preview.
- Run selected / run downstream / run whole graph.
- Local Run Manager with refresh, cancel, retry, and clear completed.
- Run history and activity log.
- Collapsible left and right panels.

v8 should keep all of that working, but the UI should feel much more polished and organized.

---

## Hard constraints

1. **Keep the app vanilla.**
   Do not convert to React, Vue, Svelte, or another framework for v8.

2. **No build step.**
   The app should still run with:

   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

3. **Preserve existing backend routes.**
   Do not rename or remove existing API endpoints.

4. **Preserve existing data shape.**
   Do not introduce a database or migration in this task.

5. **Preserve existing important DOM IDs unless deliberately updating every dependent reference.**
   The current `app.js` uses direct `querySelector` calls against many IDs. Keep these IDs available:

   ```text
   appLayout
   projectSelect
   loadProjectBtn
   newProjectBtn
   saveProjectBtn
   exportProjectBtn
   importProjectBtn
   duplicateProjectBtn
   templatesBtn
   saveTemplateBtn
   projectSettingsBtn
   importProjectFile
   toggleNodesBtn
   toggleInspectorBtn
   nodeLibrary
   assetList
   canvas
   projectName
   projectDescription
   previewPlanBtn
   runSelectedBtn
   runFromSelectedBtn
   runWholeGraphBtn
   refreshRunsBtn
   selectedNodeLabel
   selectedEdgePanel
   deleteSelectedEdgeBtn
   workflowPlan
   workflowMessages
   refreshJobsBtn
   clearCompletedJobsBtn
   jobList
   runHistory
   outputLog
   settingsPanelBackdrop
   settingsPanel
   closeSettingsBtn
   costGuardEnabled
   costWarnAbove
   costMaxSingle
   costMaxWorkflow
   blockUnknownCost
   modelOverrideList
   saveSettingsBtn
   cancelSettingsBtn
   templatesPanelBackdrop
   templatesPanel
   closeTemplatesBtn
   templateList
   ```

6. **Do not remove functionality to make the UI prettier.**
   If a feature existed in v7, it must remain reachable in v8.

7. **Use accessible HTML.**
   Buttons must remain real buttons. Tabs must expose active state. Inputs need labels or `aria-label`.

8. **Do not hide errors.**
   Toasts can be added, but the Activity log must still show important messages.

---

## Design direction

The v8 UI should feel like a small creative workflow studio, not a bare MVP.

Use a dark, high-contrast studio theme with:

- Soft glass panels.
- Better spacing.
- Rounded cards.
- Clear command groups.
- Better empty states.
- Better visual hierarchy.
- Compact but readable node cards.
- A more useful canvas header/HUD.
- A tabbed inspector instead of one long right panel.

Working product name in the UI:

```text
WaveSpeed Studio v8
```

Suggested visual language:

- Dark background with subtle radial/canvas grid.
- Accent color for successful/active states.
- Amber/yellow for running/warning states.
- Red for error/destructive states.
- Pills/chips for metadata.
- Cards with slightly lifted shadows.
- Command-bar groups instead of one long horizontal button row.

---

## Main v8 UX problems to solve

### Problem 1 — Top bar is crowded

Current top bar has many actions in one scroll row. v8 should group actions into clearer command groups:

- Project selector group.
- Project file/actions group.
- Workflow run group.
- Utility group.

Keep all actions available.

### Problem 2 — Left library is hard to scan

Add:

- Search box for nodes.
- Category filter chips.
- Clearer node cards.
- Better disabled-state messaging.
- Asset section below node library, still reachable.

### Problem 3 — Right inspector is too long

Convert the right panel into tabs:

```text
Project | Workflow | Runs | Activity
```

Each tab should show only the relevant content.

### Problem 4 — Canvas has weak context

Add a canvas HUD/status strip showing:

- Current project name.
- Node count.
- Edge count.
- Asset count.
- Active job count.
- Selected node/edge summary.

The canvas should also have a better empty state when no nodes exist.

### Problem 5 — Feedback is too hidden

Keep `outputLog`, but add small toast notifications for common actions:

- Project loaded/saved/imported/exported/duplicated.
- Job queued.
- Connection created/deleted.
- Copy URL.
- Validation or API errors.

---

## Files to edit

Minimum required files:

```text
web/index.html
web/style.css
web/app.js
README.md
CODEX_TASKS.md
```

Optional new file if it keeps `app.js` cleaner:

```text
web/ui-v8.js
```

If adding `web/ui-v8.js`, load it after `app.js` only if it does not depend on monkey-patching fragile behavior. Prefer integrating core UI state into `app.js` when possible.

---

## Implementation plan

### Phase 1 — Prepare v8 structure safely

1. Create a working branch:

   ```bash
   git checkout -b v8-ui-upgrade
   ```

2. Run the app once before changes and confirm the current UI loads:

   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

3. Review current `web/app.js` selectors before changing HTML.

4. Keep all required IDs listed above.

5. Add comments in changed HTML where an element ID is required by existing JS.

Acceptance:

- The app still loads before the visual restyle is started.
- No missing-selector runtime errors are introduced.

---

### Phase 2 — Rework `web/index.html`

Replace the current basic layout with a more structured studio shell.

Target structure:

```text
body
  div.app-shell
    header.studio-topbar
      section.brand-block
      section.project-command-group
      section.workflow-command-group
      section.utility-command-group

    main#appLayout.layout.studio-layout
      button#toggleNodesBtn.panel-tab.panel-tab-left
      button#toggleInspectorBtn.panel-tab.panel-tab-right

      aside.sidebar.studio-sidebar
        section.panel-section.library-section
          header.section-header
          input#nodeSearchInput
          div#nodeCategoryFilters
          div#nodeLibrary
        section.panel-section.assets-section
          header.section-header
          div#assetList

      section.canvas-wrap.studio-canvas-wrap
        div.canvas-toolbar
          div.canvas-title
          div#canvasStats.canvas-stats
        div#canvasSelectionBar.canvas-selection-bar
        div#canvas.canvas
          div.canvas-help / empty state

      aside.inspector.studio-inspector
        nav.inspector-tabs
          buttons with data-inspector-tab
        section#projectTab.inspector-tab-panel
        section#workflowTab.inspector-tab-panel
        section#runsTab.inspector-tab-panel
        section#activityTab.inspector-tab-panel

    existing settings panel markup
    existing templates panel markup
    div#toastStack.toast-stack
```

Required new IDs:

```text
nodeSearchInput
nodeCategoryFilters
canvasStats
canvasSelectionBar
toastStack
```

Recommended inspector tab button data attributes:

```html
<button type="button" class="inspector-tab active" data-inspector-tab="project">Project</button>
<button type="button" class="inspector-tab" data-inspector-tab="workflow">Workflow</button>
<button type="button" class="inspector-tab" data-inspector-tab="runs">Runs</button>
<button type="button" class="inspector-tab" data-inspector-tab="activity">Activity</button>
```

Map existing content into tabs:

Project tab:

- `#projectName`
- `#projectDescription`
- `#selectedNodeLabel`
- `#selectedEdgePanel`
- `#deleteSelectedEdgeBtn`

Workflow tab:

- `#previewPlanBtn`
- `#runSelectedBtn`
- `#runFromSelectedBtn`
- `#runWholeGraphBtn`
- `#refreshRunsBtn`
- `#workflowPlan`
- `#workflowMessages`

Runs tab:

- `#refreshJobsBtn`
- `#clearCompletedJobsBtn`
- `#jobList`
- `#runHistory`

Activity tab:

- `#outputLog`

Acceptance:

- All old controls still exist.
- Inspector content is separated into tabs.
- Settings and Templates panels still open and close.
- Import file input still works.

---

### Phase 3 — Replace `web/style.css` with v8 design system

Create a cleaner tokenized stylesheet.

Required CSS sections:

1. Root tokens:

   ```css
   :root {
     --bg: ...;
     --bg-2: ...;
     --panel: ...;
     --panel-2: ...;
     --panel-glass: ...;
     --field: ...;
     --text: ...;
     --muted: ...;
     --line: ...;
     --accent: ...;
     --accent-2: ...;
     --danger: ...;
     --shadow: ...;
     --radius-sm: ...;
     --radius-md: ...;
     --radius-lg: ...;
   }
   ```

2. Base reset and typography.
3. Top command bar.
4. Layout grid and collapsed side panels.
5. Sidebar/library cards.
6. Canvas toolbar, stats, grid, empty state.
7. Node cards and connection handles.
8. Inspector tabs and tab panels.
9. Workflow/job/run cards.
10. Asset previews.
11. Settings/templates modal panels.
12. Toast stack.
13. Responsive layout.

Responsive requirements:

- At widths below `1100px`, stack panels vertically or allow sidebar/inspector to collapse cleanly.
- Avoid horizontal overflow except inside the canvas area.
- Top command groups may wrap, but controls must remain usable.
- Canvas must remain scrollable.

Important visual details:

- Node cards should be wider than v7 if useful, around `300px` to `320px`.
- Node forms should be easier to read.
- Primary Run buttons should visually stand out.
- Delete buttons should appear destructive but not overly loud.
- Disabled library cards should remain readable.
- Edge paths should still be clickable.
- Selected node and selected edge should be obvious.

Acceptance:

- UI looks modern on desktop.
- UI remains usable on a laptop-width screen.
- Existing canvas node dragging and edge drawing still work.

---

### Phase 4 — Extend UI state in `web/app.js`

Extend current `state.ui` with v8 UI preferences.

Suggested state:

```js
ui: {
  leftPanelCollapsed: false,
  rightPanelCollapsed: false,
  activeInspectorTab: 'project',
  nodeLibraryQuery: '',
  nodeLibraryCategory: 'all',
}
```

Update layout preference load/save so older localStorage values do not break.

Required helper functions:

```js
function projectStats() {}
function activeJobsCount() {}
function renderCanvasStats() {}
function renderCanvasSelectionBar() {}
function renderStudioChrome() {}
function setInspectorTab(tabName) {}
function renderInspectorTabs() {}
function showToast(message, kind = 'info') {}
function normalizeCategory(value) {}
function libraryCategories() {}
function renderNodeCategoryFilters() {}
function filteredNodeDefs() {}
function setupV8EventHandlers() {}
```

Call `renderStudioChrome()` inside `renderAll()` after the project/canvas/job state has been updated.

Suggested implementation detail:

```js
function renderAll() {
  renderLayoutState();
  renderProjectPanel();
  renderCanvas();
  renderAssets();
  renderWorkflowPanels();
  renderJobs();
  renderSettingsPanel();
  renderTemplatesPanel();
  updateWorkflowButtons();
  renderStudioChrome();
}
```

Acceptance:

- v8-specific UI updates after loading project, saving, adding node, deleting node, connecting edge, deleting edge, queuing jobs, refreshing jobs, and importing project.
- Old saved layout preferences do not crash the app.

---

### Phase 5 — Add node search and category filters

Update `renderNodeLibrary()` so it uses `filteredNodeDefs()` instead of always rendering every node.

Search should match:

- Title.
- Type.
- Category.
- Description.
- Model ID if available.

Category filters should be built dynamically from available node definitions.

Required behavior:

- `All` filter always exists.
- Active category chip is visually marked.
- Search input updates the library live.
- Empty result shows a helpful message.
- Disabled nodes are still visible unless filtered out by search/category.

Suggested empty state text:

```text
No nodes match this search. Try clearing the search or switching category.
```

Acceptance:

- Typing `image` filters library to image-related nodes.
- Selecting a category updates visible nodes.
- Add Node still works for enabled nodes.
- Coming Soon still appears for disabled nodes.

---

### Phase 6 — Add canvas stats and selection bar

Add `renderCanvasStats()` to update `#canvasStats` with compact stat pills:

```text
Nodes: N
Edges: N
Assets: N
Active jobs: N
```

Add `renderCanvasSelectionBar()` to update `#canvasSelectionBar`:

When a node is selected:

```text
Selected node: <title> · <type> · <status>
```

When an edge is selected:

```text
Selected edge: <source title> → <target title> · input <target input>
```

When nothing is selected:

```text
No selection. Drag from an output handle to an input handle to connect nodes.
```

Acceptance:

- Stats update when nodes/assets/jobs change.
- Selection bar updates when selecting a node or edge.
- Bar does not block canvas dragging or edge clicking.

---

### Phase 7 — Add inspector tabs

Implement tab switching inside `app.js`.

Required behavior:

- Default tab is `project`.
- Clicking tab buttons switches panels.
- Active tab persists in localStorage with other UI state.
- Keyboard shortcuts switch tabs:

```text
Alt+1 = Project
Alt+2 = Workflow
Alt+3 = Runs
Alt+4 = Activity
```

Panel display approach:

- Use `.active` class on the selected tab button.
- Use `.active` class or `hidden` attribute on tab panels.
- Keep all existing child IDs in the DOM.

Acceptance:

- Project tab shows project form and selection info.
- Workflow tab shows workflow actions, plan, and messages.
- Runs tab shows jobs and run history.
- Activity tab shows output log.
- All existing buttons in tabs still work.

---

### Phase 8 — Add toast notifications without replacing logs

Implement `showToast(message, kind)`.

Suggested kinds:

```text
info
success
warning
error
```

Use toasts for important user feedback in these functions:

- `loadProject`
- `createProject`
- `saveProject`
- `importProjectFile`
- `duplicateProject`
- `createProjectFromTemplate`
- `deleteUserTemplate`
- `saveCurrentProjectAsTemplate`
- `saveProjectSettings`
- `addNode`
- `createEdgeFromHandles`
- `deleteEdge`
- `copyText`
- `runNode`
- `queueWorkflowJob`
- `refreshJobs` only on error, not every poll
- `cancelJob`
- `retryJob`
- `clearCompletedJobs`
- `uploadFromNode`

Do not spam toasts during job polling.

Toasts should auto-dismiss after around 3–5 seconds and have a close button.

Acceptance:

- Successful save shows a toast and still writes to `#outputLog`.
- API errors show error toast and still write to `#outputLog`.
- Polling does not create repeated notifications.

---

### Phase 9 — Add useful keyboard shortcuts

Extend the existing keydown listener.

Required shortcuts:

```text
Ctrl/Cmd+S       Save project
Ctrl/Cmd+Enter   Preview workflow plan
Ctrl/Cmd+Shift+Enter Run whole graph
Alt+1            Project inspector tab
Alt+2            Workflow inspector tab
Alt+3            Runs inspector tab
Alt+4            Activity inspector tab
Escape           Cancel edge drag; close settings/templates if open
Delete/Backspace Delete selected edge, preserving current behavior
```

Rules:

- Do not steal shortcuts while typing in inputs, textareas, or selects, except `Escape` for closing panels.
- Prevent browser Save dialog for `Ctrl/Cmd+S` only when the app can save a project.

Acceptance:

- `Ctrl+S` saves project instead of opening browser save dialog.
- Shortcuts do not damage typing in prompt fields.
- Existing delete-selected-edge behavior still works.

---

### Phase 10 — Improve empty states

Add better empty states for:

1. Canvas with no nodes.
2. Node library search with no results.
3. Asset list with no assets.
4. Run manager with no jobs.
5. Run history with no runs.
6. Workflow plan with no preview.
7. Workflow messages with no messages.

Canvas empty state should include a short starter hint:

```text
Start by adding Upload Image or Text to Image from the node library.
```

Acceptance:

- Empty states are styled as helpful cards, not plain muted text.
- Empty states do not interfere with existing JS selectors.

---

### Phase 11 — Polish node cards

Improve `nodeCardHtml()` output and styling without breaking functionality.

Node card should clearly show:

- Drag handle.
- Editable title.
- Status pill.
- Category/output/model badges.
- Cost/model details in a compact metadata block.
- Inputs/forms.
- Run/branch/save/delete actions.
- Error messages.
- Output previews.

Recommended changes:

- Make `Run` visually primary.
- Make `Delete` destructive style.
- Use compact metadata chips.
- Better spacing between inputs.
- Keep output and input handles visible and easy to click.

Acceptance:

- Node dragging works.
- Field edits update node inputs.
- Run button queues job.
- Branch buttons still work.
- Save/delete still work.
- Output previews still render.

---

### Phase 12 — Docs update

Update `README.md` with a short v8 UI section.

Add under Current MVP behavior or a new heading:

```markdown
## V8 UI upgrade

V8 keeps the vanilla FastAPI/static frontend but reorganizes the interface into a studio layout with a command bar, searchable node library, canvas stats, tabbed inspector, and toast feedback. Existing project, template, asset, workflow, and run-manager APIs remain unchanged.
```

Update `CODEX_TASKS.md` with a completed or active phase:

```markdown
## Phase 8 — UI upgrade

1. Rework static frontend into WaveSpeed Studio v8 layout.
2. Add searchable node library and category filters.
3. Add canvas stats and selection bar.
4. Add tabbed inspector.
5. Add toast feedback and keyboard shortcuts.
6. Preserve existing FastAPI routes and local JSON storage.
```

Acceptance:

- Docs explain what v8 changed.
- Docs do not claim production readiness.

---

## Suggested implementation details

### `projectStats()`

Suggested shape:

```js
function projectStats() {
  return {
    nodes: state.project?.nodes?.length || 0,
    edges: state.project?.edges?.length || 0,
    assets: state.project?.assets?.length || 0,
    activeJobs: activeJobsCount(),
  };
}
```

### `activeJobsCount()`

Suggested shape:

```js
function activeJobsCount() {
  return (state.jobs || []).filter((job) => ACTIVE_JOB_STATUSES.includes(job.status)).length;
}
```

### `filteredNodeDefs()`

Suggested logic:

```js
function filteredNodeDefs() {
  const query = (state.ui.nodeLibraryQuery || '').trim().toLowerCase();
  const category = state.ui.nodeLibraryCategory || 'all';
  return allNodeDefs().filter((def) => {
    const matchesCategory = category === 'all' || normalizeCategory(def.category) === category;
    const searchable = [
      def.title,
      def.type,
      def.category,
      def.description,
      def.model_id,
      def.id,
    ].join(' ').toLowerCase();
    return matchesCategory && (!query || searchable.includes(query));
  });
}
```

### `showToast()`

Suggested behavior:

```js
function showToast(message, kind = 'info') {
  const stack = qs('#toastStack');
  if (!stack || !message) return;
  const item = document.createElement('div');
  item.className = `toast toast-${kind}`;
  item.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <button type="button" aria-label="Dismiss notification">×</button>
  `;
  item.querySelector('button').addEventListener('click', () => item.remove());
  stack.appendChild(item);
  window.setTimeout(() => item.remove(), 4200);
}
```

### Inspector tabs

Suggested behavior:

```js
function setInspectorTab(tabName) {
  const valid = ['project', 'workflow', 'runs', 'activity'];
  state.ui.activeInspectorTab = valid.includes(tabName) ? tabName : 'project';
  saveLayoutPreference();
  renderInspectorTabs();
}
```

---

## Manual test checklist

Run the app:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000
```

Then verify:

### Startup

- App loads without console errors.
- A project loads or a new project is created.
- Top command bar appears.
- Left sidebar appears.
- Canvas appears.
- Right inspector appears with tabs.

### Project actions

- New Project works.
- Load works.
- Save Project works.
- Export Project works.
- Import Project opens file picker.
- Duplicate Project works.
- Templates opens.
- Save as Template works.
- Project Settings opens.

### Node library

- Node list renders.
- Search filters nodes.
- Category chips filter nodes.
- Add Node adds enabled nodes to canvas.
- Disabled nodes cannot be added.

### Canvas

- Empty state appears when project has no nodes.
- Node can be dragged.
- Node selection updates selection bar.
- Node deletion still works.
- Canvas stats update.

### Edges

- Drag output handle to input handle creates edge.
- Duplicate edge is blocked.
- Self-loop is blocked.
- Cycle is blocked.
- Incompatible media kind is blocked.
- Selecting edge updates selection bar and right panel.
- Delete Selected Edge works.
- Delete/Backspace shortcut works when not typing.

### Node forms and outputs

- Prompt/field changes update node inputs.
- Asset select works for image fields.
- Upload Image node uploads asset.
- Output previews still render for image/video/audio.
- Copy URL works and shows toast.

### Workflow

- Preview Plan works.
- Run Selected works when node selected.
- Run From Selected works when node selected.
- Run Whole Graph queues job.
- Workflow errors/warnings show.

### Run Manager

- Jobs list renders.
- Refresh Jobs works.
- Cancel queued/running job works as before.
- Retry failed/cancelled job works.
- Clear Completed works.
- Active job count updates.

### Inspector tabs

- Project tab works.
- Workflow tab works.
- Runs tab works.
- Activity tab works.
- Alt+1/2/3/4 shortcuts switch tabs.

### Keyboard shortcuts

- Ctrl/Cmd+S saves project.
- Ctrl/Cmd+Enter previews plan.
- Ctrl/Cmd+Shift+Enter runs whole graph.
- Escape cancels edge connection.
- Escape closes settings/templates panels.
- Shortcuts do not interfere while typing in inputs/textareas/selects.

### Responsive

- UI remains usable around 1366px desktop width.
- UI remains usable around 1024px laptop width.
- Below tablet width, panels stack/collapse without hiding required controls permanently.

---

## Automated sanity checks

At minimum, run:

```bash
python -m compileall app
```

If tests exist, run them:

```bash
pytest
```

Use browser console to check that there are no missing-selector errors such as:

```text
Cannot read properties of null
```

---

## Definition of done

The v8 task is complete when:

1. `python -m uvicorn app.main:app --reload --port 8000` serves the app.
2. The app loads at `/` with no console errors.
3. All v7 features remain functional.
4. UI is visibly upgraded into a polished studio layout.
5. Node library search and category filters work.
6. Canvas stats and selection bar work.
7. Inspector tabs work.
8. Toast feedback works without replacing the Activity log.
9. Keyboard shortcuts work safely.
10. README and CODEX_TASKS mention the v8 UI upgrade.

---

## Non-goals for v8

Do not implement these in this task:

- React migration.
- React Flow migration.
- Database migration.
- Authentication.
- Multi-user support.
- Billing.
- New WaveSpeed models.
- Advanced timeline editor.
- Photoshop-style layers.
- Inpainting or masking canvas.
- Deployment hardening.

Those can remain future phases.

---

## Final instruction to Codex

Implement the v8 UI upgrade in small, safe commits. Preserve existing behavior first, then improve the visual structure. Whenever changing HTML, immediately check matching selectors in `web/app.js`. Prefer clear vanilla JavaScript helpers over large fragile rewrites.
