import unittest

from app.schemas import ArtifactRole, Asset, AssetKind, CanvasNode, ComparisonSet, ModelSpec, NodeType, Project
from app.services.artifact_service import set_artifact_role
from app.services.tool_compatibility import can_compare_models, compatible_models_for_node


class V10CompareTests(unittest.TestCase):
    def test_compatible_models_can_be_compared_when_fields_match(self):
        source = CanvasNode(type=NodeType.text_to_image, title="Image")
        models = compatible_models_for_node(
            source,
            [
                ModelSpec(id="wavespeed-a", label="A", node_type=NodeType.text_to_image, category="image", output_kind=AssetKind.image),
                ModelSpec(id="wavespeed-b", label="B", node_type=NodeType.text_to_image, category="image", output_kind=AssetKind.image),
            ],
        )
        ok, message = can_compare_models(models)
        self.assertTrue(ok, message)

    def test_incompatible_or_single_model_returns_clear_reason(self):
        ok, message = can_compare_models(
            [ModelSpec(id="wavespeed-a", label="A", node_type=NodeType.text_to_image, category="image", output_kind=AssetKind.image)]
        )
        self.assertFalse(ok)
        self.assertIn("variants", message)

    def test_winner_selection_persists_on_comparison_and_artifact(self):
        project = Project(
            assets=[Asset(id="asset_a", kind=AssetKind.image, filename="a.png")],
            comparison_sets=[ComparisonSet(project_id="project", source_node_id="node", artifact_ids=["asset_a"])],
        )
        project.comparison_sets[0].winner_asset_id = "asset_a"
        set_artifact_role(project, "asset_a", ArtifactRole.winner)
        self.assertEqual(project.comparison_sets[0].winner_asset_id, "asset_a")
        self.assertEqual(project.assets[0].view.role, ArtifactRole.winner)


if __name__ == "__main__":
    unittest.main()
