from __future__ import annotations

from app.schemas import AssetKind, CanvasEdge, CanvasNode, NodeType, Project, new_id, utc_now
from app.services.artifact_service import get_artifact
from app.services.registry import default_model_for_node_type


class BranchError(ValueError):
    pass


COMPATIBLE_TARGETS: dict[AssetKind, dict[NodeType, list[str]]] = {
    AssetKind.image: {
        NodeType.image_to_image: ["image"],
        NodeType.reference_to_image: ["reference_image"],
        NodeType.upscale_image: ["image"],
        NodeType.remove_background: ["image"],
        NodeType.remove_object: ["image", "mask_image"],
        NodeType.image_to_video: ["image", "last_image"],
        NodeType.start_end_to_video: ["image", "last_image"],
        NodeType.talking_avatar: ["image", "mask_image"],
    },
    AssetKind.video: {
        NodeType.lip_sync: ["video"],
        NodeType.video_extend: ["video"],
        NodeType.video_effect: ["video"],
    },
    AssetKind.audio: {
        NodeType.speech_to_text: ["audio"],
        NodeType.lip_sync: ["audio"],
        NodeType.talking_avatar: ["audio"],
    },
    AssetKind.other: {
        NodeType.text_to_image: ["prompt"],
        NodeType.text_to_video: ["prompt"],
        NodeType.text_to_speech: ["text"],
        NodeType.text_to_3d: ["prompt"],
    },
}


def create_branch_from_artifact(
    project: Project,
    artifact_id: str,
    target_node_type: NodeType,
    target_input_name: str | None = None,
    title: str | None = None,
) -> tuple[CanvasNode, CanvasEdge]:
    artifact = get_artifact(project, artifact_id)
    compatible_inputs = COMPATIBLE_TARGETS.get(artifact.kind, {}).get(target_node_type, [])
    if not compatible_inputs:
        raise BranchError(f"Cannot branch {artifact.kind.value} artifact to {target_node_type.value}.")

    if target_input_name:
        if target_input_name not in compatible_inputs:
            raise BranchError(f"Input {target_input_name} is not compatible with {artifact.kind.value} artifacts.")
        input_name = target_input_name
    elif len(compatible_inputs) == 1:
        input_name = compatible_inputs[0]
    else:
        input_name = compatible_inputs[0]

    model = default_model_for_node_type(target_node_type)
    if model and not model.enabled:
        raise BranchError(model.enabled_reason or f"Target node type {target_node_type.value} is disabled.")

    source_node = next((node for node in project.nodes if node.id == artifact.lineage.source_node_id), None)
    x = (source_node.x + 340) if source_node else 160
    y = (source_node.y + 40) if source_node else 160
    node = CanvasNode(
        type=target_node_type,
        title=title or f"{target_node_type.value.replace('_', ' ').title()} Branch",
        model_id=None,
        x=x,
        y=y,
        inputs={input_name: artifact.id},
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    edge = CanvasEdge(
        id=new_id("edge"),
        source_node_id=source_node.id if source_node else "",
        target_node_id=node.id,
        source_handle="output",
        target_handle=input_name,
        source_output="output",
        target_input=input_name,
    )
    node.last_run = {
        "branched_from_artifact_id": artifact.id,
        "source_model_id": artifact.lineage.source_model_id,
    }
    project.nodes.append(node)
    if edge.source_node_id:
        project.edges.append(edge)
    return node, edge
