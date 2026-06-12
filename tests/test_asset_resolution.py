import tempfile
import unittest
from pathlib import Path

from app.schemas import Asset, AssetKind, Project
from app.services.node_runner import (
    NodeRunError,
    resolve_asset_input,
    resolve_asset_kind_from_url,
    resolve_audio_input,
    resolve_video_input,
)


class FakeAdapter:
    def __init__(self):
        self.uploaded_paths = []

    async def upload_file(self, path):
        self.uploaded_paths.append(Path(path))
        return f"https://wavespeed.example/uploads/{Path(path).name}"


class AssetResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_asset_upload_sets_wavespeed_url_for_reuse(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3") as file:
            project = Project(
                id="project_notvalid",
                assets=[Asset(id="asset_audio", kind=AssetKind.audio, filename="voice.mp3", local_path=file.name)],
            )
            adapter = FakeAdapter()
            resolved = await resolve_audio_input(adapter, {"audio": "asset_audio"}, project)
            self.assertEqual(resolved, f"https://wavespeed.example/uploads/{Path(file.name).name}")
            self.assertEqual(project.assets[0].wavespeed_url, resolved)
            self.assertEqual(len(adapter.uploaded_paths), 1)

    async def test_kind_mismatch_has_clear_error(self):
        project = Project(
            assets=[Asset(id="asset_image", kind=AssetKind.image, filename="still.png", public_url="https://example.com/still.png")]
        )
        with self.assertRaisesRegex(NodeRunError, "Expected audio asset for audio, got image"):
            await resolve_audio_input(FakeAdapter(), {"audio": "asset_image"}, project)

    async def test_localhost_urls_are_rejected(self):
        with self.assertRaisesRegex(NodeRunError, "Localhost video URLs are not reachable"):
            await resolve_video_input(FakeAdapter(), {"video": "http://localhost:8000/uploads/a.mp4"}, None)

    async def test_direct_public_urls_are_allowed_and_kind_checked(self):
        resolved = await resolve_asset_input(
            FakeAdapter(),
            {"audio": "https://cdn.example.com/speech.flac"},
            None,
            "audio",
            {AssetKind.audio},
        )
        self.assertEqual(resolved, "https://cdn.example.com/speech.flac")
        with self.assertRaisesRegex(NodeRunError, "Expected audio asset for audio, got video"):
            await resolve_audio_input(FakeAdapter(), {"audio": "https://cdn.example.com/movie.mp4"}, None)

    def test_asset_kind_suffix_detection(self):
        self.assertEqual(resolve_asset_kind_from_url("https://example.com/a.PNG?x=1"), AssetKind.image)
        self.assertEqual(resolve_asset_kind_from_url("https://example.com/a.webm"), AssetKind.video)
        self.assertEqual(resolve_asset_kind_from_url("https://example.com/a.flac"), AssetKind.audio)
        self.assertEqual(resolve_asset_kind_from_url("https://example.com/a.glb"), AssetKind.other)


if __name__ == "__main__":
    unittest.main()
