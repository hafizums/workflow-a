import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.schemas import Asset, AssetKind, CanvasEdge, CanvasNode, NodeType, Project
from app.services import local_utility_runner, project_store
from app.services.artifact_service import artifact_lineage_tree
from app.services.branching import BranchError, create_branch_from_artifact
from app.services.input_safety import is_url_private_or_local
from app.services.recipe_store import apply_recipe_to_project
from app.services.run_manager import LocalRunManager
from app.services.workflow_resolver import build_workflow_plan


class Batch1EdgeCaseTests(unittest.IsolatedAsyncioTestCase):
    def test_private_url_detection_covers_rfc1918_link_local_and_ipv6(self):
        self.assertTrue(is_url_private_or_local("http://172.20.0.1/video.mp4"))
        self.assertTrue(is_url_private_or_local("http://169.254.169.254/latest/meta-data"))
        self.assertTrue(is_url_private_or_local("http://[fd00::1]/video.mp4"))
        self.assertTrue(is_url_private_or_local("http://localhost:8000/uploads/a.mp4"))
        self.assertFalse(is_url_private_or_local("https://example.com/video.mp4"))

    def test_upload_path_traversal_is_rejected_for_local_utilities(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(local_utility_runner.LocalUtilityRunError, "escapes the upload directory"):
                local_utility_runner.local_upload_path("/uploads/../../secret.mp4", Path(temp_dir))

    async def test_corrupt_project_file_is_skipped_on_list_and_clear_on_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = SimpleNamespace(project_dir=Path(temp_dir))
            good = Project(id="project_aaaaaaaaaaaa", name="Good")
            bad_path = Path(temp_dir) / "project_bbbbbbbbbbbb.json"
            await project_store.save_project(good, settings)
            bad_path.write_text("{not json", encoding="utf-8")

            projects = await project_store.list_projects(settings)
            self.assertEqual([project.id for project in projects], ["project_aaaaaaaaaaaa"])
            with self.assertRaisesRegex(project_store.ProjectStorageSchemaError, "invalid JSON or schema"):
                await project_store.load_project("project_bbbbbbbbbbbb", settings)

    def test_incompatible_media_edge_is_reported_during_planning(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image", output_urls=["https://example.com/a.png"]),
                CanvasNode(id="node_audio", type=NodeType.speech_to_text, title="Transcribe"),
            ],
            edges=[CanvasEdge(id="edge_bad", source_node_id="node_image", target_node_id="node_audio", target_input="audio")],
        )
        plan = build_workflow_plan(project)
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["errors"][0]["code"], "incompatible_edge_media")

    def test_direct_negative_prompt_on_model_requires_prompt_source(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "Move slowly"}),
                CanvasNode(
                    id="node_video",
                    type=NodeType.text_to_video,
                    title="Video",
                    inputs={"negative_prompt": "blur"},
                ),
            ],
            edges=[CanvasEdge(id="edge_prompt", source_node_id="node_prompt", target_node_id="node_video", target_input="prompt")],
        )
        plan = build_workflow_plan(project)
        self.assertFalse(plan["ok"])
        self.assertTrue(any(error["details"].get("input") == "negative_prompt" for error in plan["errors"]))

    def test_artifact_lineage_cycle_is_marked_not_recursive(self):
        project = Project(
            assets=[
                Asset(id="asset_a", kind=AssetKind.image, filename="a.png", public_url="https://example.com/a.png"),
                Asset(id="asset_b", kind=AssetKind.image, filename="b.png", public_url="https://example.com/b.png"),
            ]
        )
        project.assets[0].lineage.source_artifact_ids = ["asset_b"]
        project.assets[1].lineage.source_artifact_ids = ["asset_a"]
        tree = artifact_lineage_tree(project, "asset_a")
        self.assertTrue(tree["upstream_assets"][0]["upstream_assets"][0]["cycle_detected"])

    def test_video_effect_branching_matches_image_based_runner(self):
        project = Project(
            assets=[
                Asset(id="asset_image", kind=AssetKind.image, filename="a.png", public_url="https://example.com/a.png"),
                Asset(id="asset_video", kind=AssetKind.video, filename="a.mp4", public_url="https://example.com/a.mp4"),
            ]
        )
        image_node, _edge = create_branch_from_artifact(project, "asset_image", NodeType.video_effect)
        self.assertEqual(image_node.inputs["image"], "asset_image")
        with self.assertRaisesRegex(BranchError, "Cannot branch video artifact"):
            create_branch_from_artifact(project, "asset_video", NodeType.video_effect)

    async def test_applying_recipe_twice_keeps_edge_ids_unique(self):
        project = Project(id="project_cccccccccccc", name="Recipe Target")
        try:
            project = await apply_recipe_to_project(project, "recipe_storyboard_explorer")
            project = await apply_recipe_to_project(project, "recipe_storyboard_explorer")
            edge_ids = [edge.id for edge in project.edges]
            self.assertEqual(len(edge_ids), len(set(edge_ids)))
        finally:
            await maybe_delete_project(project.id)

    async def test_runnable_local_utility_can_be_queued(self):
        project = Project(
            id="project_dddddddddddd",
            name="Utility Queue",
            nodes=[CanvasNode(id="node_frame", type=NodeType.video_last_frame, title="Last Frame", inputs={"video": "asset_video"})],
            assets=[Asset(id="asset_video", kind=AssetKind.video, filename="clip.mp4", public_url="https://example.com/clip.mp4")],
        )
        manager = LocalRunManager()
        try:
            await project_store.save_project(project)
            job = await manager.queue_node_run(project.id, "node_frame")
            self.assertEqual(job.node_ids, ["node_frame"])
            self.assertEqual(job.request["model_id"], "local/utility/video_last_frame")
        finally:
            await maybe_delete_project(project.id)


async def maybe_delete_project(project_id: str) -> None:
    try:
        await project_store.delete_project(project_id)
    except project_store.ProjectStoreError:
        pass


if __name__ == "__main__":
    unittest.main()
