from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class AssetKind(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"
    other = "other"


class NodeType(str, Enum):
    upload_image = "upload_image"
    text_to_image = "text_to_image"
    image_to_image = "image_to_image"
    reference_to_image = "reference_to_image"
    upscale_image = "upscale_image"
    remove_background = "remove_background"
    remove_object = "remove_object"
    image_to_video = "image_to_video"
    start_end_to_video = "start_end_to_video"
    text_to_video = "text_to_video"
    reference_to_video = "reference_to_video"
    video_extend = "video_extend"
    video_effect = "video_effect"
    text_to_speech = "text_to_speech"
    text_to_audio = "text_to_audio"
    speech_to_text = "speech_to_text"
    generate_voice = "generate_voice"
    talking_avatar = "talking_avatar"
    lip_sync = "lip_sync"
    portrait_transfer = "portrait_transfer"
    image_to_3d = "image_to_3d"
    text_to_3d = "text_to_3d"
    generic_wavespeed = "generic_wavespeed"


class NodeStatus(str, Enum):
    idle = "idle"
    queued = "queued"
    running = "running"
    success = "success"
    error = "error"
    skipped = "skipped"


class Asset(BaseModel):
    id: str = Field(default_factory=lambda: new_id("asset"))
    kind: AssetKind = AssetKind.other
    filename: str
    content_type: str | None = None
    local_path: str | None = None
    public_url: str | None = None
    wavespeed_url: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CanvasNode(BaseModel):
    id: str = Field(default_factory=lambda: new_id("node"))
    type: NodeType
    title: str
    model_id: str | None = None
    estimated_base_cost_usd: float | None = None
    x: float = 120
    y: float = 120
    inputs: Dict[str, Any] = Field(default_factory=dict)
    output_asset_ids: List[str] = Field(default_factory=list)
    output_urls: List[str] = Field(default_factory=list)
    last_run: Dict[str, Any] = Field(default_factory=dict)
    status: NodeStatus = NodeStatus.idle
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CanvasEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: new_id("edge"))
    source_node_id: str = ""
    target_node_id: str = ""
    source_handle: str = "output"
    target_handle: str = "input"
    source_output: str | None = None
    target_input: str | None = None
    source: str | None = None
    target: str | None = None
    source_node: str | None = None
    target_node: str | None = None
    sourceNodeId: str | None = None
    targetNodeId: str | None = None
    from_node: str | None = Field(default=None, validation_alias="from")
    to: str | None = None


class CostGuardSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = False
    warn_at_usd_per_run: float | None = Field(
        default=None,
        validation_alias=AliasChoices("warn_at_usd_per_run", "warn_above_usd"),
    )
    block_at_usd_per_run: float | None = Field(
        default=None,
        validation_alias=AliasChoices("block_at_usd_per_run", "max_single_run_usd"),
    )
    max_workflow_run_usd: float | None = None
    block_on_unknown_cost: bool = False

    @model_validator(mode="after")
    def validate_costs(self):
        cost_fields = {
            "warn_at_usd_per_run": self.warn_at_usd_per_run,
            "block_at_usd_per_run": self.block_at_usd_per_run,
            "max_workflow_run_usd": self.max_workflow_run_usd,
        }
        for field_name, value in cost_fields.items():
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be greater than or equal to zero.")

        if (
            self.warn_at_usd_per_run is not None
            and self.block_at_usd_per_run is not None
            and self.warn_at_usd_per_run > self.block_at_usd_per_run
        ):
            raise ValueError("warn_at_usd_per_run cannot exceed block_at_usd_per_run.")
        return self


class ProjectSettings(BaseModel):
    model_overrides: Dict[str, str] = Field(default_factory=dict)
    cost_guard: CostGuardSettings = Field(default_factory=CostGuardSettings)


class CostGuardSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    enabled: bool | None = None
    warn_at_usd_per_run: float | None = Field(
        default=None,
        validation_alias=AliasChoices("warn_at_usd_per_run", "warn_above_usd"),
    )
    block_at_usd_per_run: float | None = Field(
        default=None,
        validation_alias=AliasChoices("block_at_usd_per_run", "max_single_run_usd"),
    )
    max_workflow_run_usd: float | None = None
    block_on_unknown_cost: bool | None = None

    @model_validator(mode="after")
    def validate_costs(self):
        cost_fields = {
            "warn_at_usd_per_run": self.warn_at_usd_per_run,
            "block_at_usd_per_run": self.block_at_usd_per_run,
            "max_workflow_run_usd": self.max_workflow_run_usd,
        }
        for field_name, value in cost_fields.items():
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be greater than or equal to zero.")

        if (
            self.warn_at_usd_per_run is not None
            and self.block_at_usd_per_run is not None
            and self.warn_at_usd_per_run > self.block_at_usd_per_run
        ):
            raise ValueError("warn_at_usd_per_run cannot exceed block_at_usd_per_run.")
        return self


class ProjectSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_overrides: Optional[Dict[str, str]] = None
    cost_guard: Optional[CostGuardSettingsUpdate] = None


