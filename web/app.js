const state = {
  project: null,
  projects: [],
  models: [],
  templates: [],
  selectedNodeId: null,
  workflowRunning: false,
  settingsOpen: false,
  templatesOpen: false,
  ui: {
    leftPanelCollapsed: false,
    rightPanelCollapsed: false,
  },
};

const CARD_GAP_X = 330;
const CARD_BRANCH_OFFSET_Y = 40;

const LOCAL_FALLBACK_NODE_DEFS = [
  {
    id: 'upload_image',
    title: 'Upload Image',
    type: 'upload_image',
    category: 'input',
    description: 'Add a local source image asset.',
    runnable: false,
    upload: true,
    enabled: true,
    defaults: {},
  },
];

const qs = (selector) => document.querySelector(selector);

async function api(path, options = {}) {
  const headers = options.body instanceof FormData
    ? options.headers || {}
    : { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const response = await fetch(path, { headers, ...options });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const error = await response.json();
      message = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail || error);
    } catch {
      message = await response.text();
    }
    throw new Error(message || response.statusText);
  }
  return response.json();
}

function log(value) {
  qs('#outputLog').textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
}

function now() {
  return new Date().toISOString();
}

function nodeModel(node) {
  return modelResolution(node).model;
}

function modelResolution(node) {
  const nodeModelId = node.model_id && !node.model_id.startsWith('TODO_') ? node.model_id : '';
  const projectOverrideId = state.project?.settings?.model_overrides?.[node.type] || '';
  const compatibleModels = state.models.filter((model) => model.node_type === node.type);
  const catalogDefault = compatibleModels.find((model) => model.enabled) || compatibleModels[0] || null;

  if (nodeModelId) {
    const model = compatibleModels.find((item) => item.id === nodeModelId || item.default_model_id === nodeModelId) || null;
    return {
      model,
      effective_model_id: model?.default_model_id || model?.id || nodeModelId,
      source: 'node override',
      node_model_id: nodeModelId,
      project_override_model_id: projectOverrideId,
      catalog_default_model_id: catalogDefault?.default_model_id || catalogDefault?.id || '',
      override_active: true,
      error: model ? '' : `Model ${nodeModelId} is not registered for ${node.type}.`,
    };
  }

  if (projectOverrideId) {
    const model = compatibleModels.find((item) => item.id === projectOverrideId || item.default_model_id === projectOverrideId) || null;
    return {
      model,
      effective_model_id: model?.default_model_id || model?.id || projectOverrideId,
      source: 'project override',
      node_model_id: '',
      project_override_model_id: projectOverrideId,
      catalog_default_model_id: catalogDefault?.default_model_id || catalogDefault?.id || '',
      override_active: true,
      error: model ? '' : `Project override ${projectOverrideId} is not registered for ${node.type}.`,
    };
  }

  return {
    model: catalogDefault,
    effective_model_id: catalogDefault?.default_model_id || catalogDefault?.id || '',
    source: 'catalog default',
    node_model_id: '',
    project_override_model_id: '',
    catalog_default_model_id: catalogDefault?.default_model_id || catalogDefault?.id || '',
    override_active: false,
    error: catalogDefault ? '' : `No catalog model is registered for ${node.type}.`,
  };
}

function nodeDefByType(node) {
  const model = nodeModel(node) || state.models.find((item) => item.node_type === node.type);
  if (model) return modelToNodeDef(model);
  return LOCAL_FALLBACK_NODE_DEFS.find((item) => item.type === node.type) || allNodeDefs().find((item) => item.type === node.type);
}

function assetUrl(asset) {
  return asset?.wavespeed_url || asset?.public_url || '';
}

function assetById(assetId) {
  return state.project?.assets?.find((asset) => asset.id === assetId);
}

function nodeOutputAssets(node) {
  return (node.output_asset_ids || []).map(assetById).filter(Boolean);
}

function imageAssets() {
  return (state.project?.assets || []).filter((asset) => asset.kind === 'image' && assetUrl(asset));
}

async function loadModels() {
  state.models = await api('/api/models');
}

async function refreshProjectList() {
  state.projects = await api('/api/projects');
  const select = qs('#projectSelect');
  select.innerHTML = '';
  state.projects.forEach((project) => {
    const option = document.createElement('option');
    option.value = project.id;
    option.textContent = project.name || project.id;
    select.appendChild(option);
  });
  if (state.project) select.value = state.project.id;
}

async function loadProject(projectId) {
  if (!projectId) return;
  state.project = await api(`/api/projects/${projectId}`);
  if (!state.project.nodes.some((node) => node.id === state.selectedNodeId)) {
    state.selectedNodeId = null;
  }
  localStorage.setItem('wavespeed_canvas_project_id', state.project.id);
  renderAll();
  log(`Loaded ${state.project.name}`);
}

async function loadSelectedProject() {
  await loadProject(qs('#projectSelect').value);
}

async function createProject() {
  state.project = await api('/api/projects', {
    method: 'POST',
    body: JSON.stringify({ name: 'WaveSpeed Canvas Workflow' }),
  });
  state.selectedNodeId = null;
  localStorage.setItem('wavespeed_canvas_project_id', state.project.id);
  await refreshProjectList();
  renderAll();
  log(state.project);
}

function updateProjectFieldsFromForm() {
  if (!state.project) return;
  state.project.name = qs('#projectName').value || 'Untitled Workflow';
  state.project.description = qs('#projectDescription').value || '';
}

async function saveProject() {
  if (!state.project) return log('No project to save.');
  updateProjectFieldsFromForm();
  state.project = await api(`/api/projects/${state.project.id}`, {
    method: 'PUT',
    body: JSON.stringify(state.project),
  });
  await refreshProjectList();
  renderAll();
  log('Project saved.');
}

async function exportProject() {
  if (!state.project) return log('Create or load a project first.');
  await persistProjectSilently();
  const response = await fetch(`/api/projects/${state.project.id}/export`);
  if (!response.ok) {
    return log(await response.text());
  }
  const blob = await response.blob();
  const disposition = response.headers.get('content-disposition') || '';
  const filename = disposition.match(/filename="?([^"]+)"?/i)?.[1] || `wavespeed-workflow-${state.project.id}.json`;
  downloadBlob(blob, filename);
  log(`Exported ${state.project.name}.`);
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function openImportPicker() {
  qs('#importProjectFile').value = '';
  qs('#importProjectFile').click();
}

async function importProjectFile(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const body = new FormData();
  body.append('file', file);
  try {
    const result = await api('/api/projects/import', { method: 'POST', body });
    state.project = result.project;
    state.selectedNodeId = null;
    localStorage.setItem('wavespeed_canvas_project_id', state.project.id);
    await refreshProjectList();
    renderAll();
    logImportResult('Imported project.', result);
  } catch (error) {
    log(error.message);
  }
}

async function duplicateProject() {
  if (!state.project) return log('Create or load a project first.');
  await persistProjectSilently();
  const name = window.prompt('Duplicate project name', `Copy of ${state.project.name || 'Workflow'}`);
  if (name === null) return;
  try {
    const result = await api(`/api/projects/${state.project.id}/duplicate`, {
      method: 'POST',
      body: JSON.stringify({ name: name || undefined, include_outputs: true, include_run_history: false }),
    });
    state.project = result.project;
    state.selectedNodeId = null;
    localStorage.setItem('wavespeed_canvas_project_id', state.project.id);
    await refreshProjectList();
    renderAll();
    logImportResult('Duplicated project.', result);
  } catch (error) {
    log(error.message);
  }
}

