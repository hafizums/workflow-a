import unittest

from app.schemas import Asset, AssetKind, CanvasNode, NodeType, Project
from app.services.branching import BranchError, create_branch_from_artifact


class V10BranchingTests(unittest.TestCase):
    def test_image_artifact_branches_to_image_to_video(self):
        project = Project(
            nodes=[CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image", x=10, y=20)],
            assets=[Asset(id="asset_image", kind=AssetKind.image, filename="image.png")],
        )
        project.assets[0].lineage.source_node_id = "node_image"
        node, edge = create_branch_from_artifact(project, "asset_image", NodeType.image_to_video, "image")
        self.assertEqual(node.inputs["image"], "asset_image")
        self.assertEqual(edge.source_node_id, "node_image")

    def test_audio_artifact_branches_to_speech_to_text(self):
        project = Project(assets=[Asset(id="asset_audio", kind=AssetKind.audio, filename="voice.mp3")])
        node, _edge = create_branch_from_artifact(project, "asset_audio", NodeType.speech_to_text, "audio")
        self.assertEqual(node.inputs["audio"], "asset_audio")

    def test_text_like_artifact_branches_to_prompt_model(self):
        project = Project(assets=[Asset(id="asset_text", kind=AssetKind.other, filename="transcript.txt")])
        node, _edge = create_branch_from_artifact(project, "asset_text", NodeType.text_to_image, "prompt")
        self.assertEqual(node.inputs["prompt"], "asset_text")

    def test_incompatible_branch_fails_clearly(self):
        project = Project(assets=[Asset(id="asset_audio", kind=AssetKind.audio, filename="voice.mp3")])
        with self.assertRaisesRegex(BranchError, "Cannot branch"):
            create_branch_from_artifact(project, "asset_audio", NodeType.upscale_image, "image")


if __name__ == "__main__":
    unittest.main()
