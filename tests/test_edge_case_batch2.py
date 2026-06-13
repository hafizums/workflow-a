import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.application.use_cases.run_node as run_node_use_case
import app.routers.assets as assets_router
from app.core.config import Settings
from app.main import app
from app.schemas import Asset, AssetKind, CanvasEdge, CanvasNode, NodeStatus, NodeType, Project, RunJob, WaveSpeedCatalogField
from app.services import local_utility_runner, node_runner, project_store
from app.services.model_input_resolver import ModelInputResolverError, coerce_field_value
from app.services.run_manager import LocalRunManager, RunManagerError
from app.services.wavespeed_adapter import WaveSpeedAdapter
from app.services.workflow_resolver import build_workflow_plan, resolve_inputs_for_node, build_graph


class Batch2ApiEdgeCaseTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.created_project_ids: list[str] = []

    def tearDown(self):
        for project_id in self.created_project_ids:
            self.client.delete(f"/api/projects/{project_id}")

    def test_upload_unknown_type_is_kept_as_other_and_mime_wins_when_mismatched(self):
        unknown = self.client.post(
            "/api/assets/upload",
            files={"file": ("payload.bin", b"hello", "application/octet-stream")},
        )
        self.assertEqual(unknown.status_code, 200, unknown.text)
        self.assertEqual(unknown.json()["kind"], "other")

        mismatched = self.client.post(
            "/api/assets/upload",
            files={"file": ("looks-like-image.png", b"video", "video/mp4")},
        )
        self.assertEqual(mismatched.status_code, 200, mismatched.text)
        self.assertEqual(mismatched.json()["kind"], "image")

    def test_upload_to_cloud_failure_removes_local_file(self):
        before = {path.name for path in assets_router.get_settings().upload_dir.glob("*")}

        class FailingAdapter:
            def __init__(self, _settings):
                pass

            async def upload_file(self, _path):
                raise RuntimeError("cloud upload failed")

        original_adapter = assets_router.WaveSpeedAdapter
        assets_router.WaveSpeedAdapter = FailingAdapter
        try:
            response = self.client.post(
                "/api/assets/upload?upload_to_wavespeed=true",
                files={"file": ("cleanup-test.png", b"not an image", "image/png")},
            )
        finally:
            assets_router.WaveSpeedAdapter = original_adapter

        after = {path.name for path in assets_router.get_settings().upload_dir.glob("*")}
        self.assertEqual(response.status_code, 400)
        self.assertEqual(before, after)

    def test_import_rejects_malformed_json_and_oversized_body(self):
        malformed = self.client.post("/api/projects/import", content="{not json", headers={"content-type": "application/json"})
        self.assertEqual(malformed.status_code, 400)
        self.assertIn("valid JSON", malformed.json()["detail"])

        oversized = self.client.post("/api/projects/import", content=b"{" + b"a" * (2 * 1024 * 1024 + 2), headers={"content-type": "application/json"})
        self.assertEqual(oversized.status_code, 400)
        self.assertIn("size limit", oversized.json()["detail"])

    def test_unknown_template_and_recipe_return_404(self):
        template = self.client.get("/api/templates/template_missing")
        self.assertEqual(template.status_code, 404)
        recipe = self.client.get("/api/recipes/recipe_missing")
        self.assertEqual(recipe.status_code, 404)

    def test_artifact_rating_bounds_return_400(self):
        project = self.client.post("/api/projects", json={"name": "Artifact Rating"}).json()
        self.created_project_ids.append(project["id"])
        project["assets"] = [{"id": "asset_rating", "kind": "image", "filename": "a.png"}]
        save = self.client.put(f"/api/projects/{project['id']}", json=project)
        self.assertEqual(save.status_code, 200, save.text)

        response = self.client.post(f"/api/projects/{project['id']}/artifacts/asset_rating/rating", json={"rating": 6})
        self.assertEqual(response.status_code, 400)
        self.assertIn("between 1 and 5", response.json()["detail"])

    def test_branch_video_to_video_effect_is_rejected_by_api(self):
        project = self.client.post("/api/projects", json={"name": "Branch API"}).json()
        self.created_project_ids.append(project["id"])
        project["assets"] = [{"id": "asset_video", "kind": "video", "filename": "clip.mp4", "public_url": "https://example.com/clip.mp4"}]
        save = self.client.put(f"/api/projects/{project['id']}", json=project)
        self.assertEqual(save.status_code, 200, save.text)

        response = self.client.post(
            f"/api/projects/{project['id']}/artifacts/asset_video/branch",
            json={"target_node_type": "video_effect"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Cannot branch video artifact", response.json()["detail"])

    def test_project_settings_keep_backend_cost_values_in_usd(self):
        project = self.client.post("/api/projects", json={"name": "Cost Settings"}).json()
        self.created_project_ids.append(project["id"])

        response = self.client.put(
            f"/api/projects/{project['id']}/settings",
            json={
                "model_overrides": {},
                "cost_guard": {
                    "enabled": True,
                    "warn_at_usd_per_run": 0.01,
                    "block_at_usd_per_run": 0.02,
                    "max_workflow_run_usd": 0.03,
                    "block_on_unknown_cost": False,
                },
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()["cost_guard"]
        self.assertEqual(saved["warn_at_usd_per_run"], 0.01)
        self.assertEqual(saved["block_at_usd_per_run"], 0.02)
        self.assertEqual(saved["max_workflow_run_usd"], 0.03)


class Batch2RunEdgeCaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        for project_id in getattr(self, "created_project_ids", []):
            try:
                await project_store.delete_project(project_id)
            except project_store.ProjectStoreError:
                pass

    async def test_missing_api_key_error_is_clear_and_has_no_secret(self):
        old_env = os.environ.pop("WAVESPEED_API_KEY", None)
        try:
            adapter = WaveSpeedAdapter(Settings(_env_file=None, wavespeed_api_key=None))
            with self.assertRaisesRegex(RuntimeError, "WAVESPEED_API_KEY is missing"):
                adapter.require_api_key()
        finally:
            if old_env is not None:
                os.environ["WAVESPEED_API_KEY"] = old_env

    async def test_provider_run_exception_is_wrapped_without_secret(self):
        module = types.ModuleType("wavespeed")

        class Client:
            def __init__(self, api_key):
                self.api_key = api_key

            def run(self, _model_id, _inputs, timeout, poll_interval):
                raise RuntimeError(f"provider exploded without leaking {self.api_key}")

        module.Client = Client
        old_module = sys.modules.get("wavespeed")
        sys.modules["wavespeed"] = module
        try:
            adapter = WaveSpeedAdapter(Settings(wavespeed_api_key="secret-token-for-test"))
            with self.assertRaises(RuntimeError) as caught:
                await adapter.run_model("model/test", {"prompt": "x"})
            self.assertIn("WaveSpeed run failed for model/test", str(caught.exception))
            self.assertNotIn("secret-token-for-test", str(caught.exception))
            self.assertIn("[redacted]", str(caught.exception))
        finally:
            if old_module is None:
                sys.modules.pop("wavespeed", None)
            else:
                sys.modules["wavespeed"] = old_module

    async def test_save_to_project_false_does_not_mutate_saved_node_but_true_does(self):
        self.created_project_ids = []
        project = Project(
            id="project_eeeeeeeeeeee",
            name="Run Save Semantics",
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A lamp"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image", model_id="wavespeed-ai/z-image/turbo"),
            ],
            edges=[CanvasEdge(id="edge_prompt", source_node_id="node_prompt", target_node_id="node_image", target_input="prompt")],
        )
        self.created_project_ids.append(project.id)
        await project_store.save_project(project)

        class FakeGateway:
            async def run_model(self, _model_id, _inputs):
                return {"outputs": ["https://example.com/out.png"]}

            async def run_llm_chat(self, _model_id, _inputs):
                return {"text": "ok"}

        original_gateway = run_node_use_case.WaveSpeedGateway
        run_node_use_case.WaveSpeedGateway = lambda _settings: FakeGateway()
        try:
            client = TestClient(app)
            direct = client.post(
                "/api/runs/node",
                json={
                    "project_id": project.id,
                    "node_type": "text_to_image",
                    "model_id": "wavespeed-ai/z-image/turbo",
                    "inputs": {"prompt": "Direct prompt"},
                    "save_to_project": False,
                },
            )
            self.assertEqual(direct.status_code, 200, direct.text)
            saved_after_direct = await project_store.load_project(project.id)
            self.assertEqual(saved_after_direct.nodes[1].status, NodeStatus.idle)

            saved = client.post(
                "/api/runs/node",
                json={"project_id": project.id, "node_id": "node_image", "save_to_project": True},
            )
            self.assertEqual(saved.status_code, 200, saved.text)
            saved_after_true = await project_store.load_project(project.id)
            self.assertEqual(saved_after_true.nodes[1].status, NodeStatus.success)
        finally:
            run_node_use_case.WaveSpeedGateway = original_gateway

    async def test_denylisted_model_returns_api_error_before_provider_call(self):
        old_denylist = dict(node_runner.DENYLISTED_MODEL_IDS)
        node_runner.DENYLISTED_MODEL_IDS["wavespeed-ai/z-image/turbo"] = "blocked in test"
        try:
            response = TestClient(app).post(
                "/api/runs/node",
                json={
                    "node_type": "text_to_image",
                    "model_id": "wavespeed-ai/z-image/turbo",
                    "inputs": {"prompt": "Blocked"},
                    "save_to_project": False,
                },
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("blocked in test", response.json()["detail"])
        finally:
            node_runner.DENYLISTED_MODEL_IDS.clear()
            node_runner.DENYLISTED_MODEL_IDS.update(old_denylist)

    async def test_malformed_provider_output_marks_saved_node_error(self):
        self.created_project_ids = []
        project = Project(
            id="project_abababababab",
            name="Malformed Output",
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A lamp"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image", model_id="wavespeed-ai/z-image/turbo"),
            ],
            edges=[CanvasEdge(id="edge_prompt", source_node_id="node_prompt", target_node_id="node_image", target_input="prompt")],
        )
        self.created_project_ids.append(project.id)
        await project_store.save_project(project)

        class FakeGateway:
            async def run_model(self, _model_id, _inputs):
                return {}

            async def run_llm_chat(self, _model_id, _inputs):
                return {}

        original_gateway = run_node_use_case.WaveSpeedGateway
        run_node_use_case.WaveSpeedGateway = lambda _settings: FakeGateway()
        try:
            response = TestClient(app).post(
                "/api/runs/node",
                json={"project_id": project.id, "node_id": "node_image", "save_to_project": True},
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("did not include output", response.json()["detail"])
            saved_project = await project_store.load_project(project.id)
            saved_node = next(node for node in saved_project.nodes if node.id == "node_image")
            self.assertEqual(saved_node.status, NodeStatus.error)
            self.assertIn("did not include output", saved_node.error_message)
        finally:
            run_node_use_case.WaveSpeedGateway = original_gateway

    async def test_workflow_overlap_blocks_intersecting_active_jobs(self):
        self.created_project_ids = []
        project = Project(
            id="project_ffffffffffff",
            name="Overlap",
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A lamp"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image", model_id="wavespeed-ai/z-image/turbo"),
            ],
            edges=[CanvasEdge(id="edge_prompt", source_node_id="node_prompt", target_node_id="node_image", target_input="prompt")],
        )
        self.created_project_ids.append(project.id)
        await project_store.save_project(project)
        manager = LocalRunManager()
        manager.jobs["job_existing"] = RunJob(project_id=project.id, kind="single_node", node_ids=["node_image"], status="queued")
        with self.assertRaisesRegex(RunManagerError, "active queued or running job"):
            await manager.queue_workflow_run(project.id, "selected", "node_image")

    async def test_in_memory_jobs_do_not_survive_new_manager_instance(self):
        manager = LocalRunManager()
        manager.jobs["job_one"] = RunJob(project_id="project_aaaaaaaaaaaa", kind="single_node", node_ids=["node_a"], status="success")
        self.assertEqual(len(await manager.list_jobs()), 1)
        restarted = LocalRunManager()
        self.assertEqual(await restarted.list_jobs(), [])

    async def test_stitch_video_direct_errors_and_order_validation(self):
        with self.assertRaisesRegex(local_utility_runner.LocalUtilityRunError, "at least two"):
            await local_utility_runner.run_stitch_video(inputs={"videos": ["one"]}, project=Project(), target_node=None)

        project = Project(
            nodes=[
                CanvasNode(id="node_a", type=NodeType.image_to_video, title="A", output_urls=["https://example.com/a.mp4"]),
                CanvasNode(id="node_b", type=NodeType.image_to_video, title="B", output_urls=["https://example.com/b.mp4"]),
                CanvasNode(
                    id="node_stitch",
                    type=NodeType.stitch_video,
                    title="Stitch",
                    inputs={"videos_order": ["edge:edge_a", "edge:missing", "edge:edge_a"]},
                ),
            ],
            edges=[
                CanvasEdge(id="edge_a", source_node_id="node_a", target_node_id="node_stitch", target_input="videos"),
                CanvasEdge(id="edge_b", source_node_id="node_b", target_node_id="node_stitch", target_input="videos"),
            ],
        )
        _resolved, errors = resolve_inputs_for_node(project.nodes[2], build_graph(project), project)
        self.assertTrue(errors)
        self.assertTrue(all(error["code"] == "invalid_list_order" for error in errors))

    async def test_local_utility_output_cleanup_on_stitch_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir)
            first = upload_dir / "first.mp4"
            second = upload_dir / "second.mp4"
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            original_get_settings = local_utility_runner.get_settings
            original_stitch_videos = local_utility_runner.stitch_videos
            local_utility_runner.get_settings = lambda: SimpleNamespace(upload_dir=upload_dir, max_upload_mb=50)

            def fail_stitch(_sources, output, _resolution, _fps):
                Path(output).write_bytes(b"partial")
                raise RuntimeError("ffmpeg missing")

            local_utility_runner.stitch_videos = fail_stitch
            try:
                project = Project(
                    assets=[
                        Asset(id="asset_first", kind=AssetKind.video, filename="first.mp4", local_path=str(first)),
                        Asset(id="asset_second", kind=AssetKind.video, filename="second.mp4", local_path=str(second)),
                    ]
                )
                with self.assertRaisesRegex(local_utility_runner.LocalUtilityRunError, "ffmpeg missing"):
                    await local_utility_runner.run_stitch_video(
                        inputs={"videos": ["asset_first", "asset_second"]},
                        project=project,
                        target_node=None,
                    )
                self.assertFalse(any(path.name.endswith("-stitched.mp4") for path in upload_dir.iterdir()))
            finally:
                local_utility_runner.get_settings = original_get_settings
                local_utility_runner.stitch_videos = original_stitch_videos

    async def test_catalog_asset_list_min_max_and_other_asset_kind_are_rejected(self):
        class FakeAdapter:
            async def upload_file(self, _path):
                return "https://files.example/uploaded.png"

        project = Project(
            assets=[
                Asset(id="asset_one", kind=AssetKind.image, filename="one.png", public_url="https://example.com/one.png"),
                Asset(id="asset_two", kind=AssetKind.image, filename="two.png", public_url="https://example.com/two.png"),
                Asset(id="asset_three", kind=AssetKind.image, filename="three.png", public_url="https://example.com/three.png"),
                Asset(id="asset_other", kind=AssetKind.other, filename="payload.bin", public_url="https://example.com/payload.bin"),
            ]
        )
        field = WaveSpeedCatalogField(
            name="images",
            type="asset_url_list",
            asset_kind=AssetKind.image,
            min_items=2,
            max_items=2,
        )

        with self.assertRaisesRegex(ModelInputResolverError, "at least 2"):
            await coerce_field_value(FakeAdapter(), field, ["asset_one"], project)
        with self.assertRaisesRegex(ModelInputResolverError, "at most 2"):
            await coerce_field_value(FakeAdapter(), field, ["asset_one", "asset_two", "asset_three"], project)
        with self.assertRaisesRegex(ModelInputResolverError, "Expected image asset"):
            await coerce_field_value(FakeAdapter(), field, ["asset_one", "asset_other"], project)

        resolved = await coerce_field_value(FakeAdapter(), field, ["asset_one", "asset_two"], project)
        self.assertEqual(resolved, ["https://example.com/one.png", "https://example.com/two.png"])


if __name__ == "__main__":
    unittest.main()