function logImportResult(prefix, result) {
  const warnings = result.warnings?.length ? `\nWarnings:\n${result.warnings.map((item) => `- ${item}`).join('\n')}` : '';
  log(`${prefix} ${result.project?.name || ''}${warnings}`);
}

async function fetchProjectSettings() {
  if (!state.project) return null;
  const settings = await api(`/api/projects/${state.project.id}/settings`);
  state.project.settings = settings;
  return settings;
}

async function openProjectSettings() {
  if (!state.project) return log('Create or load a project first.');
  try {
    await fetchProjectSettings();
    state.settingsOpen = true;
    renderSettingsPanel();
  } catch (error) {
    log(error.message);
  }
}

function closeProjectSettings() {
  state.settingsOpen = false;
  renderSettingsPanel();
}

async function openTemplatesPanel() {
  state.templatesOpen = true;
  try {
    await loadTemplates();
  } catch (error) {
    log(error.message);
  }
  renderTemplatesPanel();
}

function closeTemplatesPanel() {
  state.templatesOpen = false;
  renderTemplatesPanel();
}

async function loadTemplates() {
  state.templates = await api('/api/templates');
}

function renderTemplatesPanel() {
  const panel = qs('#templatesPanel');
  const backdrop = qs('#templatesPanelBackdrop');
  panel.classList.toggle('hidden', !state.templatesOpen);
  backdrop.classList.toggle('hidden', !state.templatesOpen);
  if (!state.templatesOpen) return;

  const list = qs('#templateList');
  if (!state.templates.length) {
    list.innerHTML = '<div class="muted">No templates found.</div>';
    return;
  }
  list.innerHTML = state.templates.map((template) => `
    <article class="template-card">
      <header>
        <div>
          <strong>${escapeHtml(template.name)}</strong>
          <p>${escapeHtml(template.description || '')}</p>
        </div>
        <span class="badge ${template.builtin ? 'ok' : ''}">${template.builtin ? 'built-in' : 'user'}</span>
      </header>
      <div class="badge-row">
        <span class="badge">${escapeHtml(template.category || 'workflow')}</span>
        <span class="badge">${Number(template.nodes?.length || 0)} nodes</span>
        ${(template.tags || []).slice(0, 4).map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join('')}
      </div>
      <div class="template-actions">
        <button type="button" data-template-create="${attr(template.id)}">Create Project</button>
        ${template.builtin ? '' : `<button type="button" data-template-delete="${attr(template.id)}">Delete</button>`}
      </div>
    </article>
  `).join('');

  list.querySelectorAll('[data-template-create]').forEach((button) => {
    button.addEventListener('click', () => createProjectFromTemplate(button.dataset.templateCreate));
  });
  list.querySelectorAll('[data-template-delete]').forEach((button) => {
    button.addEventListener('click', () => deleteUserTemplate(button.dataset.templateDelete));
  });
}

async function createProjectFromTemplate(templateId) {
  const template = state.templates.find((item) => item.id === templateId);
  const name = window.prompt('New project name', template ? `${template.name} Project` : 'New Workflow');
  if (name === null) return;
  try {
    const project = await api(`/api/templates/${templateId}/create-project`, {
      method: 'POST',
      body: JSON.stringify({ name: name || undefined }),
    });
    state.project = project;
    state.selectedNodeId = null;
    localStorage.setItem('wavespeed_canvas_project_id', state.project.id);
    await refreshProjectList();
    closeTemplatesPanel();
    renderAll();
    log(`Created project from template: ${state.project.name}`);
  } catch (error) {
    log(error.message);
  }
}

async function deleteUserTemplate(templateId) {
  if (!window.confirm('Delete this local template?')) return;
  try {
    await api(`/api/templates/${templateId}`, { method: 'DELETE' });
    await loadTemplates();
    renderTemplatesPanel();
    log('Template deleted.');
  } catch (error) {
    log(error.message);
  }
}

async function saveCurrentProjectAsTemplate() {
  if (!state.project) return log('Create or load a project first.');
  await persistProjectSilently();
  const name = window.prompt('Template name', `${state.project.name || 'Workflow'} Template`);
  if (name === null || !name.trim()) return;
  const description = window.prompt('Template description', state.project.description || '') || '';
  const category = window.prompt('Template category', 'image') || 'image';
  const tagText = window.prompt('Tags, comma separated', 'starter') || '';
  try {
    const template = await api(`/api/templates/from-project/${state.project.id}`, {
      method: 'POST',
      body: JSON.stringify({
        name: name.trim(),
        description,
        category,
        tags: tagText.split(',').map((tag) => tag.trim()).filter(Boolean),
        include_outputs: false,
        include_settings: true,
      }),
    });
    await loadTemplates();
    renderTemplatesPanel();
    log(`Saved template: ${template.name}`);
  } catch (error) {
    log(error.message);
  }
}

function projectSettings() {
  if (!state.project.settings) {
    state.project.settings = {
      model_overrides: {},
      cost_guard: {},
    };
  }
  state.project.settings.model_overrides ||= {};
  state.project.settings.cost_guard ||= {};
  return state.project.settings;
}

function renderSettingsPanel() {
  const panel = qs('#settingsPanel');
  const backdrop = qs('#settingsPanelBackdrop');
  panel.classList.toggle('hidden', !state.settingsOpen);
  backdrop.classList.toggle('hidden', !state.settingsOpen);
  if (!state.settingsOpen || !state.project) return;

  const settings = projectSettings();
  const guard = settings.cost_guard || {};
  qs('#costGuardEnabled').checked = !!guard.enabled;
  qs('#costWarnAbove').value = numberInputValue(guard.warn_at_usd_per_run);
  qs('#costMaxSingle').value = numberInputValue(guard.block_at_usd_per_run);
  qs('#costMaxWorkflow').value = numberInputValue(guard.max_workflow_run_usd);
  qs('#blockUnknownCost').checked = !!guard.block_on_unknown_cost;
  renderModelOverrides(settings.model_overrides || {});
}

function numberInputValue(value) {
  return value === null || value === undefined ? '' : String(value);
}

function renderModelOverrides(overrides) {
  const list = qs('#modelOverrideList');
  const runnableGroups = runnableModelGroups();
  if (!runnableGroups.length) {
    list.innerHTML = '<div class="muted">No runnable model overrides are available.</div>';
    return;
  }

  list.innerHTML = runnableGroups.map((group) => {
    const current = overrides[group.node_type] || '';
    return `
      <div class="override-row" data-node-type="${attr(group.node_type)}">
        <div class="override-copy">
          <strong>${escapeHtml(group.label)}</strong>
          <span>Default: ${escapeHtml(group.default_model_id || group.models[0]?.id || 'none')}</span>
        </div>
        <select data-setting-override="${attr(group.node_type)}">
          <option value="">Use catalog default</option>
          ${group.models.map((model) => {
            const modelId = model.default_model_id || model.id;
            return `<option value="${attr(modelId)}" ${modelId === current ? 'selected' : ''}>${escapeHtml(modelId)}</option>`;
          }).join('')}
        </select>
        <button type="button" data-reset-override="${attr(group.node_type)}">Reset</button>
      </div>
    `;
  }).join('');

  list.querySelectorAll('[data-reset-override]').forEach((button) => {
    button.addEventListener('click', () => {
      const select = list.querySelector(`[data-setting-override="${cssEscape(button.dataset.resetOverride)}"]`);
      if (select) select.value = '';
    });
  });
}

