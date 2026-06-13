import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from app.schemas import Asset, AssetKind, CanvasEdge, CanvasNode, NodeType, Project
from app.services import local_utility_runner
from app.services.utility_tools import RUNNABLE_LOCAL_UTILITY_NODE_TYPES, get_utility_tool
from app.services.workflow_resolver import build_execution_plan, build_graph, build_workflow_plan, resolve_inputs_for_node, resolve_source_output


class V10UtilityNodeTests(unittest.TestCase):
    def test_prompt_card_resolves_into_model_prompt(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A bright product photo"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[CanvasEdge(source_node_id="node_prompt", target_node_id="node_image", target_input="prompt")],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        image_step = next(step for step in plan["steps"] if step["node_id"] == "node_image")
        self.assertEqual(image_step["resolved_inputs"]["prompt"], "A bright product photo")
        self.assertEqual([step["node_id"] for step in plan["steps"]], ["node_image"])

    def test_prompt_card_generic_input_edge_defaults_to_prompt(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A bright product photo"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[CanvasEdge(source_node_id="node_prompt", target_node_id="node_image", target_input="input")],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        image_step = next(step for step in plan["steps"] if step["node_id"] == "node_image")
        self.assertEqual(image_step["resolved_inputs"]["prompt"], "A bright product photo")

    def test_llm_text_output_can_feed_model_prompt(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "Improve this"}),
                CanvasNode(
                    id="node_llm",
                    type=NodeType.llm_text,
                    title="LLM",
                    last_run={"text_output": "A refined product prompt"},
                ),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[
                CanvasEdge(source_node_id="node_prompt", target_node_id="node_llm", target_input="text"),
                CanvasEdge(source_node_id="node_llm", target_node_id="node_image", target_input="prompt"),
            ],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        image_step = next(step for step in plan["steps"] if step["node_id"] == "node_image")
        self.assertTrue(plan["ok"])
        self.assertEqual(image_step["resolved_inputs"]["prompt"], "A refined product prompt")

    def test_unrun_llm_prompt_source_must_run_first(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "Improve this"}),
                CanvasNode(id="node_llm", type=NodeType.llm_text, title="LLM"),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[
                CanvasEdge(source_node_id="node_prompt", target_node_id="node_llm", target_input="text"),
                CanvasEdge(source_node_id="node_llm", target_node_id="node_image", target_input="prompt"),
            ],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["errors"][0]["code"], "missing_upstream_output")

    def test_asset_input_resolves_selected_asset_id(self):
        project = Project(
            assets=[Asset(id="asset_image", kind=AssetKind.image, filename="image.png")],
            nodes=[CanvasNode(id="node_asset", type=NodeType.asset_input, title="Asset", inputs={"asset_id": "asset_image"})],
        )
        self.assertEqual(resolve_source_output(project.nodes[0], project), "asset_image")

    def test_compare_board_collects_selection_without_model_resolution_error(self):
        project = Project(
            assets=[Asset(id="asset_a", kind=AssetKind.image, filename="a.png")],
            nodes=[CanvasNode(id="node_compare", type=NodeType.compare_board, title="Compare", inputs={"selected_asset_id": "asset_a"})],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        self.assertTrue(plan["ok"])
        self.assertEqual(plan["node_ids"], [])
        self.assertEqual(resolve_source_output(project.nodes[0], project), "asset_a")

    def test_execution_plan_excludes_prompt_card_but_keeps_downstream_model(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A bright product photo"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[CanvasEdge(source_node_id="node_prompt", target_node_id="node_image", target_input="prompt")],
        )
        _graph, selected_ids, warnings, errors = build_execution_plan(project, mode="from_node", node_id="node_prompt")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(selected_ids, ["node_image"])

    def test_multiple_upstream_assets_collect_into_generic_image_list_input(self):
        project = Project(
            assets=[
                Asset(id="asset_a", kind=AssetKind.image, filename="a.png", public_url="https://example.com/a.png"),
                Asset(id="asset_b", kind=AssetKind.image, filename="b.png", public_url="https://example.com/b.png"),
            ],
            nodes=[
                CanvasNode(id="node_a", type=NodeType.asset_input, title="A", inputs={"asset_id": "asset_a"}),
                CanvasNode(id="node_b", type=NodeType.asset_input, title="B", inputs={"asset_id": "asset_b"}),
                CanvasNode(
                    id="node_edit",
                    type=NodeType.generic_wavespeed,
                    title="Edit",
                    model_id="alibaba/wan-2.7/image-edit",
                    inputs={"prompt": "combine"},
                ),
            ],
            edges=[
                CanvasEdge(source_node_id="node_a", target_node_id="node_edit", target_input="images"),
                CanvasEdge(source_node_id="node_b", target_node_id="node_edit", target_input="images"),
            ],
        )
        resolved, errors = resolve_inputs_for_node(project.nodes[2], build_graph(project), project)
        self.assertEqual(errors, [])
        self.assertEqual(resolved["images"], ["asset_a", "asset_b"])

    def test_video_last_frame_utility_is_cataloged_as_runnable(self):
        tool = get_utility_tool(NodeType.video_last_frame)
        self.assertIsNotNone(tool)
        self.assertIn(NodeType.video_last_frame, RUNNABLE_LOCAL_UTILITY_NODE_TYPES)
        self.assertEqual(tool.output_kind, AssetKind.image)
        self.assertEqual(tool.fields[0].name, "video")
        self.assertEqual(tool.fields[0].asset_kind, AssetKind.video)

    def test_stitch_video_utility_is_cataloged_as_runnable(self):
        tool = get_utility_tool(NodeType.stitch_video)
        self.assertIsNotNone(tool)
        self.assertIn(NodeType.stitch_video, RUNNABLE_LOCAL_UTILITY_NODE_TYPES)
        self.assertEqual(tool.output_kind, AssetKind.video)
        self.assertEqual(tool.fields[0].name, "videos")
        self.assertEqual(tool.fields[0].type, "asset_url_list")
        self.assertEqual(tool.fields[0].asset_kind, AssetKind.video)

    def test_stitch_video_collects_multiple_connected_video_outputs(self):
        project = Project(
            assets=[
                Asset(id="asset_video_a", kind=AssetKind.video, filename="a.mp4", public_url="https://example.com/a.mp4"),
                Asset(id="asset_video_b", kind=AssetKind.video, filename="b.mp4", public_url="https://example.com/b.mp4"),
            ],
            nodes=[
                CanvasNode(
                    id="node_video_a",
                    type=NodeType.image_to_video,
                    title="Video A",
                    output_asset_ids=["asset_video_a"],
                    output_urls=["https://example.com/a.mp4"],
                ),
                CanvasNode(
                    id="node_video_b",
                    type=NodeType.image_to_video,
                    title="Video B",
                    output_asset_ids=["asset_video_b"],
                    output_urls=["https://example.com/b.mp4"],
                ),
                CanvasNode(id="node_stitch", type=NodeType.stitch_video, title="Stitch"),
            ],
            edges=[
                CanvasEdge(source_node_id="node_video_a", target_node_id="node_stitch", target_input="videos"),
                CanvasEdge(source_node_id="node_video_b", target_node_id="node_stitch", target_input="videos"),
            ],
        )
        resolved, errors = resolve_inputs_for_node(project.nodes[2], build_graph(project), project)
        self.assertEqual(errors, [])
        self.assertEqual(resolved["videos"], ["https://example.com/a.mp4", "https://example.com/b.mp4"])

    def test_stitch_video_honors_explicit_visible_order(self):
        project = Project(
            assets=[
                Asset(id="asset_video_a", kind=AssetKind.video, filename="a.mp4", public_url="https://example.com/a.mp4"),
                Asset(id="asset_video_b", kind=AssetKind.video, filename="b.mp4", public_url="https://example.com/b.mp4"),
            ],
            nodes=[
                CanvasNode(id="node_video_a", type=NodeType.image_to_video, title="Video A", output_asset_ids=["asset_video_a"]),
                CanvasNode(id="node_video_b", type=NodeType.image_to_video, title="Video B", output_asset_ids=["asset_video_b"]),
                CanvasNode(
                    id="node_stitch",
                    type=NodeType.stitch_video,
                    title="Stitch",
                    inputs={"videos_order": ["edge:edge_b", "edge:edge_a"]},
                ),
            ],
            edges=[
                CanvasEdge(id="edge_a", source_node_id="node_video_a", target_node_id="node_stitch", target_input="videos"),
                CanvasEdge(id="edge_b", source_node_id="node_video_b", target_node_id="node_stitch", target_input="videos"),
            ],
        )
        resolved, errors = resolve_inputs_for_node(project.nodes[2], build_graph(project), project)
        self.assertEqual(errors, [])
        self.assertEqual(resolved["videos"], ["https://example.com/b.mp4", "https://example.com/a.mp4"])

    def test_video_last_frame_runner_creates_image_asset_from_project_video(self):
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            source_path = upload_dir / "clip.mp4"
            source_path.write_bytes(b"fake video for patched extractor")
            original_get_settings = local_utility_runner.get_settings
            original_extract_last_frame = local_utility_runner.extract_last_frame
            local_utility_runner.get_settings = lambda: SimpleNamespace(upload_dir=upload_dir, max_upload_mb=50)
            local_utility_runner.extract_last_frame = lambda _source, output: Path(output).write_bytes(b"frame")
            try:
                project = Project(
                    assets=[
                        Asset(
                            id="asset_video",
                            kind=AssetKind.video,
                            filename="clip.mp4",
                            local_path=str(source_path),
                        )
                    ],
                    nodes=[CanvasNode(id="node_frame", type=NodeType.video_last_frame, title="Frame")],
                )
                raw_output, output_urls, output_assets = asyncio.run(
                    local_utility_runner.run_video_last_frame(
                        inputs={"video": "asset_video", "output_format": "png"},
                        project=project,
                        target_node=project.nodes[0],
                    )
                )
            finally:
                local_utility_runner.get_settings = original_get_settings
                local_utility_runner.extract_last_frame = original_extract_last_frame

            self.assertEqual(raw_output["utility"], NodeType.video_last_frame.value)
            self.assertEqual(len(output_urls), 1)
            self.assertEqual(output_assets[0].kind, AssetKind.image)
            self.assertEqual(output_assets[0].lineage.source_artifact_ids, ["asset_video"])
            self.assertTrue(Path(output_assets[0].local_path).exists())

    def test_stitch_video_runner_creates_video_asset_from_project_videos(self):
        with TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            first_path = upload_dir / "first.mp4"
            second_path = upload_dir / "second.mp4"
            first_path.write_bytes(b"first")
            second_path.write_bytes(b"second")
            original_get_settings = local_utility_runner.get_settings
            original_stitch_videos = local_utility_runner.stitch_videos
            local_utility_runner.get_settings = lambda: SimpleNamespace(upload_dir=upload_dir, max_upload_mb=50)
            local_utility_runner.stitch_videos = lambda _sources, output, _resolution, _fps: Path(output).write_bytes(b"stitched")
            try:
                project = Project(
                    assets=[
                        Asset(id="asset_first", kind=AssetKind.video, filename="first.mp4", local_path=str(first_path)),
                        Asset(id="asset_second", kind=AssetKind.video, filename="second.mp4", local_path=str(second_path)),
                    ],
                    nodes=[CanvasNode(id="node_stitch", type=NodeType.stitch_video, title="Stitch")],
                )
                raw_output, output_urls, output_assets = asyncio.run(
                    local_utility_runner.run_stitch_video(
                        inputs={"videos": ["asset_first", "asset_second"], "resolution": "720p", "fps": 24},
                        project=project,
                        target_node=project.nodes[0],
                    )
                )
            finally:
                local_utility_runner.get_settings = original_get_settings
                local_utility_runner.stitch_videos = original_stitch_videos

            self.assertEqual(raw_output["utility"], NodeType.stitch_video.value)
            self.assertEqual(len(output_urls), 1)
            self.assertEqual(output_assets[0].kind, AssetKind.video)
            self.assertEqual(output_assets[0].content_type, "video/mp4")
            self.assertEqual(output_assets[0].lineage.source_artifact_ids, ["asset_first", "asset_second"])
            self.assertTrue(Path(output_assets[0].local_path).exists())


if __name__ == "__main__":
    unittest.main()
