import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow
} from "@xyflow/react";
import {
  ArrowDown,
  ArrowUp,
  Boxes,
  BriefcaseBusiness,
  ChevronRight,
  Clock3,
  FolderKanban,
  Image,
  Info,
  Loader2,
  PackageOpen,
  Play,
  Plus,
  RefreshCw,
  Save,
  Search,
  Upload,
  WandSparkles,
  Waves,
  X
} from "lucide-react";
import "@xyflow/react/dist/style.css";
import "./styles.css";

const NODE_WIDTH = 360;
const CANVAS_CONTEXT_MENU_WIDTH = 850;
const CANVAS_CONTEXT_MENU_HEIGHT = 560;
const DISPLAY_USD_TO_MYR_RATE = 4.06;
const FIELD_LINK_INPUTS = new Set([
  "prompt",
  "negative_prompt",
  "text",
  "image",
  "images",
  "image_url",
  "image_urls",
  "reference_image",
  "reference_images",
  "reference_url",
  "reference_urls",
  "source_image",
  "source_images",
  "target_image",
  "target_images",
  "video",
  "videos",
  "video_url",
  "video_urls",
  "audio",
  "audios",
  "audio_url",
  "audio_urls",
  "last_image",
  "mask_image",
  "body_image",
  "front_image_url",
  "back_image_url",
  "left_image_url",
  "asset_id",
  "selected_asset_id"
]);
const PROMPT_INPUTS = new Set(["prompt", "negative_prompt", "text"]);
const ASSET_INPUT_TYPES = new Set(["asset_url", "asset_id"]);
const UTILITY_NODE_TYPES = new Set([
  "prompt_card",
  "style_card",
  "character_card",
  "asset_input",
  "asset_selector",
  "compare_board",
  "variant_batch",
  "reroute",
  "note",
  "group_frame",
  "export_package",
  "video_last_frame",
  "stitch_video"
]);
const RUNNABLE_UTILITY_NODE_TYPES = new Set(["video_last_frame", "stitch_video"]);

function displayUiText(value) {
  return String(value ?? "")
    .replace(/generic_wavespeed/gi, "generic_default_model")
    .replace(/wavespeed-ai/gi, "default-model")
    .replace(/wavespeed\s+ai/gi, "Default Model")
    .replace(/wavespeed/gi, "Default Model");
}

function compactSlashPath(value) {
  const text = displayUiText(value);
  const parts = text.split("/");
  return parts.length > 2 ? parts.slice(1).join("/") : text;
}

function estimatedCostLabel(model) {
  const cost = modelEstimatedCost(model);
  return cost == null ? "cost unknown" : `from ${formatMyrFromUsd(cost)}/run`;
}

function modelEstimatedCost(model) {
  const cost = model?.estimated_base_cost_usd ?? model?.cost?.estimated_base_cost_usd;
  return cost == null || Number.isNaN(Number(cost)) ? null : Number(cost);
}

function formatMyrFromUsd(usdCost) {
  return `RM${(Number(usdCost) * DISPLAY_USD_TO_MYR_RATE).toFixed(4)}`;
}