function runnableModelGroups() {
  const groups = new Map();
  state.models
    .filter((model) => model.enabled && model.default_model_id && model.node_type !== 'upload_image')
    .forEach((model) => {
      const existing = groups.get(model.node_type) || {
        node_type: model.node_type,
        label: model.label || model.display_name || model.node_type,
        default_model_id: model.default_model_id,
        models: [],
      };
      existing.models.push(model);
      groups.set(model.node_type, existing);
    });
  return Array.from(groups.values());
}

function settingsPayloadFromPanel() {
  const modelOverrides = {};
  qs('#modelOverrideList').querySelectorAll('[data-setting-override]').forEach((select) => {
    if (select.value) {
      modelOverrides[select.dataset.settingOverride] = select.value;
    }
  });

  return {
    model_overrides: modelOverrides,
    cost_guard: {
      enabled: qs('#costGuardEnabled').checked,
      warn_at_usd_per_run: optionalNumber('#costWarnAbove'),
      block_at_usd_per_run: optionalNumber('#costMaxSingle'),
      max_workflow_run_usd: optionalNumber('#costMaxWorkflow'),
      block_on_unknown_cost: qs('#blockUnknownCost').checked,
    },
  };
}

function optionalNumber(selector) {
  const value = qs(selector).value.trim();
  return value === '' ? null : Number(value);
}

async function saveProjectSettings() {
  if (!state.project) return log('Create or load a project first.');
  try {
    const settings = await api(`/api/projects/${state.project.id}/settings`, {
      method: 'PUT',
      body: JSON.stringify(settingsPayloadFromPanel()),
    });
    state.project.settings = settings;
    closeProjectSettings();
    renderAll();
    log('Project settings saved.');
  } catch (error) {
    log(error.message);
  }
}

async function persistProjectSilently() {
  if (!state.project) return;
  updateProjectFieldsFromForm();
  state.project = await api(`/api/projects/${state.project.id}`, {
    method: 'PUT',
    body: JSON.stringify(state.project),
  });
  await refreshProjectList();
}

function renderNodeLibrary() {
  const library = qs('#nodeLibrary');
  library.innerHTML = '';
  allNodeDefs().forEach((def) => {
    const item = document.createElement('div');
    const enabled = def.enabled !== false;
    item.className = `library-item ${enabled ? 'enabled' : 'disabled'}`;
    item.innerHTML = `
      <strong>${escapeHtml(def.title)}</strong>
      <div class="badge-row">
        <span class="badge">${escapeHtml(def.category)}</span>
        <span class="badge">${escapeHtml(def.output_kind || 'local')}</span>
        <span class="badge ${enabled ? 'ok' : 'muted-badge'}">${enabled ? 'enabled' : 'disabled'}</span>
      </div>
      <div class="library-meta">${escapeHtml(costLabel(def))} - ${escapeHtml(def.verification_status || 'local')}</div>
      <p>${escapeHtml(def.description)}</p>
      ${def.enabled_reason && !enabled ? `<div class="disabled-reason">${escapeHtml(def.enabled_reason)}</div>` : ''}
      <button type="button" ${enabled ? '' : 'disabled'}>${enabled ? 'Add Node' : 'Coming Soon'}</button>
    `;
    item.querySelector('button').addEventListener('click', () => {
      if (enabled) addNode(def);
    });
    library.appendChild(item);
  });
}

function allNodeDefs() {
  if (!state.models.length) return LOCAL_FALLBACK_NODE_DEFS;
  return state.models.map(modelToNodeDef);
}

function modelToNodeDef(model) {
  return {
    id: model.id,
    title: model.label,
    type: model.node_type,
    category: model.category,
    model_id: model.id,
    description: model.description,
    runnable: model.enabled && model.node_type !== 'upload_image',
    enabled: model.enabled,
    upload: model.node_type === 'upload_image',
    output_kind: model.output_kind,
    estimated_base_cost_usd: model.estimated_base_cost_usd,
    cost_unit: model.cost_unit,
    pricing_note: model.pricing_note,
    verification_status: model.verification_status,
    enabled_reason: model.enabled_reason,
    defaults: defaultInputsFromFields(model.fields || []),
  };
}

function defaultInputsFromFields(fields) {
  const inputs = {};
  fields.forEach((field) => {
    if (field.default !== null && field.default !== undefined) {
      inputs[field.name] = field.default;
    }
  });
  if (fields.some((field) => field.name === 'prompt') && !inputs.prompt) {
    inputs.prompt = 'A clean modern product poster, studio lighting';
  }
  return inputs;
}

function costLabel(item) {
  const estimate = item?.estimated_base_cost_usd;
  if (estimate === null || estimate === undefined) return 'cost unknown';
  const unit = item.cost_unit || 'run';
  return estimate === 0 ? '$0' : `from $${Number(estimate).toFixed(3)}/${unit}`;
}

function outputKindFromNodeType(nodeType) {
  if (['image_to_video', 'text_to_video', 'start_end_to_video', 'reference_to_video', 'video_extend', 'video_effect', 'talking_avatar', 'lip_sync', 'portrait_transfer'].includes(nodeType)) {
    return 'video';
  }
  if (['text_to_speech', 'text_to_audio'].includes(nodeType)) return 'audio';
  if (['text_to_image', 'image_to_image', 'upload_image', 'reference_to_image', 'upscale_image', 'remove_background', 'remove_object'].includes(nodeType)) {
    return 'image';
  }
  return 'other';
}

function outputKindFromUrl(url) {
  const clean = String(url || '').split('?')[0].toLowerCase();
  if (/\.(mp4|mov|webm)$/.test(clean)) return 'video';
  if (/\.(mp3|wav|m4a|ogg)$/.test(clean)) return 'audio';
  if (/\.(png|jpg|jpeg|webp|gif)$/.test(clean)) return 'image';
  return '';
}

function renderCostNote(item) {
  if (!item) return '';
  return `
    <div class="node-cost">
      <span>${escapeHtml(costLabel(item))}</span>
      ${item.pricing_note ? `<small>${escapeHtml(item.pricing_note)}</small>` : ''}
    </div>
  `;
}

function renderModelDetails(node, resolution, item, outputKind) {
  if (node.type === 'upload_image') {
    return renderCostNote(item);
  }
  const effectiveModelId = resolution.effective_model_id || item?.model_id || item?.id || 'No model';
  const sourceClass = resolution.source === 'project override' ? 'ok' : '';
  return `
    <div class="node-cost">
      <span>Model: ${escapeHtml(effectiveModelId)}</span>
      <small>Cost: ${escapeHtml(costLabel(item))}</small>
      <small>Output: ${escapeHtml(outputKind)}</small>
      <small>Source: <strong class="${sourceClass}">${escapeHtml(resolution.source)}</strong></small>
      ${resolution.project_override_model_id ? `<small>Project override: ${escapeHtml(resolution.project_override_model_id)}</small>` : ''}
      ${resolution.error ? `<small>${escapeHtml(resolution.error)}</small>` : ''}
      ${item?.pricing_note ? `<small>${escapeHtml(item.pricing_note)}</small>` : ''}
    </div>
  `;
}