class Project(BaseModel):
    id: str = Field(default_factory=lambda: new_id("project"))
    name: str = "Untitled Workflow"
    description: str = ""
    nodes: List[CanvasNode] = Field(default_factory=list)
    edges: List[CanvasEdge] = Field(default_factory=list)
    assets: List[Asset] = Field(default_factory=list)
    runs: List[Dict[str, Any]] = Field(default_factory=list)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectCreate(BaseModel):
    name: str = "Untitled Workflow"
    description: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[CanvasNode]] = None
    edges: Optional[List[CanvasEdge]] = None
    assets: Optional[List[Asset]] = None
    runs: Optional[List[Dict[str, Any]]] = None
    settings: Optional[ProjectSettings] = None


class ProjectExportEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_name: str = Field(
        default="wavespeed_canvas_project_export",
        validation_alias="schema",
        serialization_alias="schema",
    )
    version: int = 1
    exported_at: datetime = Field(default_factory=utc_now)
    app: str = "WaveSpeed Canvas MVP"
    project: Project
    warnings: List[str] = Field(default_factory=list)


class ProjectImportRequest(BaseModel):
    import_data: Dict[str, Any]
    mode: str = "copy"
    name: str | None = None
    include_outputs: bool = True
    include_run_history: bool = False


class ProjectDuplicateRequest(BaseModel):
    name: str | None = None
    include_outputs: bool = True
    include_run_history: bool = False


class ProjectImportResponse(BaseModel):
    ok: bool = True
    project: Project
    warnings: List[str] = Field(default_factory=list)
    id_map: Dict[str, Dict[str, str]] = Field(default_factory=dict)


class WorkflowTemplate(BaseModel):
    id: str = Field(default_factory=lambda: new_id("template"))
    name: str
    description: str = ""
    category: str = "image"
    tags: List[str] = Field(default_factory=list)
    version: int = 1
    builtin: bool = False
    nodes: List[CanvasNode] = Field(default_factory=list)
    edges: List[CanvasEdge] = Field(default_factory=list)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkflowTemplateCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "image"
    tags: List[str] = Field(default_factory=list)
    nodes: List[CanvasNode] = Field(default_factory=list)
    edges: List[CanvasEdge] = Field(default_factory=list)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class WorkflowTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    tags: List[str] | None = None
    nodes: List[CanvasNode] | None = None
    edges: List[CanvasEdge] | None = None
    settings: ProjectSettings | None = None


class TemplateFromProjectRequest(BaseModel):
    name: str
    description: str = ""
    category: str = "image"
    tags: List[str] = Field(default_factory=list)
    include_outputs: bool = False
    include_settings: bool = True


class CreateProjectFromTemplateRequest(BaseModel):
    name: str | None = None
    description: str = ""


class ModelField(BaseModel):
    name: str
    type: str
    required: bool = False
    default: Any = None
    description: str = ""


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


class ModelSpec(BaseModel):
    id: str
    label: str
    node_type: NodeType
    category: str
    output_kind: AssetKind
    enabled: bool = True
    description: str = ""
    fields: List[ModelField] = Field(default_factory=list)
    default_model_id: str | None = None
    display_name: str | None = None
    estimated_base_cost_usd: float | None = None
    cost_unit: str | None = None
    pricing_note: str | None = None
    cost: CostMetadata | None = None
    docs_url: str | None = None
    verification_status: str = "candidate"
    enabled_reason: str | None = None


class CategorySpec(BaseModel):
    id: str
    label: str
    description: str
    recommended_for_mvp: bool = False
    node_type: NodeType | None = None
    node_types: List[NodeType] = Field(default_factory=list)


class RunNodeRequest(BaseModel):
    project_id: str | None = None
    node_id: str | None = None
    node_type: NodeType = NodeType.generic_wavespeed
    model_id: str | None = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    save_to_project: bool = True


class EstimateRunRequest(BaseModel):
    project_id: str | None = None
    node_id: str | None = None
    node_type: NodeType = NodeType.generic_wavespeed
    model_id: str | None = None


class EstimateRunResponse(BaseModel):
    ok: bool
    node_type: NodeType
    model_id: str | None = None
    model_source: str
    estimated_base_cost_usd: float | None = None
    cost_unit: str | None = None
    pricing_note: str | None = None
    warning: str
    enabled: bool = False
    enabled_reason: str | None = None
    verification_status: str | None = None
    requires_confirmation: bool = False
    blocked: bool = False
    cost_guard_message: str | None = None
    status: str | None = None
    message: str | None = None
    limit_usd: float | None = None


class RunNodeResponse(BaseModel):
    ok: bool
    model_id: str
    node_id: str | None = None
    raw_output: Dict[str, Any] = Field(default_factory=dict)
    output_urls: List[str] = Field(default_factory=list)
    asset_ids: List[str] = Field(default_factory=list)
    error: str | None = None


class ErrorResponse(BaseModel):
    detail: str
