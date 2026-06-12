from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.storage import read_json, write_json
from app.schemas import (
    CanvasEdge,
    CanvasNode,
    NodeStatus,
    NodeType,
    Project,
    ProjectSettings,
    WorkflowTemplate,
    WorkflowTemplateCreate,
    new_id,
)
from app.services import portable_project, project_store
from app.services.project_validation import validate_edges_reference_nodes, validate_project_settings
from app.services.registry import get_model_for_node

TEMPLATE_ID_RE = re.compile(r"^template_[a-zA-Z0-9_-]{3,80}$")


class TemplateStoreError(ValueError):
    """Base error for local template persistence."""


class TemplateNotFoundError(TemplateStoreError):
    pass


class BuiltinTemplateError(TemplateStoreError):
    pass


def builtin_templates() -> list[WorkflowTemplate]:
    return [
        WorkflowTemplate(
            id="template_basic_image_remix",
            name="Basic Image Remix",
            description="Generate an image, then remix it.",
            category="image",
            tags=["image", "remix", "starter"],
            builtin=True,
            nodes=[
                template_node("node_text_image", NodeType.text_to_image, "Text to Image", 80, 80, {"prompt": "A clean product hero image, studio lighting"}),
                template_node("node_remix", NodeType.image_to_image, "Image to Image", 430, 120, {"prompt": "Create a fresh campaign variation"}),
            ],
            edges=[template_edge("edge_text_to_remix", "node_text_image", "node_remix", "image")],
        ),
        WorkflowTemplate(
            id="template_product_cleanup",
            name="Product Cleanup",
            description="Upload a product image, remove the background, and upscale it.",
            category="image",
            tags=["product", "cleanup", "upscale"],
            builtin=True,
            nodes=[
                template_node("node_upload", NodeType.upload_image, "Upload Image", 80, 80, {}),
                template_node("node_bg", NodeType.remove_background, "Remove Background", 430, 80, {}),
                template_node("node_upscale", NodeType.upscale_image, "Upscale Image", 780, 80, {}),
            ],
            edges=[
                template_edge("edge_upload_bg", "node_upload", "node_bg", "image"),
                template_edge("edge_bg_upscale", "node_bg", "node_upscale", "image"),
            ],
        ),
        WorkflowTemplate(
            id="template_image_to_short_video",
            name="Image to Short Video",
            description="Generate a still image and animate it into a short clip.",
            category="video",
            tags=["image", "video", "motion"],
            builtin=True,
            nodes=[
                template_node("node_text_image", NodeType.text_to_image, "Text to Image", 80, 80, {"prompt": "A cinematic product scene"}),
                template_node("node_video", NodeType.image_to_video, "Image to Video", 430, 120, {"prompt": "Slow cinematic camera move"}),
            ],
            edges=[template_edge("edge_image_video", "node_text_image", "node_video", "image")],
        ),
        WorkflowTemplate(
            id="template_ugc_starter",
            name="UGC Starter",
            description="A lightweight product UGC workflow with image cleanup, remix, video, and voiceover.",
            category="ugc",
            tags=["ugc", "product", "video", "voiceover"],
            builtin=True,
            nodes=[
                template_node("node_upload", NodeType.upload_image, "Upload Image", 80, 90, {}),
                template_node("node_bg", NodeType.remove_background, "Remove Background", 390, 90, {}),
                template_node("node_remix", NodeType.image_to_image, "Image to Image", 700, 90, {"prompt": "Turn this product into a social ad image"}),
                template_node("node_video", NodeType.image_to_video, "Image to Video", 1010, 90, {"prompt": "Handheld UGC-style product reveal"}),
                template_node("node_tts", NodeType.text_to_speech, "Text to Speech", 700, 430, {"text": "Here is why this product belongs in your daily routine."}),
            ],
            edges=[
                template_edge("edge_upload_bg", "node_upload", "node_bg", "image"),
                template_edge("edge_bg_remix", "node_bg", "node_remix", "image"),
                template_edge("edge_remix_video", "node_remix", "node_video", "image"),
            ],
        ),
        WorkflowTemplate(
            id="template_voiceover_only",
            name="Voiceover Only",
            description="Create a standalone voiceover asset.",
            category="audio",
            tags=["audio", "voiceover"],
            builtin=True,
            nodes=[
                template_node("node_tts", NodeType.text_to_speech, "Text to Speech", 90, 90, {"text": "Write your voiceover script here."}),
            ],
            edges=[],
        ),
    ]


def template_node(node_id: str, node_type: NodeType, title: str, x: float, y: float, inputs: dict) -> CanvasNode:
    return CanvasNode(id=node_id, type=node_type, title=title, x=x, y=y, inputs=inputs)


def template_edge(edge_id: str, source: str, target: str, target_input: str) -> CanvasEdge:
    return CanvasEdge(
        id=edge_id,
        source_node_id=source,
        target_node_id=target,
        source_handle="output",
        target_handle=target_input,
        target_input=target_input,
    )