function addNode(def) {
  if (!state.project) return log('Create or load a project first.');
  if (def.enabled === false) return log('This node is disabled until the model is ready.');
  const index = state.project.nodes.length;
  const node = {
    id: `node_${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`,
    type: def.type,
    title: def.title,
    model_id: null,
    estimated_base_cost_usd: def.estimated_base_cost_usd ?? null,
    x: 80 + (index % 3) * 300,
    y: 80 + Math.floor(index / 3) * 360,
    inputs: { ...def.defaults },
    output_asset_ids: [],
    output_urls: [],
    last_run: {},
    status: 'idle',
    error_message: null,
    created_at: now(),
    updated_at: now(),
  };
  state.project.nodes.push(node);
  state.selectedNodeId = node.id;
  renderAll();
}

function renderAll() {
  renderLayoutState();
  renderProjectPanel();
  renderCanvas();
  renderAssets();
  renderWorkflowPanels();
  renderSettingsPanel();
  renderTemplatesPanel();
  updateWorkflowButtons();
}

function loadLayoutPreference() {
  try {
    const saved = JSON.parse(localStorage.getItem('wavespeed_canvas_layout') || '{}');
    state.ui.leftPanelCollapsed = !!saved.leftPanelCollapsed;
    state.ui.rightPanelCollapsed = !!saved.rightPanelCollapsed;
  } catch {
    state.ui.leftPanelCollapsed = false;
    state.ui.rightPanelCollapsed = false;
  }
}

function saveLayoutPreference() {
  localStorage.setItem('wavespeed_canvas_layout', JSON.stringify(state.ui));
}

function renderLayoutState() {
  const layout = qs('#appLayout');
  if (!layout) return;
  layout.classList.toggle('left-collapsed', state.ui.leftPanelCollapsed);
  layout.classList.toggle('right-collapsed', state.ui.rightPanelCollapsed);

  const nodesBtn = qs('#toggleNodesBtn');
  const inspectorBtn = qs('#toggleInspectorBtn');
  if (nodesBtn) {
    nodesBtn.textContent = state.ui.leftPanelCollapsed ? 'Show Nodes' : 'Hide Nodes';
    nodesBtn.setAttribute('aria-pressed', String(state.ui.leftPanelCollapsed));
  }
  if (inspectorBtn) {
    inspectorBtn.textContent = state.ui.rightPanelCollapsed ? 'Show Inspector' : 'Hide Inspector';
    inspectorBtn.setAttribute('aria-pressed', String(state.ui.rightPanelCollapsed));
  }
}

function toggleLeftPanel() {
  state.ui.leftPanelCollapsed = !state.ui.leftPanelCollapsed;
  saveLayoutPreference();
  renderLayoutState();
  window.requestAnimationFrame(renderConnections);
}

function toggleRightPanel() {
  state.ui.rightPanelCollapsed = !state.ui.rightPanelCollapsed;
  saveLayoutPreference();
  renderLayoutState();
  window.requestAnimationFrame(renderConnections);
}

function renderProjectPanel() {
  qs('#projectName').value = state.project?.name || '';
  qs('#projectDescription').value = state.project?.description || '';
}

function renderCanvas() {
  const canvas = qs('#canvas');
  canvas.querySelectorAll('.canvas-node').forEach((el) => el.remove());
  const layer = ensureConnectionLayer();
  layer.innerHTML = connectionDefs();
  qs('.canvas-help').classList.toggle('hidden', !!state.project?.nodes?.length);
  if (!state.project) return;

  state.project.nodes.forEach((node) => {
    const card = document.createElement('article');
    card.className = `canvas-node status-${node.status} ${node.id === state.selectedNodeId ? 'selected' : ''}`;
    card.style.left = `${node.x}px`;
    card.style.top = `${node.y}px`;
    card.dataset.nodeId = node.id;
    card.innerHTML = nodeCardHtml(node);
    wireNodeCard(card, node);
    canvas.appendChild(card);
  });
  renderConnections();
}

function nodeCardHtml(node) {
  const def = nodeDefByType(node) || {};
  const resolution = modelResolution(node);
  const model = resolution.model;
  const isRunnable = !!model?.enabled && def.runnable !== false;
  const outputKind = model?.output_kind || def.output_kind || outputKindFromNodeType(node.type);
  return `
    <header class="node-card-header">
      <button type="button" class="node-drag-handle" data-drag-handle title="Move node">Move</button>
      <input class="node-title-input" data-field="title" value="${attr(node.title)}" />
      <span class="node-status">${escapeHtml(node.status)}</span>
    </header>
    <div class="node-meta">${escapeHtml(model?.label || node.model_id || def.category || node.type)}</div>
    <div class="badge-row">
      <span class="badge">${escapeHtml(model?.category || def.category || node.type)}</span>
      <span class="badge">${escapeHtml(outputKind)}</span>
      <span class="badge ${model?.enabled ? 'ok' : 'muted-badge'}">${model?.enabled ? 'enabled' : 'disabled'}</span>
      <span class="badge">${escapeHtml(model?.verification_status || def.verification_status || 'local')}</span>
    </div>
    ${renderModelDetails(node, resolution, model || def, outputKind)}
    ${renderNodeFields(node)}
    ${renderUploadControls(node, def)}
    ${renderPlaceholderNotice(node, def, model)}
    <div class="node-actions">
      ${isRunnable ? '<button type="button" data-action="run">Run</button>' : ''}
      ${canBranchFromNode(node) ? '<button type="button" data-action="branch">Branch from output</button>' : ''}
      ${canBranchToVideo(node) ? '<button type="button" data-action="branch-video">Animate output</button>' : ''}
      <button type="button" data-action="save">Save</button>
      <button type="button" data-action="delete">Delete</button>
    </div>
    ${node.error_message ? `<div class="node-error">${escapeHtml(node.error_message)}</div>` : ''}
    ${renderOutputPreview(node)}
  `;
}

function renderNodeFields(node) {
  const model = nodeModel(node);
  const fields = model?.fields || placeholderFields(node);
  if (!fields.length) return '';
  return fields.map((field) => renderField(node, field)).join('');
}

function placeholderFields(node) {
  if (['upscale_image', 'remove_background'].includes(node.type)) {
    return [{ name: 'image', type: 'asset_url', required: true, description: 'Source image' }];
  }
  if (node.type === 'image_to_video') {
    return [
      { name: 'prompt', type: 'string', required: true, description: 'Motion prompt' },
      { name: 'image', type: 'asset_url', required: true, description: 'Source image' },
      { name: 'duration', type: 'integer', required: false, description: 'Duration' },
    ];
  }
  return [];
}

