import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import CanvasEdge, CanvasNode, NodeType, Project
from app.services.model_catalog import CHEAPEST_MODEL_BY_NODE_TYPE, list_catalog_entries
from app.services.node_runner import NodeRunError, prepare_inputs
from app.services.registry import MODELS
from app.services.workflow_resolver import build_workflow_plan


class FakeAdapter:
    async def upload_file(self, path):
        return f"https://wavespeed.example/{path.name}"


class ModelCatalogTests(unittest.TestCase):
    def test_cheapest_mapping_contains_all_planned_node_types(self):
        expected_node_types = {
            "text_to_image",
            "image_to_image",
            "reference_to_image",
            "upscale_image",
            "remove_background",
            "remove_object",
            "image_to_video",
            "start_end_to_video",
            "text_to_video",
            "reference_to_video",
            "video_extend",
            "video_effect",
            "text_to_speech",
            "text_to_audio",
            "speech_to_text",
            "generate_voice",
            "talking_avatar",
            "lip_sync",
            "portrait_transfer",
            "image_to_3d",
            "text_to_3d",
            "llm_text",
            "llm_vision",
        }
        self.assertEqual(expected_node_types, set(CHEAPEST_MODEL_BY_NODE_TYPE))

    def test_catalog_entries_include_required_metadata(self):
        allowed_statuses = {"verified", "candidate", "needs_params", "disabled", "experimental"}
        for entry in list_catalog_entries():
            with self.subTest(node_type=entry.node_type):
                self.assertTrue(entry.node_type)
                self.assertTrue(entry.category)
                self.assertTrue(entry.output_kind)
                self.assertIn(entry.verification_status, allowed_statuses)
                self.assertIsInstance(entry.enabled, bool)

    def test_enabled_models_do_not_use_placeholder_ids(self):
        for model in [item for item in MODELS if item.enabled]:
            with self.subTest(model_id=model.id):
                self.assertFalse(model.id.startswith(("planned/", "TODO_")))
                if model.node_type == NodeType.upload_image:
                    continue
                self.assertIsNotNone(model.default_model_id)
                self.assertFalse(model.default_model_id.startswith("TODO_"))

    def test_existing_image_registry_entries_still_exist(self):
        model_ids = {model.id for model in MODELS}
        node_types = {model.node_type for model in MODELS}
        self.assertIn(NodeType.upload_image, node_types)
        self.assertIn("wavespeed-ai/z-image/turbo", model_ids)
        self.assertIn("wavespeed-ai/z-image-turbo/image-to-image", model_ids)
        self.assertIn("deepseek/deepseek-v4-flash", model_ids)
        self.assertIn("openai/gpt-5-nano", model_ids)

    def test_project_json_loads_without_settings(self):
        project = Project.model_validate(
            {
                "id": "project_aaaaaaaaaaaa",
                "name": "Old Project",
                "nodes": [],
                "edges": [],
                "assets": [],
                "runs": [],
            }
        )
        self.assertEqual(project.settings.model_overrides, {})
        self.assertFalse(project.settings.cost_guard.enabled)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_incompatible_model_cannot_run(self):
        response = self.client.post(
            "/api/runs/node",
            json={
                "node_type": "text_to_image",
                "model_id": "wavespeed-ai/qwen3-tts/text-to-speech",
                "inputs": {"prompt": "ambient rain"},
                "save_to_project": False,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not registered for node type text_to_image", response.json()["detail"])

    def test_unknown_catalog_node_type_returns_clear_404(self):
        response = self.client.get("/api/model-catalog/nope")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Unknown model catalog node type", response.json()["detail"])

    def test_cost_estimate_endpoint_returns_known_estimate(self):
        response = self.client.post(
            "/api/runs/estimate",
            json={
                "node_type": "image_to_video",
                "model_id": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["estimated_base_cost_usd"], 0.05)
        self.assertEqual(body["cost_unit"], "run")
        self.assertIn("estimate", body["warning"])


class NodeRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_node_runner_rejects_missing_required_fields(self):
        with self.assertRaisesRegex(NodeRunError, "Prompt is required"):
            await prepare_inputs(FakeAdapter(), "wavespeed-ai/z-image/turbo", {}, None)

        with self.assertRaisesRegex(NodeRunError, "Text is required"):
            await prepare_inputs(FakeAdapter(), "wavespeed-ai/qwen3-tts/text-to-speech", {}, None)

        with self.assertRaisesRegex(NodeRunError, "image is required"):
            await prepare_inputs(
                FakeAdapter(),
                "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
                {"prompt": "Slow pan"},
                None,
            )


class WorkflowResolverTests(unittest.TestCase):
    def test_workflow_maps_image_output_to_image_to_video_input(self):
        project = Project(
            nodes=[
                CanvasNode(
                    id="node_image",
                    type=NodeType.text_to_image,
                    title="Image",
                    model_id="wavespeed-ai/z-image/turbo",
                    output_urls=["https://example.com/image.png"],
                ),
                CanvasNode(
                    id="node_video",
                    type=NodeType.image_to_video,
                    title="Video",
                    model_id="wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
                    inputs={"prompt": "Slow cinematic move"},
                ),
            ],
            edges=[
                CanvasEdge(
                    source_node_id="node_image",
                    target_node_id="node_video",
                    target_handle="input",
                )
            ],
        )
        plan = build_workflow_plan(project)
        video_step = next(step for step in plan["steps"] if step["node_id"] == "node_video")
        self.assertEqual(video_step["resolved_inputs"]["image"], "https://example.com/image.png")


if __name__ == "__main__":
    unittest.main()