function App() {
  const { screenToFlowPosition } = useReactFlow();
  const [projects, setProjects] = useState([]);
  const [project, setProject] = useState(null);
  const [models, setModels] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [activeRailMenu, setActiveRailMenu] = useState("");
  const [libraryQuery, setLibraryQuery] = useState("");
  const [libraryCategory, setLibraryCategory] = useState("all");
  const [libraryCollapseTick, setLibraryCollapseTick] = useState(0);
  const [librarySearchAutoOpen, setLibrarySearchAutoOpen] = useState(true);
  const [uploadToWaveSpeed, setUploadToWaveSpeed] = useState(false);
  const [status, setStatus] = useState("Loading workspace...");
  const [busyNodeId, setBusyNodeId] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [modal, setModal] = useState("");
  const [templates, setTemplates] = useState([]);
  const [recipes, setRecipes] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [workflowPlan, setWorkflowPlan] = useState(null);
  const [settingsDraft, setSettingsDraft] = useState(null);
  const [canvasContextMenu, setCanvasContextMenu] = useState(null);
  const fileInputRef = useRef(null);
  const importProjectRef = useRef(null);

  useEffect(() => {
    refreshWorkspace();
  }, []);

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setActiveRailMenu("");
        setCanvasContextMenu(null);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    const hasActiveJobs = jobs.some((job) => ["queued", "running", "cancel_requested"].includes(job.status));
    if (!hasActiveJobs) return undefined;
    const timer = window.setInterval(() => refreshJobs(false), 1500);
    return () => window.clearInterval(timer);
  }, [jobs]);

  async function api(path, options = {}) {
    const response = await fetch(path, options);
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      throw new Error(detailMessage(body) || response.statusText);
    }
    return body;
  }

  async function refreshWorkspace() {
    try {
      const [loadedProjects, loadedModels, loadedCategories] = await Promise.all([
        api("/api/projects"),
        api("/api/models?enabled_only=true"),
        api("/api/categories")
      ]);
      setProjects(loadedProjects);
      setModels(loadedModels);
      setCategories(loadedCategories);
      if (loadedProjects.length) {
        await loadProject(loadedProjects[0].id, false);
      } else {
        await createProject();
      }
      setStatus("Workspace ready.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function loadProject(projectId, announce = true) {
    const loaded = await api(`/api/projects/${projectId}`);
    setProject(loaded);
    setSelectedNodeId(loaded.nodes?.[0]?.id || "");
    if (announce) setStatus(`Loaded ${loaded.name}.`);
    return loaded;
  }

  async function createProject() {
    const created = await api("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Default Model Canvas Workflow", description: "" })
    });
    setProject(created);
    setProjects((items) => [created, ...items.filter((item) => item.id !== created.id)]);
    setSelectedNodeId("");
    setStatus("Created project.");
    return created;
  }

  async function saveProject(nextProject = project) {
    if (!nextProject) return null;
    setIsSaving(true);
    try {
      const saved = await api(`/api/projects/${nextProject.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(projectPayload(nextProject))
      });
      setProject(saved);
      setProjects((items) => [saved, ...items.filter((item) => item.id !== saved.id)]);
      setStatus("Project saved.");
      return saved;
    } finally {
      setIsSaving(false);
    }
  }

  async function exportProject() {
    if (!project) return;
    try {
      const saved = await saveProject(project);
      const response = await fetch(`/api/projects/${saved.id}/export`);
      if (!response.ok) throw new Error(await response.text());
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") || "";
      const filename = disposition.match(/filename="?([^"]+)"?/i)?.[1] || `default-model-workflow-${saved.id}.json`;
      downloadBlob(blob, filename);
      setStatus(`Exported ${saved.name}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function importProject(file) {
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const result = await api("/api/projects/import", { method: "POST", body });
      setProject(result.project);
      setSelectedNodeId("");
      await refreshProjectList(result.project);
      setStatus(`Imported ${result.project.name}.`);
    } catch (error) {
      setStatus(error.message);
    } finally {
      if (importProjectRef.current) importProjectRef.current.value = "";
    }
  }

  async function duplicateProject() {
    if (!project) return;
    const name = window.prompt("Duplicate project name", `Copy of ${displayUiText(project.name || "Workflow")}`);
    if (name === null) return;
    try {
      const saved = await saveProject(project);
      const result = await api(`/api/projects/${saved.id}/duplicate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || undefined, include_outputs: true, include_run_history: false })
      });
      setProject(result.project);
      setSelectedNodeId("");
      await refreshProjectList(result.project);
      setStatus(`Duplicated ${result.project.name}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function refreshProjectList(preferredProject = project) {
    const loadedProjects = await api("/api/projects");
    setProjects(loadedProjects);
    if (preferredProject) {
      setProjects((items) => [preferredProject, ...items.filter((item) => item.id !== preferredProject.id)]);
    }
  }

  async function openTemplates() {
    try {
      const loaded = await api("/api/templates");
      setTemplates(loaded);
      setModal("templates");
      setStatus(`Loaded ${loaded.length} templates.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function createProjectFromTemplate(template) {
    const name = window.prompt("New project name", `${template.name || "Template"} Project`);
    if (name === null) return;
    try {
      const created = await api(`/api/templates/${template.id}/create-project`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || undefined })
      });
      setProject(created);
      setSelectedNodeId("");
      await refreshProjectList(created);
      setModal("");
      setStatus(`Created project from ${template.name}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function deleteTemplate(template) {
    if (template.builtin || !window.confirm("Delete this local template?")) return;
    try {
      await api(`/api/templates/${template.id}`, { method: "DELETE" });
      setTemplates(await api("/api/templates"));
      setStatus("Template deleted.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function saveCurrentProjectAsTemplate() {
    if (!project) return;
    const name = window.prompt("Template name", `${displayUiText(project.name || "Workflow")} Template`);
    if (name === null || !name.trim()) return;
    const description = window.prompt("Template description", project.description || "") || "";
    const category = window.prompt("Template category", "image") || "image";
    const tagText = window.prompt("Tags, comma separated", "starter") || "";
    try {
      const saved = await saveProject(project);
      await api(`/api/templates/from-project/${saved.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          description,
          category,
          tags: tagText.split(",").map((tag) => tag.trim()).filter(Boolean),
          include_outputs: false,
          include_settings: true
        })
      });
      setTemplates(await api("/api/templates"));
      setModal("templates");
      setStatus("Template saved.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function openRecipes() {
    try {
      const loaded = await api("/api/recipes");
      setRecipes(loaded);
      setModal("recipes");
      setStatus(`Loaded ${loaded.length} recipes.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function applyRecipe(recipe) {
    if (!project) return;
    try {
      const saved = await saveProject(project);
      const updated = await api(`/api/projects/${saved.id}/apply-recipe/${recipe.id}`, { method: "POST" });
      setProject(updated);
      setSelectedNodeId(updated.nodes?.[0]?.id || "");
      setModal("");
      setStatus(`Applied recipe: ${recipe.name}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function createProjectFromRecipe(recipe) {
    const name = window.prompt("New project name", `${recipe.name || "Recipe"} Project`);
    if (name === null) return;
    try {
      const created = await api(`/api/recipes/${recipe.id}/create-project`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || undefined })
      });
      setProject(created);
      setSelectedNodeId(created.nodes?.[0]?.id || "");
      await refreshProjectList(created);
      setModal("");
      setStatus(`Created project from ${recipe.name}.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function openSettings() {
    if (!project) return;
    try {
      const settings = await api(`/api/projects/${project.id}/settings`);
      setSettingsDraft(settings);
      setModal("settings");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function saveSettings() {
    if (!project || !settingsDraft) return;
    try {
      const settings = await api(`/api/projects/${project.id}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settingsDraft)
      });
      setProject((current) => current ? { ...current, settings } : current);
      setModal("");
      setStatus("Project settings saved.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  function updateProject(mutator) {
    setProject((current) => {
      if (!current) return current;
      const draft = structuredClone(current);
      mutator(draft);
      return draft;
    });
  }

  const modelById = useMemo(() => {
    const map = new Map();
    for (const model of models) {
      map.set(model.id, model);
      if (model.model_id) map.set(model.model_id, model);
      if (model.default_model_id) map.set(model.default_model_id, model);
    }
    return map;
  }, [models]);

  const modelsByNodeType = useMemo(() => {
    const map = new Map();
    for (const model of models) {
      if (!map.has(model.node_type)) map.set(model.node_type, []);
      map.get(model.node_type).push(model);
    }
    return map;
  }, [models]);

  const catalogLibraryModels = useMemo(
    () => models.filter((model) => !isUtilityLibraryModel(model)),
    [models]
  );

  const utilityLibraryModels = useMemo(
    () => models.filter(isUtilityLibraryModel).sort((a, b) => String(a.label || a.id).localeCompare(String(b.label || b.id))),
    [models]
  );

  const libraryModels = useMemo(() => {
    const query = libraryQuery.trim().toLowerCase();
    return catalogLibraryModels
      .filter((model) => model.enabled)
      .filter((model) => libraryCategory === "all" || model.category === libraryCategory)
      .filter((model) => {
        if (!query) return true;
        return [
          model.label,
          model.display_name,
          model.id,
          model.default_model_id,
          model.node_type,
          model.category,
          model.description,
          ...(model.capability_tags || [])
        ]
          .join(" ")
          .toLowerCase()
          .includes(query);
      })
      .sort((a, b) => librarySortScore(a) - librarySortScore(b) || providerForModel(a).localeCompare(providerForModel(b)) || a.label.localeCompare(b.label));
  }, [catalogLibraryModels, libraryCategory, libraryQuery]);

  const libraryGroups = useMemo(() => {
    const groups = new Map();
    for (const model of libraryModels) {
      const provider = providerForModel(model);
      if (!groups.has(provider)) groups.set(provider, []);
      groups.get(provider).push(model);
    }
    return [...groups.entries()]
      .map(([provider, items]) => ({ provider, items }))
      .sort((a, b) => providerSortScore(a.provider) - providerSortScore(b.provider) || a.provider.localeCompare(b.provider));
  }, [libraryModels]);

  const canvasContextModels = useMemo(
    () => catalogLibraryModels
      .filter((model) => model.enabled)
      .sort((a, b) => librarySortScore(a) - librarySortScore(b) || providerForModel(a).localeCompare(providerForModel(b)) || a.label.localeCompare(b.label)),
    [catalogLibraryModels]
  );

  const canvasContextUtilities = useMemo(
    () => utilityLibraryModels,
    [utilityLibraryModels]
  );

  const selectedNode = useMemo(
    () => project?.nodes?.find((node) => node.id === selectedNodeId) || null,
    [project, selectedNodeId]
  );

  const selectedNodeModel = useMemo(
    () => resolveNodeModel(selectedNode, modelById, modelsByNodeType),
    [selectedNode, modelById, modelsByNodeType]
  );

  const flowNodes = useMemo(() => {
    if (!project) return [];
    return (project.nodes || []).map((node) => ({
      id: node.id,
      type: "workflowCard",
      position: { x: Number(node.x || 0), y: Number(node.y || 0) },
      data: {
        node,
        model: resolveNodeModel(node, modelById, modelsByNodeType),
        assets: project.assets || [],
        nodes: project.nodes || [],
        edges: project.edges || [],
        selected: selectedNodeId === node.id,
        busy: busyNodeId === node.id,
        onChange: updateNodeInput,
        onMoveStitchVideo: moveStitchVideoItem,
        onRun: runNode,
        onSelect: setSelectedNodeId,
        onRemove: removeNode,
        onBranch: branchFromNode
      },
      style: { width: NODE_WIDTH }
    }));
  }, [project, modelById, modelsByNodeType, selectedNodeId, busyNodeId]);

  const flowEdges = useMemo(() => {
    if (!project) return [];
    const nodeById = new Map((project.nodes || []).map((node) => [node.id, node]));
    const seen = new Set();
    return toFlowEdges(project.edges || [])
      .map((edge) => {
        const targetNode = nodeById.get(edge.target);
        const targetModel = resolveNodeModel(targetNode, modelById, modelsByNodeType);
        return {
          ...edge,
          targetHandle: normalizeTargetHandle(edge.targetHandle, targetNode, targetModel)
        };
      })
      .filter((edge) => {
        if (!edge.source || !edge.target) return false;
        const key = `${edge.source}:${edge.target}:${edge.targetHandle}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((edge) => ({
        ...edge,
        type: "smoothstep",
        animated: false
      }));
  }, [project, modelById, modelsByNodeType]);

  const onNodesChange = useCallback((changes) => {
    const changed = new Map();
    for (const change of changes) {
      if (change.type === "position" && change.position) {
        changed.set(change.id, change.position);
      }
      if (change.type === "select" && change.selected) {
        setSelectedNodeId(change.id);
      }
    }
    if (!changed.size) return;
    updateProject((draft) => {
      for (const node of draft.nodes || []) {
        const position = changed.get(node.id);
        if (position) {
          node.x = Math.round(position.x);
          node.y = Math.round(position.y);
        }
      }
    });
  }, []);

  const onEdgesChange = useCallback((changes) => {
    updateProject((draft) => {
      const current = toFlowEdges(draft.edges || []);
      const next = applyEdgeChanges(changes, current);
      draft.edges = next.map(flowEdgeToProjectEdge);
    });
  }, []);

  const onConnect = useCallback((connection) => {
    updateProject((draft) => {
      if (!connection.source || !connection.target || connection.source === connection.target) return;
      const targetNode = draft.nodes.find((node) => node.id === connection.target);
      const targetModel = resolveNodeModel(targetNode, modelById, modelsByNodeType);
      const targetInput = normalizeTargetHandle(connection.targetHandle, targetNode, targetModel);
      const newEdge = {
        ...connection,
        targetHandle: targetInput,
        id: `edge_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`
      };
      const targetIsList = isListInputField(targetModel?.fields?.find((field) => field.name === targetInput));
      const current = toFlowEdges(draft.edges || []).filter((edge) => {
        if (edge.source === connection.source && edge.target === connection.target && (edge.targetHandle || "input") === targetInput) {
          return false;
        }
        if (!targetIsList && edge.target === connection.target && (edge.targetHandle || "input") === targetInput) {
          return false;
        }
        return true;
      });
      const next = addEdge(newEdge, current);
      draft.edges = next.map(flowEdgeToProjectEdge);
    });
  }, [modelById, modelsByNodeType]);

  function updateNodeInput(nodeId, fieldName, value) {
    updateProject((draft) => {
      const node = draft.nodes.find((item) => item.id === nodeId);
      if (!node) return;
      node.inputs = { ...(node.inputs || {}), [fieldName]: value };
      node.updated_at = new Date().toISOString();
    });
  }

  function moveStitchVideoItem(nodeId, fromIndex, direction) {
    updateProject((draft) => {
      const node = draft.nodes.find((item) => item.id === nodeId);
      if (!node) return;
      const entries = stitchVideoOrderEntries(node, draft.nodes || [], draft.edges || [], draft.assets || []);
      const toIndex = fromIndex + direction;
      if (toIndex < 0 || toIndex >= entries.length) return;
      const nextEntries = [...entries];
      [nextEntries[fromIndex], nextEntries[toIndex]] = [nextEntries[toIndex], nextEntries[fromIndex]];
      node.inputs = {
        ...(node.inputs || {}),
        videos: nextEntries.filter((entry) => entry.kind === "asset").map((entry) => entry.value),
        videos_order: nextEntries.map((entry) => entry.orderKey)
      };

      const edgeEntries = nextEntries.filter((entry) => entry.kind === "edge");
      if (!edgeEntries.length) return;
      const orderedEdgeIds = new Set(edgeEntries.map((entry) => entry.edge.id));
      const orderedEdges = edgeEntries.map((entry) => entry.edge);
      const reorderedEdges = [];
      let inserted = false;
      for (const edge of draft.edges || []) {
        if (orderedEdgeIds.has(edge.id)) {
          if (!inserted) {
            reorderedEdges.push(...orderedEdges);
            inserted = true;
          }
          continue;
        }
        reorderedEdges.push(edge);
      }
      if (!inserted) reorderedEdges.push(...orderedEdges);
      draft.edges = reorderedEdges;
    });
  }

  function addModelNode(model, position = null) {
    if (!project) return;
    const nodeType = model.node_type || "generic_wavespeed";
    const id = `node_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`;
    const existingCount = project.nodes?.length || 0;
    const nextPosition = position || {
      x: 140 + (existingCount % 5) * 40,
      y: 100 + existingCount * 36
    };
    const node = {
      id,
      type: nodeType,
      title: displayUiText(model.label || model.display_name || nodeType),
      model_id: model.default_model_id || model.model_id || (model.source === "catalog" ? model.id : null),
      estimated_base_cost_usd: model.estimated_base_cost_usd ?? model.cost?.estimated_base_cost_usd ?? null,
      x: Math.round(nextPosition.x),
      y: Math.round(nextPosition.y),
      inputs: defaultInputsForModel(model),
      output_asset_ids: [],
      output_urls: [],
      last_run: {},
      status: "idle",
      error_message: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    updateProject((draft) => {
      draft.nodes = [...(draft.nodes || []), node];
    });
    setSelectedNodeId(id);
    setCanvasContextMenu(null);
    setStatus(`Added ${node.title}.`);
  }

  function openCanvasContextMenu(event) {
    event.preventDefault();
    const flowPosition = screenToFlowPosition({ x: event.clientX, y: event.clientY });
    setActiveRailMenu("");
    setCanvasContextMenu({
      screenX: Math.max(12, Math.min(event.clientX, window.innerWidth - CANVAS_CONTEXT_MENU_WIDTH - 12)),
      screenY: Math.max(12, Math.min(event.clientY, window.innerHeight - CANVAS_CONTEXT_MENU_HEIGHT - 12)),
      flowX: flowPosition.x,
      flowY: flowPosition.y
    });
  }

  function removeNode(nodeId) {
    updateProject((draft) => {
      draft.nodes = (draft.nodes || []).filter((node) => node.id !== nodeId);
      draft.edges = (draft.edges || []).filter((edge) => edge.source_node_id !== nodeId && edge.target_node_id !== nodeId);
    });
    if (selectedNodeId === nodeId) setSelectedNodeId("");
  }

  function autoTidyCanvas() {
    if (!project?.nodes?.length) {
      setStatus("No nodes to tidy.");
      return;
    }
    updateProject((draft) => {
      const positions = tidyNodePositions(draft.nodes || [], draft.edges || []);
      for (const node of draft.nodes || []) {
        const position = positions.get(node.id);
        if (!position) continue;
        node.x = position.x;
        node.y = position.y;
      }
    });
    setStatus(`Auto tidied ${project.nodes.length} nodes.`);
  }

  function branchFromNode(nodeId) {
    if (!project) return;
    const sourceNode = project.nodes.find((node) => node.id === nodeId);
    if (!sourceNode) return;
    const remixModel =
      models.find((model) => model.node_type === "image_to_image" && model.enabled) ||
      models.find((model) => model.node_type === "generic_wavespeed" && model.output_kind === "image" && model.enabled);
    if (!remixModel) {
      setStatus("No enabled remix/image-to-image model is available.");
      return;
    }
    const childId = `node_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`;
    const child = {
      id: childId,
      type: remixModel.node_type,
      title: "Remix Image",
      model_id: remixModel.default_model_id || remixModel.model_id || remixModel.id,
      estimated_base_cost_usd: remixModel.estimated_base_cost_usd ?? null,
      x: Number(sourceNode.x || 0) + 460,
      y: Number(sourceNode.y || 0),
      inputs: defaultInputsForModel(remixModel),
      output_asset_ids: [],
      output_urls: [],
      last_run: {},
      status: "idle",
      error_message: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    updateProject((draft) => {
      draft.nodes.push(child);
      draft.edges.push({
        id: `edge_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`,
        source_node_id: nodeId,
        target_node_id: childId,
        source_output: "output",
        target_input: "image"
      });
    });
    setSelectedNodeId(childId);
    setStatus("Created remix branch.");
  }

  async function runNode(nodeId) {
    if (!project) return;
    setBusyNodeId(nodeId);
    setStatus("Saving project before run...");
    try {
      const saved = await saveProject(project);
      const result = await api("/api/runs/node", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: saved.id, node_id: nodeId, save_to_project: true })
      });
      await loadProject(saved.id, false);
      setStatus(result.output_urls?.length ? "Run complete." : "Run complete. Check node output.");
    } catch (error) {
      setStatus(error.message);
      await loadProject(project.id, false).catch(() => {});
    } finally {
      setBusyNodeId("");
    }
  }

  async function uploadAsset(file) {
    if (!file || !project) return;
    setStatus("Uploading asset...");
    const form = new FormData();
    form.append("file", file);
    try {
      const asset = await api(`/api/assets/upload?upload_to_wavespeed=${uploadToWaveSpeed ? "true" : "false"}`, {
        method: "POST",
        body: form
      });
      const nextProject = structuredClone(project);
      nextProject.assets = [asset, ...(nextProject.assets || [])];
      const saved = await saveProject(nextProject);
      setProject(saved);
      setStatus(`Uploaded ${asset.filename}.`);
    } catch (error) {
      setStatus(error.message);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function runWorkflow(mode) {
    if (!project) return;
    try {
      const saved = await saveProject(project);
      const endpoint =
        mode === "all"
          ? `/api/workflows/${saved.id}/run-all`
          : mode === "from"
            ? `/api/workflows/${saved.id}/run-from-node/${selectedNodeId}`
            : `/api/workflows/${saved.id}/run-selected`;
      const options =
        mode === "selected"
          ? {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ node_id: selectedNodeId })
            }
          : { method: "POST" };
      const result = await api(endpoint, options);
      setProject(result.project || (await loadProject(saved.id, false)));
      setStatus(result.ok ? "Workflow run complete." : "Workflow run failed.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function previewWorkflowPlan(mode = "whole_graph") {
    if (!project) return;
    try {
      const saved = await saveProject(project);
      const params = new URLSearchParams({ mode });
      if (mode !== "whole_graph" && selectedNodeId) params.set("node_id", selectedNodeId);
      const plan = await api(`/api/workflows/${saved.id}/plan?${params}`);
      setWorkflowPlan(plan);
      setModal("plan");
      setStatus(plan.errors?.length ? "Workflow plan has errors." : "Workflow plan ready.");
    } catch (error) {
      setWorkflowPlan({ ok: false, errors: [{ message: error.message }], warnings: [], steps: [] });
      setModal("plan");
      setStatus(error.message);
    }
  }

  async function queueWorkflow(mode) {
    if (!project) return;
    if (mode !== "whole_graph" && !selectedNodeId) {
      setStatus("Select a node first.");
      return;
    }
    try {
      const saved = await saveProject(project);
      const endpoint =
        mode === "whole_graph"
          ? "/api/jobs/workflow/all"
          : mode === "from_node"
            ? `/api/jobs/workflow/from-node/${selectedNodeId}`
            : "/api/jobs/workflow/selected";
      await api(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: saved.id, mode, node_id: selectedNodeId || null })
      });
      await refreshJobs(true);
      await loadProject(saved.id, false);
      setStatus("Workflow job queued.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function refreshJobs(openPanel = true) {
    try {
      const loaded = await api("/api/jobs?limit=50");
      setJobs(loaded);
      if (openPanel) setModal("jobs");
      const terminalForProject = loaded.some((job) =>
        job.project_id === project?.id && ["success", "error", "cancelled"].includes(job.status)
      );
      if (terminalForProject && project?.id) {
        await loadProject(project.id, false);
      }
      return loaded;
    } catch (error) {
      setStatus(error.message);
      return [];
    }
  }

  async function cancelJob(jobId) {
    try {
      await api(`/api/jobs/${jobId}/cancel`, { method: "POST" });
      await refreshJobs(true);
      setStatus("Job cancel requested.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function retryJob(jobId) {
    try {
      await api(`/api/jobs/${jobId}/retry`, { method: "POST" });
      await refreshJobs(true);
      setStatus("Retry queued.");
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function clearCompletedJobs() {
    try {
      const result = await api("/api/jobs/completed", { method: "DELETE" });
      await refreshJobs(true);
      setStatus(`Cleared ${result.cleared || 0} completed jobs.`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  if (!project) {
    return (
      <main className="boot">
        <Loader2 className="spin" size={28} />
        <p>{status}</p>
      </main>
    );
  }

  return (
    <>
    <main className="studio left-collapsed">
      <aside className="sidebar left-panel">
        <div className="rail-brand" title="Default Model Canvas">
          <Waves size={24} />
        </div>
        <div className="menu-scroll">
          <CompactPanelSection title="Project" shortTitle="Project" icon={<FolderKanban size={15} />} popoverClassName="project-popover" popoverOpen={activeRailMenu === "Project"} onCollapsedActivate={() => setActiveRailMenu((value) => value === "Project" ? "" : "Project")} defaultOpen>
            <div className="compact-stack">
              <select value={project.id} onChange={(event) => loadProject(event.target.value)} aria-label="Current project">
                {projects.map((item) => (
                  <option key={item.id} value={item.id}>
                    {displayUiText(item.name)}
                  </option>
                ))}
              </select>
              <div className="compact-grid">
                <button type="button" onClick={createProject}>
                  <Plus size={16} /> New
                </button>
                <button type="button" onClick={() => saveProject()} disabled={isSaving}>
                  {isSaving ? <Loader2 className="spin" size={16} /> : <Save size={16} />} Save
                </button>
                <button type="button" onClick={refreshWorkspace}>
                  <RefreshCw size={16} /> Refresh
                </button>
                <a href="/docs" target="_blank" rel="noreferrer">
                  API Docs
                </a>
              </div>
              <label>
                Name
                <input value={displayUiText(project.name)} onChange={(event) => updateProject((draft) => (draft.name = event.target.value))} />
              </label>
              <label>
                Description
                <textarea value={project.description || ""} onChange={(event) => updateProject((draft) => (draft.description = event.target.value))} />
              </label>
            </div>
          </CompactPanelSection>

          <CompactPanelSection title="Models" shortTitle="Models" icon={<Boxes size={15} />} popoverOpen={activeRailMenu === "Models"} onCollapsedActivate={() => setActiveRailMenu((value) => value === "Models" ? "" : "Models")} defaultOpen>
            <div className="panel-tools compact-tools">
              <input
                type="search"
                value={libraryQuery}
                onChange={(event) => {
                  setLibraryQuery(event.target.value);
                  setLibrarySearchAutoOpen(true);
                }}
                placeholder="Search models or nodes"
              />
              <select value={libraryCategory} onChange={(event) => setLibraryCategory(event.target.value)}>
                <option value="all">All categories</option>
                {categories.filter((category) => category.id !== "utility").map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.label || category.id}
                  </option>
                ))}
              </select>
              <button
                className="panel-tool-button"
                type="button"
                onClick={() => {
                  setLibrarySearchAutoOpen(false);
                  setLibraryCollapseTick((value) => value + 1);
                }}
              >
                Collapse All
              </button>
            </div>
            <div className="library-summary" aria-live="polite">
              <strong>{libraryModels.length.toLocaleString()} models</strong>
              <span>{libraryGroups.length.toLocaleString()} providers</span>
              {libraryModels.length !== catalogLibraryModels.length && <span>{catalogLibraryModels.length.toLocaleString()} total loaded</span>}
            </div>
            <div className="node-library">
              {libraryGroups.length ? (
                libraryGroups.map((group) => (
                  <LibraryGroup
                    key={group.provider}
                    group={group}
                    collapseTick={libraryCollapseTick}
                    forceOpen={librarySearchAutoOpen && Boolean(libraryQuery.trim())}
                    onAdd={addModelNode}
                  />
                ))
              ) : (
                <p className="empty">No nodes match this search.</p>
              )}
            </div>
          </CompactPanelSection>

          <CompactPanelSection title="Utility" shortTitle="Utility" icon={<BriefcaseBusiness size={15} />} popoverOpen={activeRailMenu === "Utility"} onCollapsedActivate={() => setActiveRailMenu((value) => value === "Utility" ? "" : "Utility")}>
            <div className="library-summary" aria-live="polite">
              <strong>{utilityLibraryModels.length.toLocaleString()} utilities</strong>
              <span>local workflow tools</span>
            </div>
            <div className="node-library">
              {utilityLibraryModels.length ? (
                utilityLibraryModels.map((model) => (
                  <LibraryCard key={`${model.id}-${model.node_type}`} model={model} onAdd={addModelNode} />
                ))
              ) : (
                <p className="empty">No utility nodes loaded.</p>
              )}
            </div>
          </CompactPanelSection>

          <CompactPanelSection title="Run" shortTitle="Run" icon={<Play size={15} />} popoverOpen={activeRailMenu === "Run"} onCollapsedActivate={() => setActiveRailMenu((value) => value === "Run" ? "" : "Run")}>
            <div className="compact-stack">
              <button type="button" onClick={() => previewWorkflowPlan("whole_graph")}>
                Preview Plan
              </button>
              <button type="button" onClick={() => selectedNodeId && runNode(selectedNodeId)} disabled={!selectedNodeId || busyNodeId}>
                <Play size={16} /> Run Selected
              </button>
              <div className="compact-grid">
                <button type="button" onClick={() => runWorkflow("from")} disabled={!selectedNodeId}>
                  Run From
                </button>
                <button type="button" onClick={() => runWorkflow("all")}>Run Graph</button>
                <button type="button" onClick={() => queueWorkflow("selected")} disabled={!selectedNodeId}>
                  Queue One
                </button>
                <button type="button" onClick={() => queueWorkflow("from_node")} disabled={!selectedNodeId}>
                  Queue From
                </button>
              </div>
              <button type="button" onClick={() => queueWorkflow("whole_graph")}>
                Queue Whole Graph
              </button>
              <p className="muted">{selectedNode ? selectedNode.title : "No node selected."}</p>
            </div>
          </CompactPanelSection>

          <CompactPanelSection title="Files & Templates" shortTitle="Files" icon={<PackageOpen size={15} />} popoverOpen={activeRailMenu === "Files & Templates"} onCollapsedActivate={() => setActiveRailMenu((value) => value === "Files & Templates" ? "" : "Files & Templates")}>
            <div className="compact-grid">
              <button type="button" onClick={exportProject}>Export</button>
              <button type="button" onClick={() => importProjectRef.current?.click()}>Import</button>
              <button type="button" onClick={duplicateProject}>Duplicate</button>
              <button type="button" onClick={openTemplates}>Templates</button>
              <button type="button" onClick={openRecipes}>Recipes</button>
              <button type="button" onClick={saveCurrentProjectAsTemplate}>Save Template</button>
              <button type="button" onClick={openSettings}>Settings</button>
              <button type="button" onClick={() => refreshJobs(true)}>Run Manager</button>
            </div>
            <input
              ref={importProjectRef}
              className="hidden"
              type="file"
              accept="application/json,.json"
              onChange={(event) => importProject(event.target.files?.[0])}
            />
          </CompactPanelSection>

          <CompactPanelSection title="Assets" shortTitle="Assets" icon={<Image size={15} />} popoverOpen={activeRailMenu === "Assets"} onCollapsedActivate={() => setActiveRailMenu((value) => value === "Assets" ? "" : "Assets")}>
            <div className="compact-stack">
              <label className="check-row">
                <input type="checkbox" checked={uploadToWaveSpeed} onChange={(event) => setUploadToWaveSpeed(event.target.checked)} />
                Upload to Cloud
              </label>
              <button type="button" onClick={() => fileInputRef.current?.click()}>
                <Upload size={16} /> Upload Asset
              </button>
              <input ref={fileInputRef} className="hidden" type="file" onChange={(event) => uploadAsset(event.target.files?.[0])} />
              <AssetList assets={project.assets || []} />
            </div>
          </CompactPanelSection>

          <CompactPanelSection title="Recent Runs" shortTitle="Runs" icon={<Clock3 size={15} />} popoverOpen={activeRailMenu === "Recent Runs"} onCollapsedActivate={() => setActiveRailMenu((value) => value === "Recent Runs" ? "" : "Recent Runs")}>
            <RunList runs={project.runs || []} />
          </CompactPanelSection>
        </div>
      </aside>

      <section className="main-stage" onClick={() => { setActiveRailMenu(""); setCanvasContextMenu(null); }}>
        <div className="canvas" onContextMenu={openCanvasContextMenu}>
          <button
            className="canvas-tidy-button"
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              autoTidyCanvas();
            }}
            title="Auto tidy nodes"
          >
            <WandSparkles size={15} /> Auto Tidy
          </button>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={(_, node) => { setCanvasContextMenu(null); setSelectedNodeId(node.id); }}
            onPaneClick={() => setCanvasContextMenu(null)}
            onPaneContextMenu={openCanvasContextMenu}
            fitView
            minZoom={0.25}
            maxZoom={1.5}
            nodesDraggable
            snapToGrid
            snapGrid={[20, 20]}
          >
            <Background color="#334155" gap={24} size={1} />
            <Controls />
            <MiniMap pannable zoomable nodeStrokeWidth={3} />
          </ReactFlow>
          {canvasContextMenu && (
            <CanvasContextMenu
              menu={canvasContextMenu}
              models={canvasContextModels}
              utilities={canvasContextUtilities}
              onAdd={(model) => addModelNode(model, { x: canvasContextMenu.flowX, y: canvasContextMenu.flowY })}
              onClose={() => setCanvasContextMenu(null)}
            />
          )}
        </div>

        <footer className="status-bar">{status}</footer>
      </section>

      {selectedNode && !UTILITY_NODE_TYPES.has(selectedNode.type) && (
        <NodeSettingsPopover
          node={selectedNode}
          model={selectedNodeModel}
          assets={project.assets || []}
          onChange={(field, value) => updateNodeInput(selectedNode.id, field, value)}
          onClose={() => setSelectedNodeId("")}
        />
      )}

    </main>
    <TemplatesModal
      open={modal === "templates"}
      templates={templates}
      onClose={() => setModal("")}
      onCreate={createProjectFromTemplate}
      onDelete={deleteTemplate}
    />
    <RecipesModal
      open={modal === "recipes"}
      recipes={recipes}
      onClose={() => setModal("")}
      onApply={applyRecipe}
      onCreate={createProjectFromRecipe}
    />
    <SettingsModal
      open={modal === "settings"}
      settings={settingsDraft}
      models={models}
      onChange={setSettingsDraft}
      onClose={() => setModal("")}
      onSave={saveSettings}
    />
    <PlanModal
      open={modal === "plan"}
      plan={workflowPlan}
      onClose={() => setModal("")}
      onPreviewSelected={() => previewWorkflowPlan("selected")}
      onPreviewFrom={() => previewWorkflowPlan("from_node")}
      selectedNodeId={selectedNodeId}
    />
    <JobsModal
      open={modal === "jobs"}
      jobs={jobs}
      projects={projects}
      onClose={() => setModal("")}
      onRefresh={() => refreshJobs(true)}
      onCancel={cancelJob}
      onRetry={retryJob}
      onClear={clearCompletedJobs}
      onOpenProject={(projectId) => {
        loadProject(projectId);
        setModal("");
      }}
    />
    </>
  );
}

function TemplatesModal({ open, templates, onClose, onCreate, onDelete }) {
  if (!open) return null;
  return (
    <Modal title="Templates" subtitle="Start from reusable workflows or manage saved templates." onClose={onClose}>
      <div className="modal-list">
        {templates.length ? templates.map((template) => (
          <article key={template.id} className="template-card">
            <header>
              <div>
                <h3>{template.name}</h3>
                <p>{template.description || "No description."}</p>
              </div>
              <span className={`pill ${template.builtin ? "pill-ok" : ""}`}>{template.builtin ? "built-in" : "user"}</span>
            </header>
            <div className="node-meta">
              <span>{template.category || "workflow"}</span>
              <span>{template.nodes?.length || 0} nodes</span>
              {(template.tags || []).slice(0, 4).map((tag) => <span key={tag}>{tag}</span>)}
            </div>
            <footer>
              <button type="button" onClick={() => onCreate(template)}>Create Project</button>
              {!template.builtin && <button type="button" onClick={() => onDelete(template)}>Delete</button>}
            </footer>
          </article>
        )) : <p className="empty">No templates found.</p>}
      </div>
    </Modal>
  );
}

function RecipesModal({ open, recipes, onClose, onApply, onCreate }) {
  if (!open) return null;
  return (
    <Modal title="Recipes" subtitle="Workflow starters that can be applied to the current project or opened as a new one." onClose={onClose}>
      <div className="modal-list">
        {recipes.length ? recipes.map((recipe) => (
          <article key={recipe.id} className="template-card">
            <header>
              <div>
                <h3>{recipe.name}</h3>
                <p>{recipe.description || "No description."}</p>
              </div>
              <span className="pill">{recipe.category || "workflow"}</span>
            </header>
            <div className="node-meta">
              <span>{recipe.nodes?.length || 0} nodes</span>
              {(recipe.required_capabilities || []).slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}
              {(recipe.optional_capabilities || []).slice(0, 2).map((tag) => <span key={tag}>{tag}</span>)}
            </div>
            <footer>
              <button type="button" onClick={() => onApply(recipe)}>Apply Here</button>
              <button type="button" onClick={() => onCreate(recipe)}>New Project</button>
            </footer>
          </article>
        )) : <p className="empty">No recipes found.</p>}
      </div>
    </Modal>
  );
}

function SettingsModal({ open, settings, models, onChange, onClose, onSave }) {
  if (!open || !settings) return null;
  const costGuard = settings.cost_guard || {};
  const overrides = settings.model_overrides || {};
  const overrideNodeTypes = [...new Set(models.filter((model) => model.source !== "utility").map((model) => model.node_type))]
    .sort()
    .slice(0, 40);
  const updateCost = (field, value) => onChange({
    ...settings,
    cost_guard: { ...costGuard, [field]: value }
  });
  const updateOverride = (nodeType, value) => {
    const next = { ...overrides };
    if (value) next[nodeType] = value;
    else delete next[nodeType];
    onChange({ ...settings, model_overrides: next });
  };

  return (
    <Modal title="Project Settings" subtitle="Cost guard and model override controls." onClose={onClose}>
      <div className="settings-grid-panel">
        <section className="modal-section">
          <h3>Cost Guard</h3>
          <label className="check-row">
            <input type="checkbox" checked={Boolean(costGuard.enabled)} onChange={(event) => updateCost("enabled", event.target.checked)} />
            Enable cost guard
          </label>
          <label className="field">
            Warn above USD
            <input type="number" min="0" step="0.001" value={costGuard.warn_at_usd_per_run ?? ""} onChange={(event) => updateCost("warn_at_usd_per_run", numberOrNull(event.target.value))} />
          </label>
          <label className="field">
            Max single run USD
            <input type="number" min="0" step="0.001" value={costGuard.block_at_usd_per_run ?? ""} onChange={(event) => updateCost("block_at_usd_per_run", numberOrNull(event.target.value))} />
          </label>
          <label className="field">
            Max workflow run USD
            <input type="number" min="0" step="0.001" value={costGuard.max_workflow_run_usd ?? ""} onChange={(event) => updateCost("max_workflow_run_usd", numberOrNull(event.target.value))} />
          </label>
          <label className="check-row">
            <input type="checkbox" checked={Boolean(costGuard.block_on_unknown_cost)} onChange={(event) => updateCost("block_on_unknown_cost", event.target.checked)} />
            Block unknown-cost models
          </label>
        </section>
        <section className="modal-section">
          <h3>Model Overrides</h3>
          <div className="override-list">
            {overrideNodeTypes.map((nodeType) => (
              <label className="field" key={nodeType}>
                {nodeType}
                <select value={overrides[nodeType] || ""} onChange={(event) => updateOverride(nodeType, event.target.value)}>
                  <option value="">Catalog/default model</option>
                  {models.filter((model) => model.node_type === nodeType && model.enabled).slice(0, 80).map((model) => (
                    <option key={model.id} value={model.default_model_id || model.model_id || model.id}>
                      {displayUiText(model.label || model.id)}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
        </section>
      </div>
      <footer className="modal-actions">
        <button type="button" onClick={onSave}>Save Settings</button>
        <button type="button" onClick={onClose}>Cancel</button>
      </footer>
    </Modal>
  );
}

function PlanModal({ open, plan, onClose, onPreviewSelected, onPreviewFrom, selectedNodeId }) {
  if (!open) return null;
  const steps = plan?.steps || [];
  const warnings = plan?.warnings || [];
  const errors = plan?.errors || [];
  return (
    <Modal title="Workflow Plan" subtitle="Preview execution order, warnings, and estimated cost." onClose={onClose}>
      <div className="modal-actions">
        <button type="button" onClick={onPreviewSelected} disabled={!selectedNodeId}>Selected</button>
        <button type="button" onClick={onPreviewFrom} disabled={!selectedNodeId}>From Selected</button>
      </div>
      <div className="plan-summary">
        <span className={`pill ${plan?.ok ? "pill-ok" : ""}`}>{plan?.ok ? "ready" : "blocked"}</span>
        <span>steps: {steps.length}</span>
        <span>known cost: {formatMyrFromUsd(plan?.estimated_known_cost_usd || 0)}</span>
      </div>
      <div className="modal-list">
        {steps.length ? steps.map((step) => (
          <article key={step.node_id} className="run-card">
            <strong>{displayUiText(step.display_name || step.node_type)}</strong>
            <span>{step.status} · {displayUiText(step.effective_model_id || step.model_id || "utility")}</span>
            {step.cost_guard?.message && <em>{step.cost_guard.message}</em>}
          </article>
        )) : <p className="empty">No runnable steps in this plan.</p>}
      </div>
      <MessageList title="Warnings" messages={warnings} />
      <MessageList title="Errors" messages={errors} />
    </Modal>
  );
}

function JobsModal({ open, jobs, projects, onClose, onRefresh, onCancel, onRetry, onClear, onOpenProject }) {
  if (!open) return null;
  return (
    <Modal title="Run Manager" subtitle="Queued, running, and completed local workflow jobs." onClose={onClose}>
      <div className="modal-actions">
        <button type="button" onClick={onRefresh}>Refresh Jobs</button>
        <button type="button" onClick={onClear}>Clear Completed</button>
      </div>
      <div className="modal-list">
        {jobs.length ? jobs.map((job) => {
          const canCancel = ["queued", "running", "cancel_requested"].includes(job.status);
          const canRetry = ["error", "cancelled"].includes(job.status);
          const projectName = projects.find((item) => item.id === job.project_id)?.name || job.project_id;
          return (
            <article key={job.id} className="job-card">
              <header>
                <strong>{shortId(job.id)}</strong>
                <span className={`pill status-${job.status}`}>{job.status}</span>
              </header>
              <div className="job-meta">
                <span>{job.kind}</span>
                <span>{projectName}</span>
                <span>{job.progress_current || 0} / {job.progress_total || 0} steps</span>
              </div>
              {job.errors?.[0]?.message && <p className="node-error">{job.errors[0].message}</p>}
              <footer>
                {canCancel && <button type="button" onClick={() => onCancel(job.id)}>Cancel</button>}
                {canRetry && <button type="button" onClick={() => onRetry(job.id)}>Retry</button>}
                <button type="button" onClick={() => onOpenProject(job.project_id)}>Open Project</button>
              </footer>
            </article>
          );
        }) : <p className="empty">No jobs yet.</p>}
      </div>
    </Modal>
  );
}

function MessageList({ title, messages }) {
  if (!messages?.length) return null;
  return (
    <section className="message-list">
      <h3>{title}</h3>
      {messages.map((message, index) => (
        <p key={`${title}-${index}`}>{message.message || String(message)}</p>
      ))}
    </section>
  );
}

function Modal({ title, subtitle, children, onClose }) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="modal-panel" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}>
        <header className="modal-header">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button className="icon-button" type="button" onClick={onClose} title="Close">
            <X size={16} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

function WorkflowCard({ data }) {
  const { node, model, assets, nodes, edges, selected, busy, onChange, onMoveStitchVideo, onRun, onSelect, onRemove, onBranch } = data;
  const fields = model?.fields || [];
  const linkableFields = fields.filter(isConnectableField);
  const hasSpecificInputs = linkableFields.length > 0;
  const isUtilityNode = UTILITY_NODE_TYPES.has(node.type);
  const isRunnableUtility = RUNNABLE_UTILITY_NODE_TYPES.has(node.type);
  const runnable = model?.enabled && (!isUtilityNode || isRunnableUtility);
  const outputKind = model?.output_kind || inferOutputKind(node);
  const showBranch = outputKind === "image" && (node.output_urls?.length || node.output_asset_ids?.length);
  const runCostLabel = model?.estimated_base_cost_usd != null ? formatMyrFromUsd(model.estimated_base_cost_usd) : "";
  const handleBaseTop = 62;
  const handleGap = 24;
  const outputHandleTop = 62;
  const minHandleHeight = Math.max(outputHandleTop, hasSpecificInputs ? handleBaseTop + (linkableFields.length - 1) * handleGap : outputHandleTop) + 14;

  return (
    <article className={`workflow-node ${selected ? "selected" : ""}`} style={{ minHeight: minHandleHeight }} onClick={() => onSelect(node.id)}>
      {!hasSpecificInputs && <Handle type="target" position={Position.Left} id="input" style={{ top: outputHandleTop }} />}
      <header className="node-header">
        <div className="drag-handle">::</div>
        <ProviderBadge provider={providerForModel(model || node)} />
        <div>
          <h3>{node.title}</h3>
          <p>{displayUiText(node.model_id || model?.default_model_id || model?.id || "Local utility")}</p>
        </div>
        <span className={`status status-${node.status || "idle"}`}>{node.status || "idle"}</span>
        <button className="icon-button nodrag" type="button" title="Remove node" onClick={(event) => { event.stopPropagation(); onRemove(node.id); }}>
          <X size={14} />
        </button>
      </header>

      {isUtilityNode && fields.length > 0 && (
        <div className="field-stack nodrag">
          {fields.map((field) => (
            <React.Fragment key={field.name}>
              {!(node.type === "stitch_video" && field.name === "videos") && (
                <NodeField
                  node={node}
                  field={field}
                  assets={assets}
                  value={node.inputs?.[field.name] ?? field.default ?? defaultValueForField(field)}
                  onChange={(value) => onChange(node.id, field.name, value)}
                />
              )}
              {node.type === "stitch_video" && field.name === "videos" && (
                <StitchVideoOrder
                  node={node}
                  nodes={nodes || []}
                  edges={edges || []}
                  assets={assets}
                  onMove={(index, direction) => onMoveStitchVideo?.(node.id, index, direction)}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      {node.error_message && <p className="node-error">{node.error_message}</p>}
      <OutputPreview node={node} assets={assets} />

      <footer className="node-actions nodrag">
        {runnable && (
          <button type="button" onClick={() => onRun(node.id)} disabled={busy}>
            {busy ? <Loader2 className="spin" size={16} /> : <Play size={16} />} Run{runCostLabel && <span className="button-cost">{runCostLabel}</span>}
          </button>
        )}
        {showBranch && (
          <button type="button" onClick={() => onBranch(node.id)}>
            Branch
          </button>
        )}
      </footer>

      {!hasSpecificInputs && <HandleLabel side="left" top={outputHandleTop} label="input" />}
      {linkableFields.map((field, index) => (
        <React.Fragment key={field.name}>
          <Handle
            type="target"
            id={field.name}
            position={Position.Left}
            style={{ top: handleBaseTop + index * handleGap }}
          />
          <HandleLabel side="left" top={handleBaseTop + index * handleGap} label={field.name} />
        </React.Fragment>
      ))}
      <HandleLabel side="right" top={outputHandleTop} label="output" />
      <Handle type="source" position={Position.Right} id="output" style={{ top: outputHandleTop }} />
    </article>
  );
}

function NodeSettingsPopover({ node, model, assets, onChange, onClose }) {
  const fields = model?.fields || [];
  const hasPromptOptimizer = supportsPromptOptimizer(fields, node.type);
  const settingsCount = fields.length + (hasPromptOptimizer ? 1 : 0);
  return (
    <aside className="node-settings-popover" aria-label="Selected node settings">
      <header className="node-settings-header">
        <ProviderBadge provider={providerForModel(model || node)} />
        <div>
          <h2>{node.title}</h2>
          <p>{displayUiText(node.model_id || model?.default_model_id || model?.id || "Local utility")}</p>
        </div>
        <span className={`status status-${node.status || "idle"}`}>{node.status || "idle"}</span>
        <button className="rail-popover-close" type="button" onClick={onClose} title="Close settings">
          <X size={18} />
        </button>
      </header>
      <div className="node-settings-body">
        <div className="node-settings-summary">
          <strong>Settings</strong>
          <span>{settingsCount} controls</span>
        </div>
        {fields.length ? (
          <div className="node-settings-fields">
            {fields.map((field) => (
              <NodeField
                key={field.name}
                node={node}
                field={field}
                assets={assets}
                value={node.inputs?.[field.name] ?? field.default ?? defaultValueForField(field)}
                onChange={(value) => onChange(field.name, value)}
                showDescription
              />
            ))}
            {hasPromptOptimizer && (
              <PromptOptimizerControls
                node={node}
                onChange={onChange}
              />
            )}
          </div>
        ) : (
          <p className="empty">No settings for this node.</p>
        )}
      </div>
    </aside>
  );
}

function HandleLabel({ side, top, label }) {
  return (
    <span className={`handle-label handle-label-${side}`} style={{ top }}>
      {label}
    </span>
  );
}

function NodeField({ node, field, assets, value, onChange, showDescription = false }) {
  const isPromptLocked = PROMPT_INPUTS.has(field.name) && !UTILITY_NODE_TYPES.has(node.type);
  const label = `${field.name}${field.required ? " *" : ""}`;
  const compatibleAssets = assets.filter((asset) => !field.asset_kind || asset.kind === field.asset_kind);
  const description = showDescription && field.description ? displayUiText(field.description) : "";

  if (isPromptLocked) {
    return (
      <label className="field locked-field">
        <FieldLabel label={label} description={description} />
        <input value="Connect Prompt Card or LLM output" readOnly />
      </label>
    );
  }

  if (field.type === "boolean") {
    return (
      <label className="check-row">
        <input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} />
        <FieldLabel label={label} description={description} />
      </label>
    );
  }

  if (field.type === "select" && field.options?.length) {
    return (
      <label className="field">
        <FieldLabel label={label} description={description} />
        <select value={value ?? ""} onChange={(event) => onChange(coerceFieldValue(field, event.target.value))}>
          {field.options.map((option) => (
            <option key={String(option)} value={String(option)}>
              {String(option)}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (isAssetLikeField(field)) {
    if (isListInputField(field)) {
      const selectedValues = Array.isArray(value) ? value : splitUiList(value);
      return (
        <label className="field">
          <FieldLabel label={label} description={description} />
          <select
            multiple
            value={selectedValues}
            onChange={(event) => onChange([...event.target.selectedOptions].map((option) => option.value))}
          >
            {compatibleAssets.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.filename || asset.id}
              </option>
            ))}
          </select>
          <small>Select one or more assets, or connect multiple upstream outputs.</small>
        </label>
      );
    }
    return (
      <label className="field">
        <FieldLabel label={label} description={description} />
        <select value={value ?? ""} onChange={(event) => onChange(event.target.value)}>
          <option value="">Connected input or select asset</option>
          {compatibleAssets.map((asset) => (
            <option key={asset.id} value={asset.id}>
              {asset.filename || asset.id}
            </option>
          ))}
        </select>
      </label>
    );
  }

  if (field.type === "textarea") {
    return (
      <label className="field">
        <FieldLabel label={label} description={description} />
        <textarea value={value ?? ""} placeholder={field.placeholder || field.description || ""} onChange={(event) => onChange(event.target.value)} />
      </label>
    );
  }

  return (
    <label className="field">
      <FieldLabel label={label} description={description} />
      <input
        type={field.type === "integer" || field.type === "number" ? "number" : "text"}
        min={field.min_value ?? undefined}
        max={field.max_value ?? undefined}
        step={field.step ?? undefined}
        value={value ?? ""}
        placeholder={field.placeholder || field.description || ""}
        onChange={(event) => onChange(coerceFieldValue(field, event.target.value))}
      />
    </label>
  );
}

function StitchVideoOrder({ node, nodes, edges, assets, onMove }) {
  const entries = stitchVideoOrderEntries(node, nodes, edges, assets);
  return (
    <section className="stitch-order">
      <header>
        <strong>Stitch order</strong>
        <span>{entries.length} clips</span>
      </header>
      {entries.length ? (
        <ol>
          {entries.map((entry, index) => (
            <li key={entry.orderKey}>
              <span className="stitch-order-index">{index + 1}</span>
              <div>
                <strong>{displayUiText(entry.label)}</strong>
                <span>{entry.detail}</span>
              </div>
              <button
                className="icon-button"
                type="button"
                disabled={index === 0}
                title="Move earlier"
                onClick={(event) => {
                  event.stopPropagation();
                  onMove(index, -1);
                }}
              >
                <ArrowUp size={13} />
              </button>
              <button
                className="icon-button"
                type="button"
                disabled={index === entries.length - 1}
                title="Move later"
                onClick={(event) => {
                  event.stopPropagation();
                  onMove(index, 1);
                }}
              >
                <ArrowDown size={13} />
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p>Connect or select at least two videos.</p>
      )}
    </section>
  );
}

function FieldLabel({ label, description }) {
  return (
    <span className="field-label">
      <span>{label}</span>
      {description && (
        <span className="field-help" tabIndex={0} aria-label={description}>
          <Info size={12} />
          <span className="field-tooltip" role="tooltip">{description}</span>
        </span>
      )}
    </span>
  );
}

function PromptOptimizerControls({ node, onChange }) {
  const enabled = Boolean(node.inputs?.use_prompt_optimizer);
  return (
    <div className="optimizer-box">
      <label className="check-row">
        <input type="checkbox" checked={enabled} onChange={(event) => onChange("use_prompt_optimizer", event.target.checked)} />
        <FieldLabel label="Use prompt optimizer" description="Improve connected prompt text before sending it to the model." />
      </label>
      <div className="optimizer-grid">
        <label className="field">
          <FieldLabel label="style" description="Tone used by the prompt optimizer." />
          <select
            disabled={!enabled}
            value={node.inputs?.prompt_optimizer_style || "default"}
            onChange={(event) => onChange("prompt_optimizer_style", event.target.value)}
          >
            <option value="default">default</option>
            <option value="photographic">photographic</option>
            <option value="cinematic">cinematic</option>
            <option value="product">product</option>
            <option value="anime">anime</option>
          </select>
        </label>
        <label className="field">
          <FieldLabel label="mode" description="Target output type for optimized wording." />
          <select
            disabled={!enabled}
            value={node.inputs?.prompt_optimizer_mode || (node.type.includes("video") ? "video" : "image")}
            onChange={(event) => onChange("prompt_optimizer_mode", event.target.value)}
          >
            <option value="image">image</option>
            <option value="video">video</option>
          </select>
        </label>
      </div>
    </div>
  );
}

function OutputPreview({ node, assets }) {
  const urls = [...(node.output_urls || [])];
  for (const assetId of node.output_asset_ids || []) {
    const asset = assets.find((item) => item.id === assetId);
    const url = asset?.public_url || asset?.wavespeed_url;
    if (url && !urls.includes(url)) urls.push(url);
  }
  const textOutput = node.last_run?.text_output;
  const structuredOutput = node.last_run?.structured_output;
  if (!urls.length && !textOutput && !structuredOutput) return null;

  return (
    <div className="output-preview">
      {urls.map((url) => (
        <PreviewMedia key={url} url={url} />
      ))}
      {textOutput && <pre>{textOutput}</pre>}
      {structuredOutput && <pre>{JSON.stringify(structuredOutput, null, 2)}</pre>}
    </div>
  );
}

function PreviewMedia({ url }) {
  const lower = url.toLowerCase();
  if (/\.(mp4|mov|webm|mkv)(\?|$)/.test(lower)) return <video src={url} controls />;
  if (/\.(mp3|wav|m4a|ogg|flac)(\?|$)/.test(lower)) return <audio src={url} controls />;
  if (/\.(png|jpe?g|webp|gif)(\?|$)/.test(lower) || lower.includes("image")) return <img src={url} alt="" />;
  return (
    <a href={url} target="_blank" rel="noreferrer">
      Open output
    </a>
  );
}

function LibraryCard({ model, onAdd }) {
  return (
    <article className="library-card">
      <div className="library-card-heading">
        <div>
          <h3>{displayUiText(model.label || model.display_name)}</h3>
          <p>{displayUiText(model.description || model.default_model_id || model.id)}</p>
        </div>
      </div>
      <div className="node-meta">
        <span>{model.category}</span>
        <span>{model.output_kind}</span>
        <span>{model.source}</span>
      </div>
      <button type="button" onClick={() => onAdd(model)}>
        <Plus size={16} /> Add Node
      </button>
    </article>
  );
}

function LibraryGroup({ group, collapseTick = 0, forceOpen = false, onAdd }) {
  const [open, setOpen] = useState(() => providerSortScore(group.provider) <= 1 || group.items.length <= 6);
  const [showAll, setShowAll] = useState(false);
  useEffect(() => {
    if (collapseTick > 0) {
      setOpen(false);
      setShowAll(false);
    }
  }, [collapseTick]);
  const isOpen = forceOpen || open;
  const visibleItems = forceOpen || showAll ? group.items : group.items.slice(0, 24);
  return (
    <section className="library-group">
      <button className="library-group-header" type="button" onClick={() => setOpen((value) => !value)}>
        <span>{isOpen ? "-" : "+"}</span>
        <ProviderBadge provider={group.provider} />
        <strong>{displayUiText(group.provider)}</strong>
        <em>{group.items.length}</em>
      </button>
      {isOpen && (
        <div className="library-group-items">
          {visibleItems.map((model) => (
            <LibraryCard key={`${model.id}-${model.node_type}`} model={model} onAdd={onAdd} />
          ))}
          {group.items.length > visibleItems.length && (
            <button className="library-show-more" type="button" onClick={() => setShowAll(true)}>
              Show all {group.items.length} models
            </button>
          )}
        </div>
      )}
    </section>
  );
}

function ProviderBadge({ provider }) {
  const [logoFailed, setLogoFailed] = useState(false);
  const meta = providerBadgeMeta(provider);
  const Icon = meta.icon === "river" ? Waves : meta.icon === "toolbox" ? BriefcaseBusiness : null;
  return (
    <span className={`provider-badge ${meta.className}`} title={displayUiText(provider)} aria-hidden="true">
      {meta.logoUrl && !logoFailed ? (
        <img src={meta.logoUrl} alt="" loading="eager" decoding="async" onError={() => setLogoFailed(true)} />
      ) : Icon ? (
        <Icon size={16} strokeWidth={2.4} />
      ) : (
        meta.text
      )}
    </span>
  );
}

function AssetList({ assets }) {
  if (!assets.length) return <p className="empty">No assets yet.</p>;
  return (
    <div className="asset-list">
      {assets.slice(0, 30).map((asset) => (
        <article key={asset.id} className="asset-card">
          <div className="asset-thumb">
            {asset.kind === "image" && (asset.public_url || asset.wavespeed_url) ? (
              <img src={asset.public_url || asset.wavespeed_url} alt="" />
            ) : (
              <Image size={18} />
            )}
          </div>
          <div>
            <strong>{asset.filename || asset.id}</strong>
            <span>{asset.kind} · {asset.id}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

function RunList({ runs }) {
  if (!runs.length) return <p className="empty">No runs yet.</p>;
  return (
    <div className="run-list">
      {runs.slice(0, 10).map((run) => (
        <article key={run.id || run.run_id} className="run-card">
          <strong>{run.status || "unknown"}</strong>
          <span>{displayUiText(run.model_id || run.type || run.kind)}</span>
          {run.errors?.length ? <em>{run.errors[0].message || run.errors[0]}</em> : null}
        </article>
      ))}
    </div>
  );
}

function CompactPanelSection({ title, shortTitle, icon, popoverClassName = "", popoverOpen = false, onCollapsedActivate, children }) {
  return (
    <details className={`compact-section ${popoverOpen ? "is-active" : ""}`} open>
      <summary
        title={title}
        onClick={(event) => {
          event.preventDefault();
          onCollapsedActivate?.();
        }}
      >
        {icon ? <span className="compact-section-icon">{icon}</span> : null}
        <span className="compact-section-label">{shortTitle || title}</span>
      </summary>
      {popoverOpen && (
        <div className={`rail-popover ${popoverClassName}`}>
          <header className="rail-popover-header">
            {icon ? <span className="compact-section-icon">{icon}</span> : null}
            <strong>{title}</strong>
            <button className="rail-popover-close" type="button" onClick={onCollapsedActivate} title={`Close ${title}`}>
              <X size={20} strokeWidth={2.2} />
            </button>
          </header>
          <div className="rail-popover-body">{children}</div>
        </div>
      )}
    </details>
  );
}

function resolveNodeModel(node, modelById, modelsByNodeType) {
  if (!node) return null;
  return (
    (node.model_id && modelById.get(node.model_id)) ||
    modelsByNodeType.get(node.type)?.find((model) => model.enabled) ||
    modelsByNodeType.get(node.type)?.[0] ||
    null
  );
}

function normalizeTargetHandle(handle, targetNode, targetModel) {
  if (handle && handle !== "input") return handle;
  const fields = targetModel?.fields || [];
  const preferred = [
    "images",
    "image",
    "reference_images",
    "reference_image",
    "source_images",
    "source_image",
    "target_images",
    "target_image",
    "videos",
    "video",
    "audios",
    "audio",
    "prompt",
    "text",
    "asset_id"
  ];
  return (
    preferred.find((name) => fields.some((field) => field.name === name)) ||
    fields.find(isConnectableField)?.name ||
    targetNode?.type && defaultTargetInputForType(targetNode.type) ||
    "input"
  );
}

function isConnectableField(field) {
  return FIELD_LINK_INPUTS.has(field.name) || isAssetLikeField(field);
}

function isAssetLikeField(field) {
  if (!field) return false;
  if (["boolean", "integer", "number", "select"].includes(field.type) && !field.asset_kind) {
    return false;
  }
  return (
    ASSET_INPUT_TYPES.has(field.type) ||
    field.type === "asset_url_list" ||
    field.type === "file_url" ||
    Boolean(field.asset_kind) ||
    field.name.endsWith("_image") ||
    field.name.endsWith("_images") ||
    field.name.endsWith("_video") ||
    field.name.endsWith("_videos") ||
    field.name.endsWith("_audio") ||
    field.name.endsWith("_audios") ||
    field.name.includes("asset")
  );
}

function isListInputField(field) {
  if (!field) return false;
  const name = String(field.name || "").toLowerCase();
  if (field.type === "asset_url_list") return true;
  if ([
    "images",
    "image_urls",
    "source_images",
    "target_images",
    "reference_images",
    "reference_urls",
    "refer_images",
    "mask_images",
    "clothes_images",
    "videos",
    "video_urls",
    "reference_videos",
    "ref_videos",
    "audios",
    "audio_urls",
    "reference_audios"
  ].includes(name)) return true;
  if (name.endsWith("_images") || name.endsWith("_videos") || name.endsWith("_audios")) return true;
  return name === "reference" && String(field.description || "").toLowerCase().includes("reference image");
}

function splitUiList(value) {
  if (!value) return [];
  return String(value)
    .replaceAll(",", "\n")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function stitchVideoOrderEntries(node, nodes, edges, assets) {
  const assetById = new Map((assets || []).map((asset) => [asset.id, asset]));
  const nodeById = new Map((nodes || []).map((item) => [item.id, item]));
  const selectedValues = Array.isArray(node.inputs?.videos) ? node.inputs.videos : splitUiList(node.inputs?.videos);
  const selectedEntries = selectedValues.map((value) => {
    const asset = assetById.get(value);
    return {
      kind: "asset",
      value,
      orderKey: `asset:${value}`,
      label: asset?.filename || value,
      detail: "selected asset"
    };
  });
  const connectedEntries = (edges || [])
    .filter((edge) => edgeTargetId(edge) === node.id && normalizeHandleName(edgeTargetInput(edge)) === "videos")
    .map((edge) => {
      const sourceNode = nodeById.get(edgeSourceId(edge));
      const asset = firstOutputAsset(sourceNode, assetById);
      return {
        kind: "edge",
        edge,
        orderKey: `edge:${edge.id}`,
        label: asset?.filename || sourceNode?.title || edgeSourceId(edge) || "Connected video",
        detail: sourceNode?.title ? `from ${sourceNode.title}` : "connected output"
      };
    });
  return orderedEntries([...selectedEntries, ...connectedEntries], node.inputs?.videos_order || []);
}

function orderedEntries(entries, order) {
  const orderList = Array.isArray(order) ? order.map(String) : splitUiList(order);
  if (!orderList.length) return entries;
  const orderIndex = new Map(orderList.map((key, index) => [key, index]));
  return entries
    .map((entry, index) => ({ entry, index }))
    .sort((a, b) => {
      const aRank = orderIndex.has(a.entry.orderKey) ? orderIndex.get(a.entry.orderKey) : orderList.length + a.index;
      const bRank = orderIndex.has(b.entry.orderKey) ? orderIndex.get(b.entry.orderKey) : orderList.length + b.index;
      return aRank - bRank || a.index - b.index;
    })
    .map((item) => item.entry);
}

function edgeSourceId(edge) {
  return edge.source_node_id || edge.source || edge.sourceNodeId || edge.source_node || edge.from || "";
}

function edgeTargetId(edge) {
  return edge.target_node_id || edge.target || edge.targetNodeId || edge.target_node || edge.to || "";
}

function edgeTargetInput(edge) {
  return edge.target_input || edge.target_handle || edge.targetHandle || "input";
}

function normalizeHandleName(value) {
  return String(value || "input");
}

function firstOutputAsset(node, assetById) {
  const assetId = node?.output_asset_ids?.[0];
  return assetId ? assetById.get(assetId) : null;
}

function defaultTargetInputForType(nodeType) {
  if (["text_to_image", "text_to_video", "text_to_3d"].includes(nodeType)) return "prompt";
  if (["llm_text", "llm_vision", "text_to_speech", "text_to_audio"].includes(nodeType)) return "text";
  if (["reference_to_image", "reference_to_video"].includes(nodeType)) return "reference_image";
  if (nodeType === "stitch_video") return "videos";
  if (nodeType === "video_last_frame") return "video";
  if (nodeType === "video_extend") return "video";
  if (nodeType.includes("video_effect")) return "image";
  if (nodeType.includes("image") || nodeType.includes("background")) return "image";
  return "input";
}

function defaultInputsForModel(model) {
  const inputs = {};
  for (const field of model.fields || []) {
    if (field.default !== undefined && field.default !== null) {
      inputs[field.name] = field.default;
    } else if (field.type === "boolean") {
      inputs[field.name] = false;
    }
  }
  if ((model.fields || []).some((field) => PROMPT_INPUTS.has(field.name)) && !UTILITY_NODE_TYPES.has(model.node_type)) {
    inputs.use_prompt_optimizer = false;
    inputs.prompt_optimizer_style = "default";
    inputs.prompt_optimizer_mode = model.node_type?.includes("video") ? "video" : "image";
  }
  return inputs;
}

function supportsPromptOptimizer(fields, nodeType) {
  return !UTILITY_NODE_TYPES.has(nodeType) && fields.some((field) => field.name === "prompt");
}

function defaultValueForField(field) {
  if (field.type === "boolean") return false;
  if (field.type === "integer" || field.type === "number") return "";
  return "";
}

function coerceFieldValue(field, value) {
  if (field.type === "integer") return value === "" ? "" : Number.parseInt(value, 10);
  if (field.type === "number") return value === "" ? "" : Number.parseFloat(value);
  if (field.type === "boolean") return Boolean(value);
  return value;
}

function projectPayload(project) {
  return {
    name: project.name,
    description: project.description || "",
    nodes: project.nodes || [],
    edges: project.edges || [],
    assets: project.assets || [],
    runs: project.runs || [],
    variant_sets: project.variant_sets || [],
    comparison_sets: project.comparison_sets || [],
    export_packages: project.export_packages || [],
    settings: project.settings
  };
}

function toFlowEdges(edges) {
  return edges
    .map((edge) => ({
      id: edge.id,
      source: edge.source_node_id || edge.source,
      target: edge.target_node_id || edge.target,
      sourceHandle: edge.source_output || edge.source_handle || "output",
      targetHandle: edge.target_input || edge.target_handle || "input"
    }))
    .filter((edge) => edge.id && edge.source && edge.target);
}

function flowEdgeToProjectEdge(edge) {
  return {
    id: edge.id,
    source_node_id: edge.source,
    target_node_id: edge.target,
    source_output: edge.sourceHandle || "output",
    target_input: edge.targetHandle || "input"
  };
}

function tidyNodePositions(nodes, edges) {
  const nodeIds = new Set(nodes.map((node) => node.id));
  const outgoing = new Map(nodes.map((node) => [node.id, []]));
  const indegree = new Map(nodes.map((node) => [node.id, 0]));
  for (const edge of toFlowEdges(edges)) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target) || edge.source === edge.target) continue;
    outgoing.get(edge.source)?.push(edge.target);
    indegree.set(edge.target, (indegree.get(edge.target) || 0) + 1);
  }

  const layer = new Map(nodes.map((node) => [node.id, 0]));
  const queue = nodes.filter((node) => (indegree.get(node.id) || 0) === 0).map((node) => node.id);
  const seen = new Set(queue);
  for (let index = 0; index < queue.length; index += 1) {
    const source = queue[index];
    for (const target of outgoing.get(source) || []) {
      layer.set(target, Math.max(layer.get(target) || 0, (layer.get(source) || 0) + 1));
      indegree.set(target, (indegree.get(target) || 0) - 1);
      if ((indegree.get(target) || 0) === 0 && !seen.has(target)) {
        seen.add(target);
        queue.push(target);
      }
    }
  }

  for (const node of nodes) {
    if (!seen.has(node.id)) layer.set(node.id, Math.max(layer.get(node.id) || 0, 0));
  }

  const groups = new Map();
  for (const node of nodes) {
    const nodeLayer = layer.get(node.id) || 0;
    if (!groups.has(nodeLayer)) groups.set(nodeLayer, []);
    groups.get(nodeLayer).push(node);
  }

  const positions = new Map();
  const xStart = 120;
  const yStart = 100;
  const xGap = 440;
  const yGap = 240;
  for (const [nodeLayer, items] of [...groups.entries()].sort((a, b) => a[0] - b[0])) {
    items
      .sort((a, b) => Number(a.y || 0) - Number(b.y || 0) || Number(a.x || 0) - Number(b.x || 0))
      .forEach((node, index) => {
        positions.set(node.id, {
          x: xStart + nodeLayer * xGap,
          y: yStart + index * yGap
        });
      });
  }
  return positions;
}

function detailMessage(body) {
  if (!body) return "";
  if (typeof body === "string") return body;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg || item.message || JSON.stringify(item)).join("; ");
  if (body.detail?.errors) return JSON.stringify(body.detail.errors);
  if (body.error) return String(body.error);
  return JSON.stringify(body);
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function shortId(value) {
  return String(value || "").split("_").at(-1)?.slice(0, 8) || String(value || "");
}

function librarySortScore(model) {
  if (model.category === "utility") return 0;
  if (model.node_type === "text_to_image" || model.node_type === "image_to_image") return 1;
  if (model.source === "curated") return 2;
  return 3;
}

function isUtilityLibraryModel(model) {
  return model.category === "utility" || model.source === "utility" || String(model.id || "").startsWith("local/utility/");
}

function providerForModel(model) {
  if (isUtilityLibraryModel(model)) {
    return "Utility";
  }
  const raw = model.model_id || model.default_model_id || model.id || model.label || "";
  const prefix = String(raw).split("/")[0] || "Other";
  const names = {
    "wavespeed-ai": "Default Model",
    alibaba: "Alibaba",
    openai: "OpenAI",
    xai: "Grok",
    "x-ai": "Grok",
    grok: "Grok",
    deepseek: "DeepSeek",
    bytedance: "ByteDance",
    vidu: "Vidu",
    luma: "Luma",
    runwayml: "Runway",
    "kwaivgi": "Kling",
    "stability-ai": "Stability AI",
    "ideogram-ai": "Ideogram",
    google: "Google",
    minimax: "MiniMax",
    tencent: "Tencent",
    tripo3d: "Tripo3D",
    hyper3d: "Hyper3D",
    skywork: "Skywork",
    "skywork-ai": "Skywork AI",
    bria: "BRIA",
    akool: "Akool",
    pika: "Pika",
    reve: "Reve",
    recraft: "Recraft",
    higgsfield: "Higgsfield",
    mureka: "Mureka"
  };
  return names[prefix] || titleCaseProvider(prefix);
}

function providerSortScore(provider) {
  if (provider === "Utility") return 0;
  if (provider === "Default Model") return 1;
  return 2;
}

function providerBadgeMeta(provider) {
  const key = String(provider || "Other").toLowerCase();
  const logo = (slug, color = "ffffff") =>
    color ? `https://cdn.simpleicons.org/${slug}/${color}` : `https://cdn.simpleicons.org/${slug}`;
  const favicon = (domain) => `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
  const badges = {
    "default model": { text: "DM", icon: "river", className: "provider-default" },
    utility: { text: "UT", icon: "toolbox", className: "provider-utility" },
    akool: { text: "A", className: "provider-logo", logoUrl: favicon("akool.com") },
    google: { text: "G", className: "provider-google", logoUrl: logo("google", "") },
    openai: { text: "AI", className: "provider-openai", logoUrl: favicon("openai.com") },
    grok: { text: "x", className: "provider-grok", logoUrl: logo("x") },
    xai: { text: "x", className: "provider-grok", logoUrl: logo("x") },
    deepseek: { text: "DS", className: "provider-deepseek", logoUrl: logo("deepseek") },
    alibaba: { text: "A", className: "provider-alibaba", logoUrl: logo("alibabacloud") },
    bria: { text: "B", className: "provider-bria", logoUrl: favicon("bria.ai") },
    bytedance: { text: "BD", className: "provider-bytedance", logoUrl: logo("bytedance") },
    "character ai": { text: "CA", className: "provider-character", logoUrl: favicon("character.ai") },
    chatterbox: { text: "CB", className: "provider-logo", logoUrl: favicon("resemble.ai") },
    "clarity ai": { text: "CA", className: "provider-logo", logoUrl: favicon("clarity.ai") },
    decart: { text: "D", className: "provider-logo", logoUrl: favicon("decart.ai") },
    "elevenlabs": { text: "11", className: "provider-elevenlabs", logoUrl: logo("elevenlabs") },
    heygen: { text: "H", className: "provider-heygen", logoUrl: favicon("heygen.com") },
    hyper3d: { text: "H3", className: "provider-logo", logoUrl: favicon("hyper3d.ai") },
    inworld: { text: "I", className: "provider-logo", logoUrl: favicon("inworld.ai") },
    kling: { text: "K", className: "provider-kling", logoUrl: logo("kuaishou") },
    leonardoai: { text: "L", className: "provider-leonardo", logoUrl: favicon("leonardo.ai") },
    lightricks: { text: "LT", className: "provider-lightricks", logoUrl: favicon("lightricks.com") },
    luma: { text: "L", className: "provider-luma", logoUrl: favicon("lumalabs.ai") },
    microsoft: { text: "M", className: "provider-microsoft", logoUrl: favicon("microsoft.com") },
    midjourney: { text: "MJ", className: "provider-midjourney", logoUrl: favicon("midjourney.com") },
    runway: { text: "R", className: "provider-runway", logoUrl: favicon("runwayml.com") },
    "stability ai": { text: "S", className: "provider-stability", logoUrl: favicon("stability.ai") },
    ideogram: { text: "I", className: "provider-ideogram", logoUrl: favicon("ideogram.ai") },
    minimax: { text: "M", className: "provider-minimax", logoUrl: favicon("minimax.io") },
    "mirelo ai": { text: "MI", className: "provider-logo", logoUrl: favicon("mirelo.ai") },
    "mureka ai": { text: "MU", className: "provider-logo", logoUrl: favicon("mureka.ai") },
    nvidia: { text: "NV", className: "provider-nvidia", logoUrl: logo("nvidia") },
    tencent: { text: "T", className: "provider-tencent", logoUrl: logo("tencentqq") },
    pika: { text: "P", className: "provider-pika", logoUrl: favicon("pika.art") },
    pixverse: { text: "PX", className: "provider-logo", logoUrl: favicon("pixverse.ai") },
    "pruna ai": { text: "P", className: "provider-logo", logoUrl: favicon("pruna.ai") },
    recraft: { text: "RC", className: "provider-recraft", logoUrl: favicon("recraft.ai") },
    "recraft ai": { text: "RC", className: "provider-recraft", logoUrl: favicon("recraft.ai") },
    reve: { text: "R", className: "provider-logo", logoUrl: favicon("reve.art") },
    "scenario marketing": { text: "S", className: "provider-logo", logoUrl: favicon("scenario.com") },
    "skywork ai": { text: "S", className: "provider-logo", logoUrl: favicon("skywork.ai") },
    sonilo: { text: "S", className: "provider-logo", logoUrl: favicon("sonilo.ai") },
    sourceful: { text: "S", className: "provider-logo", logoUrl: favicon("sourceful.com") },
    sync: { text: "S", className: "provider-logo", logoUrl: favicon("sync.so") },
    topaz: { text: "T", className: "provider-topaz", logoUrl: favicon("topazlabs.com") },
    tripo3d: { text: "3D", className: "provider-logo", logoUrl: favicon("tripo3d.ai") },
    veed: { text: "V", className: "provider-veed", logoUrl: favicon("veed.io") },
    "video effects": { text: "FX", className: "provider-logo" },
    vidu: { text: "V", className: "provider-logo", logoUrl: favicon("vidu.com") },
    "z ai": { text: "Z", className: "provider-logo", logoUrl: favicon("z.ai") },
    higgsfield: { text: "H", className: "provider-higgsfield", logoUrl: favicon("higgsfield.ai") },
    "black forest labs": { text: "BF", className: "provider-black-forest" },
    fal: { text: "F", className: "provider-fal" }
  };
  if (badges[key]) return badges[key];
  const text = String(provider || "Other")
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "O";
  return { text, className: "provider-generic" };
}

function titleCaseProvider(value) {
  return String(value || "Other")
    .replaceAll("-", " ")
    .replaceAll("_", " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function inferOutputKind(node) {
  if (node.type.includes("video")) return "video";
  if (node.type.includes("audio") || node.type.includes("speech")) return "audio";
  if (node.type.includes("image") || node.type.includes("background")) return "image";
  return "other";
}

function CanvasContextMenu({ menu, models, utilities, onAdd, onClose }) {
  const promptModel = utilities.find((model) => model.node_type === "prompt_card");
  const primaryItems = [
    promptModel ? { id: "prompt", label: "Prompt", directModel: promptModel } : null,
    { id: "utility", label: "Utility", kind: "utility" },
    { id: "image", label: "Image models", kind: "image" },
    { id: "video", label: "Video models", kind: "video" },
    { id: "audio", label: "Audio models", kind: "audio" },
    { id: "three_d", label: "3D models", kind: "3d" },
    { id: "llm", label: "LLM models", kind: "llm" },
    { id: "all", label: "All models", kind: "all" }
  ].filter(Boolean);
  const [query, setQuery] = useState("");
  const [activePrimary, setActivePrimary] = useState("");
  const [costSort, setCostSort] = useState("default");
  const filteredItems = useMemo(
    () => contextMenuFilteredItems(models, utilities, query),
    [models, utilities, query]
  );
  const activeItem = primaryItems.find((item) => item.id === activePrimary) || null;
  const activeGroups = useMemo(
    () => contextMenuGroups(activeItem, filteredItems.models, filteredItems.utilities),
    [activeItem, filteredItems]
  );
  const [activeGroup, setActiveGroup] = useState("");
  const selectedGroup = activeGroups.find((group) => group.id === activeGroup) || null;
  const sortedGroupItems = useMemo(() => {
    const items = [...(selectedGroup?.items || [])];
    if (costSort === "default") return items;
    return items.sort((a, b) => {
      const costA = modelEstimatedCost(a);
      const costB = modelEstimatedCost(b);
      if (costA == null && costB == null) return 0;
      if (costA == null) return 1;
      if (costB == null) return -1;
      return costSort === "asc" ? costA - costB : costB - costA;
    });
  }, [selectedGroup, costSort]);
  const costSortLabel = costSort === "asc" ? "Cheapest first" : costSort === "desc" ? "Highest first" : "Sort by cost";

  useEffect(() => {
    if (activeGroup && !activeGroups.some((group) => group.id === activeGroup)) {
      setActiveGroup("");
    }
  }, [activeGroups, activeGroup]);

  const showGroupColumn = activeItem && !activeItem.directModel;
  const showModelColumn = showGroupColumn && Boolean(activeGroup);

  return (
    <div
      className={`canvas-context-menu ${activePrimary ? "" : "single-column"}`}
      style={{ left: menu.screenX, top: menu.screenY }}
      onClick={(event) => event.stopPropagation()}
      onContextMenu={(event) => event.preventDefault()}
    >
      <section className="context-menu-column context-menu-primary">
        <label className="context-search">
          <Search size={15} />
          <input
            value={query}
            autoFocus
            placeholder="Search"
            onChange={(event) => {
              setQuery(event.target.value);
              setActivePrimary("all");
            }}
          />
        </label>
        <div className="context-menu-list">
          {primaryItems.map((item) => (
            <button
              key={item.id}
              className={activePrimary === item.id ? "active" : ""}
              type="button"
              onClick={() => {
                if (item.directModel) {
                  onAdd(item.directModel);
                  return;
                }
                setActivePrimary(item.id);
                setActiveGroup("");
                setCostSort("default");
              }}
            >
              <span>{item.label}</span>
              {!item.directModel && <ChevronRight className="context-chevron" size={15} />}
            </button>
          ))}
        </div>
      </section>

      {showGroupColumn && (
        <section className="context-menu-column context-menu-secondary">
          <div className="context-column-title">{activeItem.label}</div>
          <div className="context-menu-list">
            {activeGroups.map((item) => (
              <button
                key={item.id}
                className={selectedGroup?.id === item.id ? "active" : ""}
                type="button"
                onClick={() => setActiveGroup(item.id)}
              >
                <span>{item.label}</span>
                <ChevronRight className="context-chevron" size={15} />
              </button>
            ))}
            {!activeGroups.length && <p className="context-empty">No matches</p>}
          </div>
        </section>
      )}

      {showModelColumn && (
        <section className="context-menu-column context-menu-tertiary">
          <div className="context-column-header">
            <div className="context-column-title">{selectedGroup?.label || "Models"}</div>
            <button
              className={`context-sort-button ${costSort !== "default" ? "active" : ""}`}
              type="button"
              title={costSortLabel}
              onClick={() => setCostSort((value) => value === "default" ? "asc" : value === "asc" ? "desc" : "default")}
            >
              {costSort === "desc" ? <ArrowDown size={13} /> : <ArrowUp size={13} />}
              <span>{costSortLabel}</span>
            </button>
          </div>
          <div className="context-menu-list">
            {sortedGroupItems.map((model) => (
              <ContextModelButton key={`${model.id}-${model.node_type}`} model={model} onAdd={onAdd} />
            ))}
            {selectedGroup && !selectedGroup.items.length && <p className="context-empty">No models</p>}
          </div>
        </section>
      )}
    </div>
  );
}

function ContextModelButton({ model, onAdd }) {
  const label = model.label || model.display_name || model.id;
  return (
    <button type="button" onClick={() => onAdd(model)}>
      <ProviderBadge provider={providerForModel(model)} />
      <span className="context-model-copy">
        <span className="context-model-label" title={displayUiText(label)}>{compactSlashPath(label)}</span>
        <span className="context-model-cost">{estimatedCostLabel(model)}</span>
      </span>
    </button>
  );
}

function contextMenuFilteredItems(models, utilities, query) {
  const needle = query.trim().toLowerCase();
  const matches = (model) => {
    if (!needle) return true;
    return [
      model.label,
      model.display_name,
      model.id,
      model.default_model_id,
      model.model_id,
      model.node_type,
      model.category,
      providerForModel(model),
      ...(model.capability_tags || [])
    ].join(" ").toLowerCase().includes(needle);
  };
  return {
    models: models.filter(matches),
    utilities: utilities.filter((model) => model.node_type !== "prompt_card").filter(matches)
  };
}

function contextMenuGroups(activeItem, models, utilities) {
  if (!activeItem || activeItem.directModel) return [];
  const items = activeItem.kind === "utility" ? utilities : models.filter((model) => contextModelKind(model) === activeItem.kind || activeItem.kind === "all");
  const groups = new Map();
  for (const model of items) {
    const label = activeItem.kind === "utility" ? "Tools" : contextModelGroupLabel(model);
    const id = label.toLowerCase().replace(/[^a-z0-9]+/g, "_") || "models";
    if (!groups.has(id)) groups.set(id, { id, label, items: [] });
    groups.get(id).items.push(model);
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      items: group.items.sort((a, b) => providerForModel(a).localeCompare(providerForModel(b)) || String(a.label || a.id).localeCompare(String(b.label || b.id)))
    }))
    .sort((a, b) => contextGroupSortScore(a.label) - contextGroupSortScore(b.label) || a.label.localeCompare(b.label));
}

function contextModelKind(model) {
  const nodeType = String(model.node_type || "");
  const category = String(model.category || "");
  const outputKind = String(model.output_kind || "");
  if (nodeType.startsWith("llm_")) return "llm";
  if (category === "3d" || nodeType.includes("_3d") || outputKind === "3d") return "3d";
  if (category === "video" || outputKind === "video" || nodeType.includes("video")) return "video";
  if (category === "audio" || outputKind === "audio" || nodeType.includes("audio") || nodeType.includes("speech") || nodeType.includes("voice")) return "audio";
  if (category === "image" || outputKind === "image" || nodeType.includes("image") || nodeType.includes("background")) return "image";
  return "all";
}

function contextModelGroupLabel(model) {
  const capability = String(model.primary_capability || model.node_type || "");
  const labels = {
    text_to_image: "Generate from text",
    image_to_image: "Generate from image",
    reference_to_image: "Reference image",
    upscale_image: "Enhance images",
    remove_background: "Edit images",
    remove_object: "Edit images",
    text_to_video: "Generate from text",
    image_to_video: "Generate from image",
    start_end_to_video: "Start/end video",
    reference_to_video: "Reference video",
    video_extend: "Extend videos",
    video_effect: "Video effects",
    text_to_speech: "Generate voice",
    text_to_audio: "Generate audio",
    speech_to_text: "Transcribe",
    generate_voice: "Generate voice",
    llm_text: "Text LLM",
    llm_vision: "Vision LLM",
    image_to_3d: "Generate from image",
    text_to_3d: "Generate from text"
  };
  return labels[capability] || titleCaseProvider(capability || providerForModel(model));
}

function contextGroupSortScore(label) {
  const order = [
    "Tools",
    "Generate from text",
    "Generate from image",
    "Reference image",
    "Reference video",
    "Start/end video",
    "Extend videos",
    "Video effects",
    "Edit images",
    "Enhance images",
    "Generate voice",
    "Generate audio",
    "Transcribe",
    "Text LLM",
    "Vision LLM"
  ];
  const index = order.indexOf(label);
  return index === -1 ? 100 : index;
}

const nodeTypes = { workflowCard: WorkflowCard };

createRoot(document.getElementById("root")).render(
  <ReactFlowProvider>
    <App />
  </ReactFlowProvider>
);
