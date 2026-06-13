from __future__ import annotations

from app.schemas import Asset, CanvasEdge, CanvasNode, NodeStatus, NodeType, Project, new_id, utc_now


AUTO_STORYBOARD_PANEL_MARKER = "storyboard_panels"


def sync_storyboard_panel_output_nodes(
    project: Project,
    source_node: CanvasNode,
    panel_assets: list[Asset],
) -> list[str]:
    """Replace auto-created storyboard panel output nodes for a detector node."""

    old_node_ids = {
        node.id
        for node in project.nodes
        if node.type == NodeType.asset_input
        and node.inputs.get("auto_created_by") == AUTO_STORYBOARD_PANEL_MARKER
        and node.inputs.get("source_node_id") == source_node.id
    }
    if old_node_ids:
        project.nodes = [node for node in project.nodes if node.id not in old_node_ids]
        project.edges = [
            edge
            for edge in project.edges
            if edge.source_node_id not in old_node_ids and edge.target_node_id not in old_node_ids
        ]

    created_node_ids: list[str] = []
    base_x = source_node.x + 420
    base_y = source_node.y
    for index, asset in enumerate(panel_assets, start=1):
        output_url = asset.public_url or asset.wavespeed_url or asset.local_path or ""
        node = CanvasNode(
            id=new_id("node"),
            type=NodeType.asset_input,
            title=f"Panel {index:02d}",
            x=base_x,
            y=base_y + ((index - 1) * 180),
            inputs={
                "asset_id": asset.id,
                "auto_created_by": AUTO_STORYBOARD_PANEL_MARKER,
                "source_node_id": source_node.id,
                "source_asset_id": asset.id,
                "panel_index": index,
            },
            output_asset_ids=[asset.id],
            output_urls=[output_url] if output_url else [],
            status=NodeStatus.success,
            last_run={
                "ok": True,
                "model_id": None,
                "completed_at": utc_now().isoformat(),
                "output_urls": [output_url] if output_url else [],
                "asset_ids": [asset.id],
                "raw_output": {
                    "utility": "storyboard_panel_output",
                    "source_node_id": source_node.id,
                    "asset_id": asset.id,
                    "panel_index": index,
                },
            },
        )
        project.nodes.append(node)
        project.edges.append(
            CanvasEdge(
                id=new_id("edge"),
                source_node_id=source_node.id,
                target_node_id=node.id,
                source_handle="output",
                target_handle="asset_id",
                source_output="output",
                target_input="asset_id",
            )
        )
        created_node_ids.append(node.id)

    return created_node_ids