function renderField(node, field) {
  const value = node.inputs?.[field.name] ?? field.default ?? '';
  const label = `${field.name}${field.required ? ' *' : ''}`;
  if (field.name === 'image' || field.name.endsWith('_image') || field.type === 'asset_url') {
    return `
      <label>
        ${escapeHtml(label)}
        <select data-input="${attr(field.name)}">
          <option value="">Choose image asset</option>
          ${imageAssets().map((asset) => {
            const url = assetUrl(asset);
            return `<option value="${attr(url)}" ${url === value ? 'selected' : ''}>${escapeHtml(asset.filename)}</option>`;
          }).join('')}
        </select>
      </label>
    `;
  }
  if (field.type === 'boolean') {
    return `
      <label class="checkbox-field">
        <input data-input="${attr(field.name)}" type="checkbox" ${value ? 'checked' : ''} />
        ${escapeHtml(label)}
      </label>
    `;
  }
  if (field.type === 'select' && Array.isArray(field.options)) {
    return `
      <label>
        ${escapeHtml(label)}
        <select data-input="${attr(field.name)}">
          ${field.options.map((option) => {
            const optionValue = typeof option === 'object' ? option.value : option;
            const optionLabel = typeof option === 'object' ? option.label || option.value : option;
            return `<option value="${attr(optionValue)}" ${optionValue === value ? 'selected' : ''}>${escapeHtml(optionLabel)}</option>`;
          }).join('')}
        </select>
      </label>
    `;
  }
  if (field.name === 'prompt' || field.type === 'textarea') {
    return `
      <label>
        ${escapeHtml(label)}
        <textarea data-input="${attr(field.name)}" rows="4">${escapeHtml(value)}</textarea>
      </label>
    `;
  }
  return `
    <label>
      ${escapeHtml(label)}
      <input data-input="${attr(field.name)}" type="${inputTypeForField(field)}" value="${attr(value)}" />
    </label>
  `;
}

function inputTypeForField(field) {
  if (field.type === 'number' || field.type === 'integer') return 'number';
  if (field.type === 'url') return 'url';
  return 'text';
}

function renderUploadControls(node, def) {
  if (!def.upload) return '';
  return `
    <div class="upload-box">
      <input type="file" accept="image/*" data-upload-file />
      <label class="row compact">
        <input type="checkbox" data-upload-wavespeed />
        Upload to WaveSpeed
      </label>
      <button type="button" data-action="upload">Upload Asset</button>
    </div>
  `;
}

function renderPlaceholderNotice(node, def, model) {
  if (def.upload || model?.enabled || def.runnable) return '';
  return `<div class="placeholder-note">${escapeHtml(model?.enabled_reason || def.enabled_reason || 'Disabled until this model is verified for execution.')}</div>`;
}

function renderOutputPreview(node) {
  const assets = nodeOutputAssets(node);
  const fallbackUrls = (node.output_urls || []).filter((url) => !assets.some((asset) => assetUrl(asset) === url));
  if (!assets.length && !fallbackUrls.length) return '';
  return `
    <div class="node-preview-list">
      ${assets.map((asset) => {
        const url = assetUrl(asset);
        return mediaPreviewHtml(url, asset.kind, asset.filename);
      }).join('')}
      ${fallbackUrls.map((url) => mediaPreviewHtml(url, outputKindFromUrl(url) || outputKindFromNodeType(node.type), 'Generated output')).join('')}
    </div>
  `;
}

function mediaPreviewHtml(url, kind, label) {
  if (!url) return '';
  const safeUrl = attr(url);
  const safeLabel = escapeHtml(label || url);
  const media = kind === 'video'
    ? `<video class="node-preview media-preview" src="${safeUrl}" controls></video>`
    : kind === 'audio'
      ? `<audio class="audio-preview" src="${safeUrl}" controls></audio>`
      : `<a href="${safeUrl}" target="_blank"><img class="node-preview" src="${safeUrl}" alt="${attr(label || 'Generated output')}" /></a>`;
  return `
    <div class="output-item">
      ${media}
      <div class="output-actions">
        <span class="output-link">${safeLabel}</span>
        <button type="button" data-action="copy-url" data-url="${safeUrl}">Copy URL</button>
        <a href="${safeUrl}" target="_blank">Open</a>
        <a href="${safeUrl}" download>Download</a>
      </div>
    </div>
  `;
}

function wireNodeCard(card, node) {
  card.addEventListener('click', (event) => {
    if (event.target.closest('button, input, textarea, select, a')) return;
    selectNode(node.id);
  });

  card.querySelectorAll('[data-input]').forEach((input) => {
    input.addEventListener('input', () => {
      const name = input.dataset.input;
      node.inputs[name] = parseFieldValue(input.value, input.type, input.checked);
      node.updated_at = now();
    });
    input.addEventListener('change', () => {
      const name = input.dataset.input;
      node.inputs[name] = parseFieldValue(input.value, input.type, input.checked);
      node.updated_at = now();
    });
  });

  card.querySelector('[data-field="title"]')?.addEventListener('input', (event) => {
    node.title = event.target.value;
    node.updated_at = now();
  });

  card.querySelector('[data-action="save"]')?.addEventListener('click', saveProject);
  card.querySelector('[data-action="delete"]')?.addEventListener('click', () => deleteNode(node.id));
  card.querySelector('[data-action="run"]')?.addEventListener('click', () => runNode(node.id));
  card.querySelector('[data-action="upload"]')?.addEventListener('click', () => uploadFromNode(card, node));
  card.querySelector('[data-action="branch"]')?.addEventListener('click', () => branchFromNode(node.id));
  card.querySelector('[data-action="branch-video"]')?.addEventListener('click', () => branchToVideoFromNode(node.id));
  card.querySelectorAll('[data-action="copy-url"]').forEach((button) => {
    button.addEventListener('click', () => copyText(button.dataset.url || ''));
  });
  setupNodeDrag(card, node);
}

function selectNode(nodeId) {
  state.selectedNodeId = nodeId;
  renderCanvas();
  renderWorkflowPanels();
  updateWorkflowButtons();
}

function parseFieldValue(value, type, checked = false) {
  if (type === 'checkbox') return checked;
  if (type === 'number') {
    const number = Number(value);
    return Number.isFinite(number) ? number : value;
  }
  return value;
}

async function copyText(value) {
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    log('Copied output URL.');
  } catch {
    log(value);
  }
}

function deleteNode(nodeId) {
  state.project.nodes = state.project.nodes.filter((node) => node.id !== nodeId);
  state.project.edges = (state.project.edges || []).filter((edge) => edge.source_node_id !== nodeId && edge.target_node_id !== nodeId);
  if (state.selectedNodeId === nodeId) {
    state.selectedNodeId = null;
  }
  renderAll();
}

function setupNodeDrag(card, node) {
  const handle = card.querySelector('[data-drag-handle]');
  if (!handle) return;

  handle.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    card.setPointerCapture(event.pointerId);
    card.classList.add('dragging');
    const startClientX = event.clientX;
    const startClientY = event.clientY;
    const startX = Number(node.x) || 0;
    const startY = Number(node.y) || 0;

    const onMove = (moveEvent) => {
      const nextX = Math.max(12, startX + moveEvent.clientX - startClientX);
      const nextY = Math.max(12, startY + moveEvent.clientY - startClientY);
      node.x = Math.round(nextX);
      node.y = Math.round(nextY);
      node.updated_at = now();
      card.style.left = `${node.x}px`;
      card.style.top = `${node.y}px`;
      renderConnections();
    };

    const onEnd = () => {
      card.classList.remove('dragging');
      if (card.hasPointerCapture(event.pointerId)) {
        card.releasePointerCapture(event.pointerId);
      }
      card.removeEventListener('pointermove', onMove);
      card.removeEventListener('pointerup', onEnd);
      card.removeEventListener('pointercancel', onEnd);
      renderConnections();
    };

    card.addEventListener('pointermove', onMove);
    card.addEventListener('pointerup', onEnd);
    card.addEventListener('pointercancel', onEnd);
  });
}

function canBranchFromNode(node) {
  return ['text_to_image', 'image_to_image'].includes(node.type) && !!primaryOutputUrl(node);
}

