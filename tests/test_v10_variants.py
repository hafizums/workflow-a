import unittest
from unittest.mock import AsyncMock, patch

from app.schemas import CanvasNode, CostGuardSettings, NodeType, Project, ProjectSettings, VariantParameter, VariantRunRequest
from app.services.variant_runner import VariantError, build_variant_payloads, queue_variant_set
from app.services.run_manager import RunManagerError


class V10VariantTests(unittest.IsolatedAsyncioTestCase):
    def test_seed_variant_request_creates_n_payloads(self):
        node = CanvasNode(type=NodeType.text_to_image, title="Image", inputs={"prompt": "A product"})
        request = VariantRunRequest(project_id="project", node_id=node.id, variant_count=4)
        payloads = build_variant_payloads(node, request)
        self.assertEqual([payload["seed"] for payload in payloads], [1, 2, 3, 4])

    def test_prompt_suffix_variant_modifies_prompt(self):
        node = CanvasNode(type=NodeType.text_to_image, title="Image", inputs={"prompt": "A product"})
        request = VariantRunRequest(
            project_id="project",
            node_id=node.id,
            variant_count=2,
            parameters=[VariantParameter(field="prompt", strategy="prompt_suffix", values=["on marble", "on glass"])],
        )
        payloads = build_variant_payloads(node, request)
        self.assertEqual(payloads[0]["prompt"], "A product on marble")
        self.assertEqual(payloads[1]["prompt"], "A product on glass")

    async def test_variant_cost_guard_blocks_total(self):
        project = Project(
            settings=ProjectSettings(cost_guard=CostGuardSettings(enabled=True, max_workflow_run_usd=0.001)),
            nodes=[CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image", inputs={"prompt": "A product"})],
        )
        request = VariantRunRequest(project_id=project.id, node_id="node_image", variant_count=4)
        with self.assertRaisesRegex(VariantError, "threshold"):
            await queue_variant_set(project, request)

    async def test_partial_queue_failures_are_recorded(self):
        project = Project(nodes=[CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image", inputs={"prompt": "A product"})])
        request = VariantRunRequest(project_id=project.id, node_id="node_image", variant_count=2)

        async def fake_queue(project_id, node_id, save_to_project=True, request_metadata=None):
            if node_id.endswith("_2_" + node_id.split("_")[-1]):
                raise RunManagerError("boom")
            return type("Job", (), {"id": "job_ok", "request": {}})()

        with patch("app.services.variant_runner.project_store.save_project", new=AsyncMock()), patch(
            "app.services.variant_runner.run_manager.queue_node_run", side_effect=fake_queue
        ):
            variant_set = await queue_variant_set(project, request)
        self.assertIn("job_ok", variant_set.job_ids)
        self.assertTrue(variant_set.errors)


if __name__ == "__main__":
    unittest.main()