async def list_templates(
    *,
    category: str | None = None,
    builtin: bool | None = None,
    settings: Settings | None = None,
) -> list[WorkflowTemplate]:
    templates = builtin_templates() + await list_user_templates(settings)
    if category:
        templates = [template for template in templates if template.category == category]
    if builtin is not None:
        templates = [template for template in templates if template.builtin is builtin]
    return sorted(templates, key=lambda item: (not item.builtin, item.category, item.name.lower()))


async def list_user_templates(settings: Settings | None = None) -> list[WorkflowTemplate]:
    settings = settings or get_settings()
    templates: list[WorkflowTemplate] = []
    for path in settings.template_dir.glob("*.json"):
        data = await read_json(path, None)
        if data:
            templates.append(validate_template(WorkflowTemplate.model_validate(data)))
    return templates


async def get_template(template_id: str, settings: Settings | None = None) -> WorkflowTemplate:
    for template in builtin_templates():
        if template.id == template_id:
            return template
    path = template_path(template_id, settings)
    data = await read_json(path, None)
    if data is None:
        raise TemplateNotFoundError("Template not found")
    return validate_template(WorkflowTemplate.model_validate(data))


async def create_template(payload: WorkflowTemplateCreate, settings: Settings | None = None) -> WorkflowTemplate:
    template = WorkflowTemplate(**payload.model_dump(), id=new_id("template"), builtin=False)
    template = validate_template(template)
    return await save_template(template, settings)


async def update_template(template_id: str, updates: dict, settings: Settings | None = None) -> WorkflowTemplate:
    template = await get_template(template_id, settings)
    if template.builtin:
        raise BuiltinTemplateError("Built-in templates cannot be updated.")
    data = template.model_dump()
    data.update({key: value for key, value in updates.items() if value is not None})
    data["updated_at"] = datetime.now(timezone.utc)
    return await save_template(validate_template(WorkflowTemplate.model_validate(data)), settings)


async def delete_template(template_id: str, settings: Settings | None = None) -> None:
    template = await get_template(template_id, settings)
    if template.builtin:
        raise BuiltinTemplateError("Built-in templates cannot be deleted.")
    path = template_path(template_id, settings)
    if not path.exists():
        raise TemplateNotFoundError("Template not found")
    path.unlink()


async def create_template_from_project(
    project: Project,
    *,
    name: str,
    description: str,
    category: str,
    tags: list[str],
    include_outputs: bool = False,
    include_settings: bool = True,
    settings: Settings | None = None,
) -> WorkflowTemplate:
    sanitized, _warnings = portable_project.sanitized_project_copy(
        project,
        include_outputs=include_outputs,
        include_settings=include_settings,
        include_run_history=False,
        reset_runtime=True,
        preserve_ids=False,
    )
    template = WorkflowTemplate(
        id=new_id("template"),
        name=name,
        description=description,
        category=category,
        tags=tags,
        builtin=False,
        nodes=sanitized.nodes,
        edges=sanitized.edges,
        settings=sanitized.settings if include_settings else ProjectSettings(),
    )
    return await save_template(validate_template(template), settings)


async def create_project_from_template(
    template: WorkflowTemplate,
    *,
    name: str | None,
    description: str,
    settings: Settings | None = None,
) -> Project:
    project = Project(
        name=name or template.name,
        description=description or template.description,
        nodes=template.nodes,
        edges=template.edges,
        settings=template.settings,
    )
    cloned, _id_map, _warnings = portable_project.clone_project(
        project,
        name=project.name,
        include_outputs=False,
        include_run_history=False,
        preserve_settings=True,
        reset_runtime=True,
    )
    cloned.description = project.description
    return await project_store.save_project(cloned, settings)


async def save_template(template: WorkflowTemplate, settings: Settings | None = None) -> WorkflowTemplate:
    settings = settings or get_settings()
    template.updated_at = datetime.now(timezone.utc)
    await write_json(template_path(template.id, settings), template.model_dump(mode="json"))
    return template


def validate_template(template: WorkflowTemplate) -> WorkflowTemplate:
    if template.builtin is False and not TEMPLATE_ID_RE.fullmatch(template.id):
        raise TemplateStoreError("Invalid template ID.")
    validate_project_settings(template.settings)
    validate_edges_reference_nodes(template.edges, {node.id for node in template.nodes})
    for node in template.nodes:
        if node.model_id:
            model = get_model_for_node(node.type, node.model_id)
            if model is None:
                raise TemplateStoreError(f"Model {node.model_id} is not registered for node type {node.type.value}.")
            if not model.enabled:
                raise TemplateStoreError(
                    model.enabled_reason or f"Model {node.model_id} is disabled for node type {node.type.value}."
                )
        node.output_asset_ids = []
        node.output_urls = []
        node.last_run = {}
        node.status = NodeStatus.idle
        node.error_message = None
    return template


def template_path(template_id: str, settings: Settings | None = None) -> Path:
    if not TEMPLATE_ID_RE.fullmatch(template_id):
        raise TemplateStoreError("Invalid template ID.")
    settings = settings or get_settings()
    return settings.template_dir / f"{template_id}.json"