function canBranchToVideo(node) {
  return ['text_to_image', 'image_to_image', 'upload_image', 'remove_background', 'upscale_image'].includes(node.type)
    && !!primaryOutputUrl(node)
    && state.models.some((model) => model.node_type === 'image_to_video' && model.enabled);
}

function primaryOutputUrl(node) {
  const asset = nodeOutputAssets(node).find((item) => item.kind === 'image' && assetUrl(item));
  return assetUrl(asset) || (node.output_urls || []).find(Boolean) || '';
}

function branchFromNode(sourceNodeId) {
  const sourceNode = state.project.nodes.find((node) => node.id === sourceNodeId);
  const outputUrl = primaryOutputUrl(sourceNode || {});
  if (!sourceNode || !outputUrl) return log('Run this image node before branching.');

  const remixModel = state.models.find((model) => model.node_type === 'image_to_image' && model.enabled);
  if (!remixModel) return log('No enabled remix model is available.');
  const remixDef = modelToNodeDef(remixModel);
  const childNode = {
    id: `node_${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`,
    type: remixDef.type,
    title: 'Remix Image',
    model_id: null,
    estimated_base_cost_usd: remixDef.estimated_base_cost_usd ?? null,
    x: Math.round((Number(sourceNode.x) || 80) + CARD_GAP_X),
    y: Math.round((Number(sourceNode.y) || 80) + CARD_BRANCH_OFFSET_Y),
    inputs: {
      ...remixDef.defaults,
      image: outputUrl,
      prompt: 'Remix this image into a fresh campaign variation',
    },
    output_asset_ids: [],
    output_urls: [],
    last_run: {},
    status: 'idle',
    error_message: null,
    created_at: now(),
    updated_at: now(),
  };

  const edge = {
    id: `edge_${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`,
    source_node_id: sourceNode.id,
    target_node_id: childNode.id,
    source_handle: 'output',
    target_handle: 'image',
    target_input: 'image',
  };

  state.project.nodes.push(childNode);
  state.project.edges = [...(state.project.edges || []), edge];
  renderAll();
  log('Created remix branch. Save project to persist it.');
}

function branchToVideoFromNode(sourceNodeId) {
  const sourceNode = state.project.nodes.find((node) => node.id === sourceNodeId);
  const outputUrl = primaryOutputUrl(sourceNode || {});
  const videoModel = state.models.find((model) => model.node_type === 'image_to_video' && model.enabled);
  if (!sourceNode || !outputUrl) return log('Run this image node before animating it.');
  if (!videoModel) return log('No enabled image-to-video model is available.');

  const videoDef = modelToNodeDef(videoModel);
  const childNode = {
    id: `node_${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`,
    type: videoDef.type,
    title: 'Image to Video',
    model_id: null,
    estimated_base_cost_usd: videoDef.estimated_base_cost_usd ?? null,
    x: Math.round((Number(sourceNode.x) || 80) + CARD_GAP_X),
    y: Math.round((Number(sourceNode.y) || 80) + CARD_BRANCH_OFFSET_Y + 120),
    inputs: {
      ...videoDef.defaults,
      image: outputUrl,
      prompt: 'Slow cinematic camera move',
    },
    output_asset_ids: [],
    output_urls: [],
    last_run: {},
    status: 'idle',
    error_message: null,
    created_at: now(),
    updated_at: now(),
  };

  const edge = {
    id: `edge_${crypto.randomUUID().replaceAll('-', '').slice(0, 12)}`,
    source_node_id: sourceNode.id,
    target_node_id: childNode.id,
    source_handle: 'output',
    target_handle: 'image',
    target_input: 'image',
  };

  state.project.nodes.push(childNode);
  state.project.edges = [...(state.project.edges || []), edge];
  renderAll();
  log('Created image-to-video branch. Save project to persist it.');
}

function ensureConnectionLayer() {
  const canvas = qs('#canvas');
  let layer = canvas.querySelector('.connection-layer');
  if (!layer) {
    layer = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    layer.classList.add('connection-layer');
    canvas.prepend(layer);
  }
  return layer;
}

function connectionDefs() {
  return `
    <defs>
      <marker id="arrowhead" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
        <path d="M 0 0 L 10 4 L 0 8 z" class="connection-arrow"></path>
      </marker>
    </defs>
  `;
}

function renderConnections() {
  const layer = ensureConnectionLayer();
  const canvas = qs('#canvas');
  layer.setAttribute('width', canvas.scrollWidth);
  layer.setAttribute('height', canvas.scrollHeight);
  layer.setAttribute('viewBox', `0 0 ${canvas.scrollWidth} ${canvas.scrollHeight}`);
  layer.innerHTML = connectionDefs();

  (state.project?.edges || []).forEach((edge) => {
    const sourceCard = canvas.querySelector(`[data-node-id="${cssEscape(edge.source_node_id)}"]`);
    const targetCard = canvas.querySelector(`[data-node-id="${cssEscape(edge.target_node_id)}"]`);
    if (!sourceCard || !targetCard) return;

    const startX = sourceCard.offsetLeft + sourceCard.offsetWidth;
    const startY = sourceCard.offsetTop + sourceCard.offsetHeight / 2;
    const endX = targetCard.offsetLeft;
    const endY = targetCard.offsetTop + targetCard.offsetHeight / 2;
    const curve = Math.max(70, Math.abs(endX - startX) * 0.45);

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('class', 'connection-path');
    path.setAttribute('d', `M ${startX} ${startY} C ${startX + curve} ${startY}, ${endX - curve} ${endY}, ${endX} ${endY}`);
    path.setAttribute('marker-end', 'url(#arrowhead)');
    layer.appendChild(path);
  });
}

