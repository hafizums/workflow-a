from __future__ import annotations

from copy import deepcopy

from app.schemas import CanvasEdge, CanvasNode, NodeStatus, NodeType, Project, WorkflowRecipe, new_id
from app.services import project_store
from app.services.registry import default_model_for_node_type


class RecipeError(ValueError):
    pass


def recipe_node(node_id: str, node_type: NodeType, title: str, x: float, y: float, inputs: dict | None = None) -> CanvasNode:
    model = default_model_for_node_type(node_type)
    node = CanvasNode(
        id=node_id,
        type=node_type,
        title=title,
        x=x,
        y=y,
        inputs=inputs or {},
        status=NodeStatus.idle,
    )
    if model and not model.enabled:
        node.error_message = model.enabled_reason or "This recipe step is unavailable until its WaveSpeed fields are verified."
    return node


def recipe_edge(edge_id: str, source: str, target: str, target_input: str) -> CanvasEdge:
    return CanvasEdge(
        id=edge_id,
        source_node_id=source,
        target_node_id=target,
        source_handle="output",
        target_handle=target_input,
        source_output="output",
        target_input=target_input,
    )


def builtin_recipes() -> list[WorkflowRecipe]:
    return [
        WorkflowRecipe(
            id="recipe_product_ad_image_video",
            name="Product Ad Image to Video",
            description="Clean up a product image, refine the ad prompt with an LLM, animate the winner, extend the clip, and package deliverables.",
            category="product",
            tags=["product", "image", "video", "llm", "export"],
            required_capabilities=["remove_background", "image_to_image", "image_to_video"],
            optional_capabilities=["llm_text", "upscale_image", "video_extend"],
            nodes=[
                recipe_node("node_asset", NodeType.asset_input, "Product Image", 80, 100, {"asset_id": ""}),
                recipe_node("node_bg", NodeType.remove_background, "Remove Background", 390, 100),
                recipe_node("node_ad_prompt", NodeType.prompt_card, "Ad Prompt", 390, 420, {"text": "Create a clean social product ad image for a premium launch."}),
                recipe_node("node_prompt_refine", NodeType.llm_text, "Refine Ad Prompt", 700, 420),
                recipe_node("node_remix", NodeType.image_to_image, "Ad Image Remix", 700, 100),
                recipe_node("node_compare", NodeType.compare_board, "Compare Stills", 1010, 100),
                recipe_node("node_upscale", NodeType.upscale_image, "Upscale Winner", 1320, 100),
                recipe_node("node_motion_prompt", NodeType.prompt_card, "Motion Prompt", 1320, 420, {"text": "Slow premium product reveal with gentle camera movement."}),
                recipe_node("node_video", NodeType.image_to_video, "Animate Winner", 1630, 100),
                recipe_node("node_extend", NodeType.video_extend, "Extend Clip", 1940, 100, {"duration": 3, "resolution": "720p"}),
                recipe_node("node_export", NodeType.export_package, "Export Package", 2250, 100),
            ],
            edges=[
                recipe_edge("edge_asset_bg", "node_asset", "node_bg", "image"),
                recipe_edge("edge_bg_remix", "node_bg", "node_remix", "image"),
                recipe_edge("edge_ad_prompt_refine", "node_ad_prompt", "node_prompt_refine", "text"),
                recipe_edge("edge_refine_remix", "node_prompt_refine", "node_remix", "prompt"),
                recipe_edge("edge_remix_compare", "node_remix", "node_compare", "input"),
                recipe_edge("edge_compare_upscale", "node_compare", "node_upscale", "image"),
                recipe_edge("edge_motion_video", "node_motion_prompt", "node_video", "prompt"),
                recipe_edge("edge_upscale_video", "node_upscale", "node_video", "image"),
                recipe_edge("edge_video_extend", "node_video", "node_extend", "video"),
                recipe_edge("edge_motion_extend", "node_motion_prompt", "node_extend", "prompt"),
                recipe_edge("edge_extend_export", "node_extend", "node_export", "input"),
            ],
        ),
        WorkflowRecipe(
            id="recipe_ugc_avatar_clip",
            name="UGC Avatar Clip",
            description="Create a voice take, pair it with a portrait, and generate an avatar clip.",
            category="avatar",
            tags=["ugc", "avatar", "voice"],
            required_capabilities=["generate_voice", "talking_avatar"],
            optional_capabilities=["lip_sync"],
            nodes=[
                recipe_node("node_script", NodeType.prompt_card, "Script", 80, 120, {"text": "Here is why this product belongs in your routine."}),
                recipe_node("node_voice", NodeType.generate_voice, "Generate Voice", 390, 120, {"voice_description": "Warm, confident creator voice"}),
                recipe_node("node_portrait", NodeType.asset_input, "Portrait", 390, 420, {"asset_id": ""}),
                recipe_node("node_avatar", NodeType.talking_avatar, "Talking Avatar", 720, 240),
                recipe_node("node_compare", NodeType.compare_board, "Compare Takes", 1030, 240),
                recipe_node("node_export", NodeType.export_package, "Export Package", 1340, 240),
            ],
            edges=[
                recipe_edge("edge_script_voice", "node_script", "node_voice", "text"),
                recipe_edge("edge_script_avatar", "node_script", "node_avatar", "prompt"),
                recipe_edge("edge_portrait_avatar", "node_portrait", "node_avatar", "image"),
                recipe_edge("edge_voice_avatar", "node_voice", "node_avatar", "audio"),
                recipe_edge("edge_avatar_compare", "node_avatar", "node_compare", "input"),
                recipe_edge("edge_compare_export", "node_compare", "node_export", "input"),
            ],
        ),
        WorkflowRecipe(
            id="recipe_storyboard_explorer",
            name="Storyboard Shot Explorer",
            description="Use prompt cards and LLM text to create image options, pick frames, animate, extend, and export.",
            category="storyboard",
            tags=["storyboard", "variants", "video", "llm"],
            required_capabilities=["text_to_image", "image_to_video"],
            optional_capabilities=["llm_text", "video_extend"],
            nodes=[
                recipe_node("node_prompt", NodeType.prompt_card, "Shot Prompt", 80, 120, {"text": "A cinematic establishing shot"}),
                recipe_node("node_prompt_refine", NodeType.llm_text, "Refine Shot Prompt", 390, 120),
                recipe_node("node_image", NodeType.text_to_image, "Image Variants", 700, 120),
                recipe_node("node_compare_image", NodeType.compare_board, "Pick Frame", 1010, 120),
                recipe_node("node_motion_prompt", NodeType.prompt_card, "Motion Prompt", 1010, 420, {"text": "Slow camera move with cinematic depth."}),
                recipe_node("node_video", NodeType.image_to_video, "Video Variants", 1320, 120),
                recipe_node("node_extend", NodeType.video_extend, "Extend Shot", 1630, 120, {"duration": 3, "resolution": "720p"}),
                recipe_node("node_export", NodeType.export_package, "Export Package", 1940, 120),
            ],
            edges=[
                recipe_edge("edge_prompt_refine", "node_prompt", "node_prompt_refine", "text"),
                recipe_edge("edge_refine_image", "node_prompt_refine", "node_image", "prompt"),
                recipe_edge("edge_image_compare", "node_image", "node_compare_image", "input"),
                recipe_edge("edge_compare_video", "node_compare_image", "node_video", "image"),
                recipe_edge("edge_motion_video", "node_motion_prompt", "node_video", "prompt"),
                recipe_edge("edge_video_extend", "node_video", "node_extend", "video"),
                recipe_edge("edge_motion_extend", "node_motion_prompt", "node_extend", "prompt"),
                recipe_edge("edge_extend_export", "node_extend", "node_export", "input"),
            ],
        ),
        WorkflowRecipe(
            id="recipe_reference_video_effects",
            name="Reference Video and Effect",
            description="Generate a reference-guided video and a template video effect from the same image input.",
            category="video",
            tags=["video", "reference", "effect"],
            required_capabilities=["reference_to_video", "video_effect"],
            nodes=[
                recipe_node("node_reference", NodeType.asset_input, "Reference Image", 80, 120, {"asset_id": ""}),
                recipe_node("node_prompt", NodeType.prompt_card, "Video Prompt", 80, 420, {"text": "Turn this reference into a short atmospheric product or character moment."}),
                recipe_node("node_reference_video", NodeType.reference_to_video, "Reference to Video", 390, 120, {"size": "1280*720", "duration": 5, "shot_type": "simple"}),
                recipe_node("node_effect", NodeType.video_effect, "Template Effect", 390, 420, {"template": "tim_burton", "bgm": True}),
                recipe_node("node_compare", NodeType.compare_board, "Compare Videos", 720, 240),
                recipe_node("node_export", NodeType.export_package, "Export Package", 1030, 240),
            ],
            edges=[
                recipe_edge("edge_reference_video_image", "node_reference", "node_reference_video", "reference_image"),
                recipe_edge("edge_prompt_reference_video", "node_prompt", "node_reference_video", "prompt"),
                recipe_edge("edge_reference_effect", "node_reference", "node_effect", "image"),
                recipe_edge("edge_video_compare", "node_reference_video", "node_compare", "input"),
                recipe_edge("edge_effect_compare", "node_effect", "node_compare", "input"),
                recipe_edge("edge_compare_export", "node_compare", "node_export", "input"),
            ],
        ),
        WorkflowRecipe(
            id="recipe_video_voiceover_dubbing",
            name="Video Voiceover / Dubbing",
            description="Pair a video with generated or uploaded audio and produce a synced clip.",
            category="video",
            tags=["video", "voiceover", "lip-sync"],
            required_capabilities=["lip_sync"],
            optional_capabilities=["text_to_audio"],
            nodes=[
                recipe_node("node_video", NodeType.asset_input, "Video Input", 80, 120, {"asset_id": ""}),
                recipe_node("node_script", NodeType.prompt_card, "Voiceover Script", 80, 420, {"text": "Replace this with the voiceover script."}),
                recipe_node("node_tts", NodeType.text_to_audio, "Text to Audio", 390, 420),
                recipe_node("node_sync", NodeType.lip_sync, "Lip Sync", 720, 240),
                recipe_node("node_compare", NodeType.compare_board, "Compare Clips", 1030, 240),
                recipe_node("node_export", NodeType.export_package, "Export Package", 1340, 240),
            ],
            edges=[
                recipe_edge("edge_script_tts", "node_script", "node_tts", "text"),
                recipe_edge("edge_video_sync", "node_video", "node_sync", "video"),
                recipe_edge("edge_tts_sync", "node_tts", "node_sync", "audio"),
                recipe_edge("edge_sync_compare", "node_sync", "node_compare", "input"),
                recipe_edge("edge_compare_export", "node_compare", "node_export", "input"),
            ],
        ),
        WorkflowRecipe(
            id="recipe_audio_transcript_assets",
            name="Audio Transcript to Creative Assets",
            description="Transcribe audio, refine the transcript with an LLM, and repurpose it into image or video prompts.",
            category="audio",
            tags=["audio", "transcript", "creative", "llm"],
            required_capabilities=["speech_to_text", "text_to_image"],
            optional_capabilities=["llm_text", "text_to_video"],
            nodes=[
                recipe_node("node_audio", NodeType.asset_input, "Audio Input", 80, 120, {"asset_id": ""}),
                recipe_node("node_transcript", NodeType.speech_to_text, "Speech to Text", 390, 120),
                recipe_node("node_prompt_refine", NodeType.llm_text, "Refine Transcript Prompt", 700, 120),
                recipe_node("node_image", NodeType.text_to_image, "Creative Image", 1010, 120),
                recipe_node("node_video", NodeType.text_to_video, "Creative Video", 1010, 420),
                recipe_node("node_export", NodeType.export_package, "Export Package", 1340, 240),
            ],
            edges=[
                recipe_edge("edge_audio_transcript", "node_audio", "node_transcript", "audio"),
                recipe_edge("edge_transcript_refine", "node_transcript", "node_prompt_refine", "text"),
                recipe_edge("edge_refine_image", "node_prompt_refine", "node_image", "prompt"),
                recipe_edge("edge_refine_video", "node_prompt_refine", "node_video", "prompt"),
                recipe_edge("edge_image_export", "node_image", "node_export", "input"),
                recipe_edge("edge_video_export", "node_video", "node_export", "input"),
            ],
        ),
        WorkflowRecipe(
            id="recipe_portrait_transfer_pack",
            name="Portrait Transfer Pack",
            description="Combine a face image with a body/reference image and package the portrait-transfer output.",
            category="avatar",
            tags=["avatar", "portrait", "image"],
            required_capabilities=["portrait_transfer"],
            nodes=[
                recipe_node("node_face", NodeType.asset_input, "Face Image", 80, 120, {"asset_id": ""}),
                recipe_node("node_body", NodeType.asset_input, "Body Image", 80, 420, {"asset_id": ""}),
                recipe_node("node_transfer", NodeType.portrait_transfer, "Portrait Transfer", 390, 240),
                recipe_node("node_compare", NodeType.compare_board, "Compare Portraits", 720, 240),
                recipe_node("node_export", NodeType.export_package, "Export Package", 1030, 240),
            ],
            edges=[
                recipe_edge("edge_face_transfer", "node_face", "node_transfer", "image"),
                recipe_edge("edge_body_transfer", "node_body", "node_transfer", "body_image"),
                recipe_edge("edge_transfer_compare", "node_transfer", "node_compare", "input"),
                recipe_edge("edge_compare_export", "node_compare", "node_export", "input"),
            ],
        ),
        WorkflowRecipe(
            id="recipe_multiview_image_to_3d",
            name="Multi-view Image to 3D",
            description="Use front, back, and left view images to generate a 3D asset package.",
            category="3d",
            tags=["3d", "image", "asset"],
            required_capabilities=["image_to_3d"],
            nodes=[
                recipe_node("node_front", NodeType.asset_input, "Front View", 80, 80, {"asset_id": ""}),
                recipe_node("node_back", NodeType.asset_input, "Back View", 80, 320, {"asset_id": ""}),
                recipe_node("node_left", NodeType.asset_input, "Left View", 80, 560, {"asset_id": ""}),
                recipe_node("node_3d", NodeType.image_to_3d, "Image to 3D", 390, 320, {"octree_resolution": 256, "textured_mesh": False}),
                recipe_node("node_compare", NodeType.compare_board, "Compare Assets", 720, 320),
                recipe_node("node_export", NodeType.export_package, "Export Package", 1030, 320),
            ],
            edges=[
                recipe_edge("edge_front_3d", "node_front", "node_3d", "front_image_url"),
                recipe_edge("edge_back_3d", "node_back", "node_3d", "back_image_url"),
                recipe_edge("edge_left_3d", "node_left", "node_3d", "left_image_url"),
                recipe_edge("edge_3d_compare", "node_3d", "node_compare", "input"),
                recipe_edge("edge_compare_export", "node_compare", "node_export", "input"),
            ],
        ),
        WorkflowRecipe(
            id="recipe_3d_asset_ideation",
            name="3D Asset Ideation",
            description="Refine a reusable prompt with an LLM and generate 3D asset candidates.",
            category="3d",
            tags=["3d", "ideation", "llm"],
            required_capabilities=["text_to_3d"],
            optional_capabilities=["llm_text"],
            nodes=[
                recipe_node("node_prompt", NodeType.prompt_card, "Object Prompt", 80, 120, {"text": "A stylized sci-fi crate, game asset ready"}),
                recipe_node("node_prompt_refine", NodeType.llm_text, "Refine Object Prompt", 390, 120),
                recipe_node("node_3d", NodeType.text_to_3d, "Text to 3D", 700, 120),
                recipe_node("node_compare", NodeType.compare_board, "Compare Assets", 1010, 120),
                recipe_node("node_export", NodeType.export_package, "Export Package", 1320, 120),
            ],
            edges=[
                recipe_edge("edge_prompt_refine", "node_prompt", "node_prompt_refine", "text"),
                recipe_edge("edge_refine_3d", "node_prompt_refine", "node_3d", "prompt"),
                recipe_edge("edge_3d_compare", "node_3d", "node_compare", "input"),
                recipe_edge("edge_compare_export", "node_compare", "node_export", "input"),
            ],
        ),
    ]


