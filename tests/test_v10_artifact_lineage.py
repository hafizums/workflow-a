import unittest

from app.schemas import ArtifactRole, Asset, AssetKind, CanvasNode, NodeType, Project
from app.services.artifact_service import artifact_lineage_tree, pin_artifact, rate_artifact, reject_artifact, set_artifact_role


class V10ArtifactLineageTests(unittest.TestCase):
    def test_generated_artifact_metadata_and_view_state_persist_on_project_model(self):
        project = Project(
            id="project_cccccccccccc",
            nodes=[CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image")],
            assets=[
                Asset(
                    id="asset_output",
                    kind=AssetKind.image,
                    filename="output.png",
                    public_url="https://example.com/output.png",
                )
            ],
        )
        asset = project.assets[0]
        asset.lineage.source_project_id = project.id
        asset.lineage.source_node_id = "node_image"
        asset.lineage.source_run_id = "run_123"
        asset.lineage.source_job_id = "job_123"
        asset.lineage.source_model_id = "wavespeed-ai/z-image/turbo"

        pin_artifact(project, "asset_output")
        rate_artifact(project, "asset_output", 5)
        set_artifact_role(project, "asset_output", ArtifactRole.winner)
        reject_artifact(project, "asset_output", False)

        reloaded = Project.model_validate(project.model_dump(mode="json"))
        reloaded_asset = reloaded.assets[0]
        self.assertEqual(reloaded_asset.lineage.source_node_id, "node_image")
        self.assertEqual(reloaded_asset.lineage.source_model_id, "wavespeed-ai/z-image/turbo")
        self.assertTrue(reloaded_asset.view.pinned)
        self.assertEqual(reloaded_asset.view.rating, 5)
        self.assertEqual(reloaded_asset.view.role, ArtifactRole.winner)

    def test_lineage_tree_returns_upstream_assets_and_node(self):
        project = Project(
            nodes=[CanvasNode(id="node_remix", type=NodeType.image_to_image, title="Remix")],
            assets=[
                Asset(id="asset_input", kind=AssetKind.image, filename="input.png"),
                Asset(id="asset_output", kind=AssetKind.image, filename="output.png"),
            ],
        )
        project.assets[1].lineage.source_node_id = "node_remix"
        project.assets[1].lineage.source_artifact_ids = ["asset_input"]

        tree = artifact_lineage_tree(project, "asset_output")
        self.assertEqual(tree["source_node_id"], "node_remix")
        self.assertEqual(tree["upstream_assets"][0]["asset_id"], "asset_input")


if __name__ == "__main__":
    unittest.main()