function cssEscape(value) {
  if (window.CSS?.escape) return CSS.escape(value);
  return String(value).replace(/"/g, '\\"');
}

async function runNode(nodeId) {
  let node = state.project.nodes.find((item) => item.id === nodeId);
  if (!node) return;
  node.status = 'running';
  node.error_message = null;
  const model = nodeModel(node);
  if (model?.enabled && node.model_id?.startsWith('TODO_')) {
    node.model_id = model.id;
  }
  renderCanvas();
  try {
    await persistProjectSilently();
    node = state.project.nodes.find((item) => item.id === nodeId);
    if (!node) return;
    const canRun = await confirmEstimatedRunCost(node);
    if (!canRun) {
      node.status = 'idle';
      renderCanvas();
      return;
    }
    const result = await api('/api/runs/node', {
      method: 'POST',
      body: JSON.stringify({
        project_id: state.project.id,
        node_id: node.id,
        node_type: node.type,
        model_id: node.model_id,
        inputs: node.inputs,
        save_to_project: true,
      }),
    });
    state.project = await api(`/api/projects/${state.project.id}`);
    renderAll();
    log(result);
  } catch (error) {
    node.status = 'error';
    node.error_message = error.message;
    renderCanvas();
    log(error.message);
  }
}

async function confirmEstimatedRunCost(node) {
  try {
    const estimate = await api('/api/runs/estimate', {
      method: 'POST',
      body: JSON.stringify({
        project_id: state.project.id,
        node_id: node.id,
        node_type: node.type,
        model_id: node.model_id,
      }),
    });
    node.estimated_base_cost_usd = estimate.estimated_base_cost_usd;
    if (estimate.blocked) {
      node.error_message = estimate.cost_guard_message || 'Run blocked by local estimated cost guard.';
      log(node.error_message);
      return false;
    }
    if (estimate.requires_confirmation) {
      return window.confirm(`${estimate.cost_guard_message}\n\n${estimate.warning}`);
    }
  } catch (error) {
    log(error.message);
  }
  return true;
}

async function uploadFromNode(card, node) {
  const fileInput = card.querySelector('[data-upload-file]');
  if (!fileInput.files.length) return log('Choose an image file first.');

  node.status = 'running';
  node.error_message = null;
  renderCanvas();

  const body = new FormData();
  body.append('file', fileInput.files[0]);
  const uploadToWaveSpeed = card.querySelector('[data-upload-wavespeed]')?.checked || false;

  try {
    const asset = await api(`/api/assets/upload?upload_to_wavespeed=${uploadToWaveSpeed}`, {
      method: 'POST',
      body,
    });
    state.project.assets.push(asset);
    node.inputs.asset_id = asset.id;
    node.inputs.image = assetUrl(asset);
    node.output_asset_ids = [asset.id];
    node.status = 'success';
    node.updated_at = now();
    await persistProjectSilently();
    renderAll();
    log(asset);
  } catch (error) {
    node.status = 'error';
    node.error_message = error.message;
    renderCanvas();
    log(error.message);
  }
}

function selectedNode() {
  return state.project?.nodes?.find((node) => node.id === state.selectedNodeId) || null;
}

async function previewWorkflowPlan() {
  if (!state.project) return log('Create or load a project first.');
  try {
    await persistProjectSilently();
    const plan = await api(`/api/workflows/${state.project.id}/plan?mode=whole_graph`);
    renderWorkflowPlan(plan);
    renderWorkflowMessages(plan.warnings || [], plan.errors || []);
    log(plan);
  } catch (error) {
    renderWorkflowMessages([], [{ message: error.message }]);
    log(error.message);
  }
}

async function runSelectedWorkflowNode() {
  const node = selectedNode();
  if (!node) return showSelectNodeError();
  if (!await confirmWorkflowPlan('selected', node.id)) return;
  await runWorkflowRequest(`/api/workflows/${state.project.id}/run-selected`, {
    method: 'POST',
    body: JSON.stringify({ node_id: node.id }),
  });
}

async function runFromSelectedNode() {
  const node = selectedNode();
  if (!node) return showSelectNodeError();
  if (!await confirmWorkflowPlan('from_node', node.id)) return;
  await runWorkflowRequest(`/api/workflows/${state.project.id}/run-from-node/${node.id}`, {
    method: 'POST',
  });
}

async function runWholeGraph() {
  if (!state.project) return log('Create or load a project first.');
  if (!await confirmWorkflowPlan('whole_graph')) return;
  await runWorkflowRequest(`/api/workflows/${state.project.id}/run-all`, {
    method: 'POST',
  });
}

async function confirmWorkflowPlan(mode, nodeId = '') {
  await persistProjectSilently();
  const params = new URLSearchParams({ mode });
  if (nodeId) params.set('node_id', nodeId);
  const plan = await api(`/api/workflows/${state.project.id}/plan?${params}`);
  renderWorkflowPlan(plan);
  renderWorkflowMessages(plan.warnings || [], plan.errors || []);
  if (plan.errors?.length) {
    log(plan);
    return false;
  }
  if (plan.cost_guard?.blocked || (plan.steps || []).some((step) => step.cost_guard?.blocked)) {
    renderWorkflowMessages(plan.warnings || [], [{
      message: plan.cost_guard?.message || 'Workflow blocked by local estimated cost guard.',
    }]);
    log(plan);
    return false;
  }
  const needsConfirmation = plan.cost_guard?.requires_confirmation
    || (plan.steps || []).some((step) => step.cost_guard?.requires_confirmation);
  if (needsConfirmation) {
    return window.confirm(`${plan.cost_guard?.message || 'Workflow cost warning.'}\n\n${plan.pricing_note || ''}`);
  }
  return true;
}

async function runWorkflowRequest(path, options) {
  if (!state.project) return log('Create or load a project first.');
  setWorkflowRunning(true);
  renderWorkflowMessages([{ message: 'Workflow running...' }], []);
  try {
    await persistProjectSilently();
    const response = await api(path, options);
    if (response.project) {
      state.project = response.project;
      if (!state.project.nodes.some((node) => node.id === state.selectedNodeId)) {
        state.selectedNodeId = null;
      }
    }
    renderAll();
    renderWorkflowMessages(response.run?.warnings || [], response.run?.errors || []);
    renderRunHistory(state.project?.runs || []);
    log(response);
  } catch (error) {
    renderWorkflowMessages([], [{ message: error.message }]);
    log(error.message);
  } finally {
    setWorkflowRunning(false);
  }
}

async function refreshRunHistory() {
  if (!state.project) return log('Create or load a project first.');
  try {
    const runs = await api(`/api/workflows/${state.project.id}/runs`);
    state.project.runs = runs;
    renderRunHistory(runs);
    log(`Loaded ${runs.length} workflow run${runs.length === 1 ? '' : 's'}.`);
  } catch (error) {
    renderWorkflowMessages([], [{ message: error.message }]);
    log(error.message);
  }
}

function showSelectNodeError() {
  renderWorkflowMessages([], [{ message: 'Select a node first.' }]);
  log('Select a node first.');
}

function renderWorkflowPanels() {
  const node = selectedNode();
  qs('#selectedNodeLabel').textContent = node ? `Selected: ${node.title}` : 'No node selected.';
  renderRunHistory(state.project?.runs || []);
}

function renderWorkflowPlan(plan) {
  const panel = qs('#workflowPlan');
  const steps = plan?.steps || [];
  if (!steps.length) {
    panel.className = 'workflow-panel muted';
    panel.textContent = 'No runnable steps in plan.';
    return;
  }
  panel.className = 'workflow-panel';
  const summary = `
    <div class="workflow-step workflow-summary ${escapeHtml(plan.cost_guard?.status || 'ok')}">
      <strong>Total: ${escapeHtml(workflowTotalLabel(plan))}</strong>
      <span>Guard: ${escapeHtml(plan.cost_guard?.status || 'ok')}</span>
      ${plan.cost_guard?.message ? `<small>${escapeHtml(plan.cost_guard.message)}</small>` : ''}
      ${plan.pricing_note ? `<small>${escapeHtml(plan.pricing_note)}</small>` : ''}
    </div>
  `;
  panel.innerHTML = summary + steps.map((step) => `
    <div class="workflow-step">
      <strong>${step.index + 1}. ${escapeHtml(step.display_name || step.node_id)}</strong>
      <span>${escapeHtml(step.node_type)} - ${escapeHtml(step.status)} - ${escapeHtml(costLabel(step))}</span>
      <small>${escapeHtml(step.effective_model_id || step.model_id || 'no model')} (${escapeHtml(step.model_source || 'node')})</small>
      <small>${escapeHtml(step.resolved_input_keys?.join(', ') || 'no inputs')}</small>
      ${step.cost_guard?.message ? `<small>${escapeHtml(step.cost_guard.message)}</small>` : ''}
    </div>
  `).join('');
}

function workflowTotalLabel(plan) {
  if (plan.estimated_total_cost_usd === null || plan.estimated_total_cost_usd === undefined) {
    if (plan.estimated_known_cost_usd) {
      return `known from $${Number(plan.estimated_known_cost_usd).toFixed(3)}`;
    }
    return 'cost unknown';
  }
  return `from $${Number(plan.estimated_total_cost_usd).toFixed(3)}`;
}

function renderWorkflowMessages(warnings = [], errors = []) {
  const panel = qs('#workflowMessages');
  if (!warnings.length && !errors.length) {
    panel.className = 'workflow-panel muted';
    panel.textContent = 'No workflow messages.';
    return;
  }
  panel.className = 'workflow-panel';
  const errorHtml = errors.map((item) => messageHtml(item, 'error')).join('');
  const warningHtml = warnings.map((item) => messageHtml(item, 'warning')).join('');
  panel.innerHTML = `${errorHtml}${warningHtml}`;
}

function messageHtml(item, kind) {
  return `
    <div class="workflow-message ${kind}">
      <strong>${escapeHtml(kind)}</strong>
      <span>${escapeHtml(item.message || item.code || String(item))}</span>
    </div>
  `;
}

function renderRunHistory(runs = []) {
  const panel = qs('#runHistory');
  if (!runs.length) {
    panel.className = 'workflow-panel muted';
    panel.textContent = 'No runs yet.';
    return;
  }
  panel.className = 'workflow-panel';
  panel.innerHTML = runs.slice(0, 8).map((run) => `
    <div class="run-history-item ${escapeHtml(run.status || 'idle')}">
      <strong>${escapeHtml(run.type || 'workflow')} - ${escapeHtml(run.status || 'unknown')}</strong>
      <span>${escapeHtml((run.node_ids || []).join(' -> ') || 'no nodes')}</span>
      <small>${escapeHtml(run.finished_at || run.started_at || '')}</small>
    </div>
  `).join('');
}

function setWorkflowRunning(isRunning) {
  state.workflowRunning = isRunning;
  updateWorkflowButtons();
}

function updateWorkflowButtons() {
  const hasProject = !!state.project;
  ['#previewPlanBtn', '#runWholeGraphBtn', '#refreshRunsBtn'].forEach((selector) => {
    qs(selector).disabled = !hasProject || state.workflowRunning;
  });
  ['#runSelectedBtn', '#runFromSelectedBtn'].forEach((selector) => {
    qs(selector).disabled = !hasProject || state.workflowRunning;
  });
  ['#saveProjectBtn', '#exportProjectBtn', '#duplicateProjectBtn', '#saveTemplateBtn', '#projectSettingsBtn'].forEach((selector) => {
    const element = qs(selector);
    if (element) element.disabled = !hasProject;
  });
}

function renderAssets() {
  const list = qs('#assetList');
  list.innerHTML = '';
  const assets = state.project?.assets || [];
  if (!assets.length) {
    list.innerHTML = '<div class="muted">No assets yet.</div>';
    return;
  }
  assets.forEach((asset) => {
    const url = assetUrl(asset);
    const card = document.createElement('div');
    card.className = 'asset-card';
    card.innerHTML = assetCardHtml(asset, url);
    list.appendChild(card);
  });

  list.querySelectorAll('[data-action="copy-url"]').forEach((button) => {
    button.addEventListener('click', () => copyText(button.dataset.url || ''));
  });
}

function assetCardHtml(asset, url) {
  const kind = asset.kind || outputKindFromUrl(url) || 'other';
  const sourceNodeId = asset.metadata?.source_node_id || '';
  return `
    ${assetMediaHtml(url, kind, asset.filename)}
    <div class="asset-card-body">
      <strong>${escapeHtml(asset.filename || asset.id)}</strong>
      <div class="badge-row">
        <span class="badge">${escapeHtml(kind)}</span>
        ${sourceNodeId ? `<span class="badge">source ${escapeHtml(sourceNodeId)}</span>` : ''}
      </div>
      <span class="asset-meta">${escapeHtml(asset.created_at ? formatDate(asset.created_at) : '')}</span>
      ${url ? `
        <div class="asset-actions">
          <button type="button" data-action="copy-url" data-url="${attr(url)}">Copy URL</button>
          <a href="${attr(url)}" target="_blank">Open</a>
          <a href="${attr(url)}" download>Download</a>
        </div>
      ` : '<span class="asset-meta">No public URL available.</span>'}
    </div>
  `;
}

function assetMediaHtml(url, kind, label) {
  if (!url) return '<div class="asset-empty-preview">No preview</div>';
  const safeUrl = attr(url);
  if (kind === 'video') {
    return `<video class="asset-media" src="${safeUrl}" controls></video>`;
  }
  if (kind === 'audio') {
    return `<div class="asset-audio-wrap"><audio class="audio-preview" src="${safeUrl}" controls></audio></div>`;
  }
  if (kind === 'image') {
    return `<a href="${safeUrl}" target="_blank"><img class="asset-media" src="${safeUrl}" alt="${attr(label || 'Asset preview')}" /></a>`;
  }
  return `<a class="asset-empty-preview" href="${safeUrl}" target="_blank">${escapeHtml(label || url)}</a>`;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value || '');
  return date.toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function attr(value) {
  return escapeHtml(value);
}

async function boot() {
  loadLayoutPreference();
  renderLayoutState();
  await loadModels();
  renderNodeLibrary();
  await refreshProjectList();

  const lastProjectId = localStorage.getItem('wavespeed_canvas_project_id');
  const fallbackProjectId = state.projects[0]?.id;
  const projectId = state.projects.some((project) => project.id === lastProjectId) ? lastProjectId : fallbackProjectId;
  if (projectId) {
    await loadProject(projectId);
  } else {
    await createProject();
  }
}

qs('#newProjectBtn').addEventListener('click', createProject);
qs('#toggleNodesBtn').addEventListener('click', toggleLeftPanel);
qs('#toggleInspectorBtn').addEventListener('click', toggleRightPanel);
qs('#saveProjectBtn').addEventListener('click', saveProject);
qs('#exportProjectBtn').addEventListener('click', exportProject);
qs('#importProjectBtn').addEventListener('click', openImportPicker);
qs('#importProjectFile').addEventListener('change', importProjectFile);
qs('#duplicateProjectBtn').addEventListener('click', duplicateProject);
qs('#templatesBtn').addEventListener('click', openTemplatesPanel);
qs('#saveTemplateBtn').addEventListener('click', saveCurrentProjectAsTemplate);
qs('#loadProjectBtn').addEventListener('click', loadSelectedProject);
qs('#projectSettingsBtn').addEventListener('click', openProjectSettings);
qs('#closeSettingsBtn').addEventListener('click', closeProjectSettings);
qs('#cancelSettingsBtn').addEventListener('click', closeProjectSettings);
qs('#settingsPanelBackdrop').addEventListener('click', closeProjectSettings);
qs('#closeTemplatesBtn').addEventListener('click', closeTemplatesPanel);
qs('#templatesPanelBackdrop').addEventListener('click', closeTemplatesPanel);
qs('#saveSettingsBtn').addEventListener('click', saveProjectSettings);
qs('#projectName').addEventListener('input', updateProjectFieldsFromForm);
qs('#projectDescription').addEventListener('input', updateProjectFieldsFromForm);
qs('#previewPlanBtn').addEventListener('click', previewWorkflowPlan);
qs('#runSelectedBtn').addEventListener('click', runSelectedWorkflowNode);
qs('#runFromSelectedBtn').addEventListener('click', runFromSelectedNode);
qs('#runWholeGraphBtn').addEventListener('click', runWholeGraph);
qs('#refreshRunsBtn').addEventListener('click', refreshRunHistory);

boot().catch((error) => log(error.message));
