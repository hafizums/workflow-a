import unittest

from app.schemas import ArtifactRole, Asset, AssetKind, Project
from app.services.export_package import create_export_package


class V10ExportPackageTests(unittest.TestCase):
    def test_export_package_includes_winner_artifacts_and_lineage(self):
        project = Project(assets=[Asset(id="asset_video", kind=AssetKind.video, filename="clip.mp4", public_url="https://example.com/clip.mp4")])
        asset = project.assets[0]
        asset.view.role = ArtifactRole.winner
        asset.lineage.source_model_id = "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast"
        manifest = create_export_package(project)
        self.assertEqual(manifest.schema_name, "wavespeed_canvas_export_package")
        self.assertEqual(manifest.version, 1)
        self.assertEqual(manifest.artifacts[0].asset_id, "asset_video")
        self.assertEqual(manifest.artifacts[0].source_model_id, "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast")


if __name__ == "__main__":
    unittest.main()