def list_recipes() -> list[WorkflowRecipe]:
    return builtin_recipes()


def get_recipe(recipe_id: str) -> WorkflowRecipe:
    recipe = next((item for item in builtin_recipes() if item.id == recipe_id), None)
    if recipe is None:
        raise RecipeError("Recipe not found")
    return recipe


def clone_recipe_graph(recipe: WorkflowRecipe) -> tuple[list[CanvasNode], list[CanvasEdge]]:
    nodes = [deepcopy(node) for node in recipe.nodes]
    edges = [deepcopy(edge) for edge in recipe.edges]
    for node in nodes:
        node.output_asset_ids = []
        node.output_urls = []
        node.last_run = {}
        node.status = NodeStatus.idle
    return nodes, edges


async def create_project_from_recipe(recipe_id: str, name: str | None = None, description: str = "") -> Project:
    recipe = get_recipe(recipe_id)
    nodes, edges = clone_recipe_graph(recipe)
    project = Project(name=name or recipe.name, description=description or recipe.description, nodes=nodes, edges=edges)
    return await project_store.save_project(project)


async def apply_recipe_to_project(project: Project, recipe_id: str) -> Project:
    recipe = get_recipe(recipe_id)
    nodes, edges = clone_recipe_graph(recipe)
    existing_ids = {node.id for node in project.nodes}
    id_map: dict[str, str] = {}
    for node in nodes:
        old_id = node.id
        if old_id in existing_ids:
            node.id = f"{old_id}_{len(existing_ids) + len(id_map) + 1}"
        id_map[old_id] = node.id
        project.nodes.append(node)
    for edge in edges:
        edge.id = new_id("edge")
        edge.source_node_id = id_map.get(edge.source_node_id, edge.source_node_id)
        edge.target_node_id = id_map.get(edge.target_node_id, edge.target_node_id)
        project.edges.append(edge)
    return await project_store.save_project(project)
