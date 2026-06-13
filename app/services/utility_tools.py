from __future__ import annotations

from app.schemas import AssetKind, ModelField, ModelSpec, NodeType

UTILITY_NODE_TYPES = {
    NodeType.prompt_card,
    NodeType.style_card,
    NodeType.character_card,
    NodeType.asset_input,
    NodeType.asset_selector,
    NodeType.compare_board,
    NodeType.variant_batch,
    NodeType.reroute,
    NodeType.note,
    NodeType.group_frame,
    NodeType.export_package,
    NodeType.video_last_frame,
    NodeType.stitch_video,
}

RUNNABLE_LOCAL_UTILITY_NODE_TYPES = {
    NodeType.video_last_frame,
    NodeType.stitch_video,
}


def utility_model(
    node_type: NodeType,
    label: str,
    output_kind: AssetKind,
    fields: list[ModelField],
    description: str,
) -> ModelSpec:
    return ModelSpec(
        id=f"local/utility/{node_type.value}",
        label=label,
        node_type=node_type,
        category="utility",
        output_kind=output_kind,
        enabled=True,
        description=description,
        fields=fields,
        default_model_id=None,
        display_name=label,
        estimated_base_cost_usd=0.0,
        cost_unit="local",
        docs_url=None,
        verification_status="local",
        enabled_reason="Local utility node; no AI model call.",
    )


UTILITY_TOOLS: list[ModelSpec] = [
    utility_model(
        NodeType.prompt_card,
        "Prompt Card",
        AssetKind.other,
        [
            ModelField(name="text", type="textarea", required=True, description="Reusable prompt text."),
            ModelField(name="negative_prompt", type="textarea", default="", description="Reusable negative prompt."),
        ],
        "Reusable text prompt block.",
    ),
    utility_model(
        NodeType.style_card,
        "Style Card",
        AssetKind.other,
        [
            ModelField(name="style_name", type="string", default="", description="Style name."),
            ModelField(name="visual_style", type="textarea", default="", description="Visual style rules."),
            ModelField(name="camera", type="string", default="", description="Camera notes."),
            ModelField(name="lighting", type="string", default="", description="Lighting notes."),
            ModelField(name="color_palette", type="string", default="", description="Color palette."),
            ModelField(name="mood", type="string", default="", description="Mood."),
            ModelField(name="quality_rules", type="textarea", default="", description="Quality rules."),
            ModelField(name="negative_rules", type="textarea", default="", description="Negative rules."),
        ],
        "Reusable visual style and quality rules.",
    ),
    utility_model(
        NodeType.character_card,
        "Character / Reference Card",
        AssetKind.other,
        [
            ModelField(name="name", type="string", default="", description="Character or product name."),
            ModelField(name="description", type="textarea", default="", description="Description."),
            ModelField(name="appearance", type="textarea", default="", description="Appearance notes."),
            ModelField(name="voice_description", type="textarea", default="", description="Voice notes."),
            ModelField(name="reference_asset_ids", type="string", default="", description="Comma-separated reference asset IDs."),
            ModelField(name="consistency_notes", type="textarea", default="", description="Consistency notes."),
        ],
        "Reusable character, product, or reference description.",
    ),
    utility_model(
        NodeType.asset_input,
        "Asset Input",
        AssetKind.other,
        [ModelField(name="asset_id", type="string", required=True, description="Project artifact ID.")],
        "Select an existing project artifact as graph input.",
    ),
    utility_model(
        NodeType.asset_selector,
        "Asset Selector",
        AssetKind.other,
        [ModelField(name="selected_asset_id", type="string", default="", description="Chosen upstream artifact ID.")],
        "Select one artifact from upstream outputs.",
    ),
    utility_model(
        NodeType.compare_board,
        "Compare Board",
        AssetKind.other,
        [ModelField(name="title", type="string", default="Compare", description="Board title.")],
        "Collect upstream outputs for side-by-side review.",
    ),
    utility_model(
        NodeType.variant_batch,
        "Variant Batch",
        AssetKind.other,
        [ModelField(name="variant_count", type="integer", default=4, description="Number of variants.")],
        "Local helper describing a variant fan-out.",
    ),
    utility_model(
        NodeType.reroute,
        "Reroute",
        AssetKind.other,
        [],
        "Graph organization node that passes through values.",
    ),
    utility_model(
        NodeType.note,
        "Note",
        AssetKind.other,
        [ModelField(name="text", type="textarea", default="", description="Canvas note.")],
        "Non-executable canvas note.",
    ),
    utility_model(
        NodeType.group_frame,
        "Group Frame",
        AssetKind.other,
        [ModelField(name="title", type="string", default="Group", description="Group label.")],
        "Canvas grouping metadata.",
    ),
    utility_model(
        NodeType.export_package,
        "Export Package",
        AssetKind.other,
        [ModelField(name="label", type="string", default="Final bundle", description="Package label.")],
        "Collect selected deliverables into an export manifest.",
    ),
    utility_model(
        NodeType.video_last_frame,
        "Video Last Frame",
        AssetKind.image,
        [
            ModelField(
                name="video",
                type="asset_url",
                required=True,
                asset_kind=AssetKind.video,
                accept="video/*",
                description="Source video asset or connected upstream video output.",
            ),
            ModelField(
                name="output_format",
                type="select",
                default="png",
                options=["png", "jpg", "jpeg"],
                description="Image format for the extracted final frame.",
            ),
        ],
        "Extract the final frame from a video as an image asset.",
    ),
    utility_model(
        NodeType.stitch_video,
        "Stitch Videos",
        AssetKind.video,
        [
            ModelField(
                name="videos",
                type="asset_url_list",
                required=True,
                asset_kind=AssetKind.video,
                accept="video/*",
                description="Two or more source video assets or connected upstream video outputs, stitched in order.",
            ),
            ModelField(
                name="resolution",
                type="select",
                default="720p",
                options=["720p", "1080p"],
                description="Output video resolution. Clips are scaled and padded to this frame size.",
            ),
            ModelField(
                name="fps",
                type="integer",
                default=24,
                description="Output frame rate for the stitched video.",
            ),
        ],
        "Combine multiple videos into one local MP4 output.",
    ),
]


def get_utility_tool(node_type: NodeType) -> ModelSpec | None:
    return next((tool for tool in UTILITY_TOOLS if tool.node_type == node_type), None)
