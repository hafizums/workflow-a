import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Project


class ProjectSettingsApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.created_project_ids: list[str] = []

    def tearDown(self):
        for project_id in self.created_project_ids:
            self.client.delete(f"/api/projects/{project_id}")

    def create_project(self) -> dict:
        response = self.client.post("/api/projects", json={"name": "V4 Settings Test"})
        self.assertEqual(response.status_code, 200)
        project = response.json()
        self.created_project_ids.append(project["id"])
        return project

    def save_project(self, project: dict) -> dict:
        response = self.client.put(f"/api/projects/{project['id']}", json=project)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_old_project_shape_loads_with_default_settings(self):
        project = Project.model_validate(
            {
                "id": "project_bbbbbbbbbbbb",
                "name": "Old Project",
                "nodes": [],
                "edges": [],
                "assets": [],
            }
        )
        self.assertEqual(project.settings.model_overrides, {})
        self.assertFalse(project.settings.cost_guard.enabled)
        self.assertIsNone(project.settings.cost_guard.max_workflow_run_usd)
        self.assertFalse(project.settings.cost_guard.block_on_unknown_cost)

    def test_settings_endpoint_returns_defaults(self):
        project = self.create_project()
        response = self.client.get(f"/api/projects/{project['id']}/settings")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["model_overrides"], {})
        self.assertFalse(body["cost_guard"]["enabled"])
        self.assertIsNone(body["cost_guard"]["max_workflow_run_usd"])
        self.assertFalse(body["cost_guard"]["block_on_unknown_cost"])

    def test_settings_endpoint_persists_valid_update(self):
        project = self.create_project()
        payload = {
            "model_overrides": {
                "text_to_image": "wavespeed-ai/z-image/turbo",
                "image_to_video": "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
            },
            "cost_guard": {
                "enabled": True,
                "warn_above_usd": 0.004,
                "max_single_run_usd": 0.1,
                "max_workflow_run_usd": 0.25,
                "block_on_unknown_cost": True,
            },
        }
        response = self.client.put(f"/api/projects/{project['id']}/settings", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["model_overrides"], payload["model_overrides"])
        self.assertEqual(body["cost_guard"]["warn_at_usd_per_run"], 0.004)
        self.assertEqual(body["cost_guard"]["block_at_usd_per_run"], 0.1)
        self.assertEqual(body["cost_guard"]["max_workflow_run_usd"], 0.25)
        self.assertTrue(body["cost_guard"]["block_on_unknown_cost"])

        persisted = self.client.get(f"/api/projects/{project['id']}/settings").json()
        self.assertEqual(persisted, body)

    def test_invalid_node_type_override_is_rejected(self):
        project = self.create_project()
        response = self.client.put(
            f"/api/projects/{project['id']}/settings",
            json={"model_overrides": {"not_a_node": "wavespeed-ai/z-image/turbo"}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown node type", response.json()["detail"])

    def test_disabled_model_override_is_rejected(self):
        project = self.create_project()
        response = self.client.put(
            f"/api/projects/{project['id']}/settings",
            json={"model_overrides": {"remove_object": "wavespeed-ai/z-image/turbo-inpaint"}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Disabled", response.json()["detail"])

    def test_incompatible_model_override_is_rejected(self):
        project = self.create_project()
        response = self.client.put(
            f"/api/projects/{project['id']}/settings",
            json={"model_overrides": {"text_to_image": "wavespeed-ai/z-image-turbo/image-to-image"}},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not registered for node type text_to_image", response.json()["detail"])

    def test_invalid_cost_guard_thresholds_are_rejected(self):
        project = self.create_project()
        response = self.client.put(
            f"/api/projects/{project['id']}/settings",
            json={
                "cost_guard": {
                    "enabled": True,
                    "warn_at_usd_per_run": 0.2,
                    "block_at_usd_per_run": 0.1,
                }
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_full_project_update_validates_settings_overrides(self):
        project = self.create_project()
        project["settings"]["model_overrides"] = {
            "remove_object": "wavespeed-ai/z-image/turbo-inpaint",
        }
        response = self.client.put(f"/api/projects/{project['id']}", json=project)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Disabled", response.json()["detail"])

    def test_cost_guard_blocks_single_run_estimate_above_max(self):
        project = self.create_project()
        self.client.put(
            f"/api/projects/{project['id']}/settings",
            json={
                "cost_guard": {
                    "enabled": True,
                    "max_single_run_usd": 0.004,
                }
            },
        )
        response = self.client.post(
            "/api/runs/estimate",
            json={
                "project_id": project["id"],
                "node_type": "text_to_image",
                "model_id": "wavespeed-ai/z-image/turbo",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["blocked"])
        self.assertEqual(body["status"], "blocked")
        self.assertEqual(body["limit_usd"], 0.004)

    def test_cost_guard_allows_single_run_below_max(self):
        project = self.create_project()
        self.client.put(
            f"/api/projects/{project['id']}/settings",
            json={
                "cost_guard": {
                    "enabled": True,
                    "max_single_run_usd": 0.01,
                }
            },
        )
        response = self.client.post(
            "/api/runs/estimate",
            json={
                "project_id": project["id"],
                "node_type": "text_to_image",
                "model_id": "wavespeed-ai/z-image/turbo",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["blocked"])
        self.assertEqual(body["status"], "ok")

    def test_workflow_plan_includes_estimated_total_cost(self):
        project = self.create_project()
        project["nodes"] = [
            {
                "id": "node_image",
                "type": "text_to_image",
                "title": "Image",
                "model_id": "wavespeed-ai/z-image/turbo",
                "inputs": {"prompt": "A studio product photo"},
            },
            {
                "id": "node_bg",
                "type": "remove_background",
                "title": "Remove Background",
                "model_id": "wavespeed-ai/image-background-remover",
                "inputs": {"image": "https://example.com/image.png"},
            },
        ]
        project = self.save_project(project)

        response = self.client.get(f"/api/workflows/{project['id']}/plan?mode=whole_graph")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["estimated_total_cost_usd"], 0.009)
        self.assertEqual(body["estimated_known_cost_usd"], 0.009)
        self.assertEqual(body["cost_guard"]["status"], "ok")
        self.assertEqual(len(body["steps"]), 2)

    def test_workflow_plan_blocks_when_total_exceeds_max(self):
        project = self.create_project()
        project["settings"]["cost_guard"] = {
            "enabled": True,
            "warn_at_usd_per_run": None,
            "block_at_usd_per_run": None,
            "max_workflow_run_usd": 0.006,
            "block_on_unknown_cost": False,
        }
        project["nodes"] = [
            {
                "id": "node_image",
                "type": "text_to_image",
                "title": "Image",
                "model_id": "wavespeed-ai/z-image/turbo",
                "inputs": {"prompt": "A studio product photo"},
            },
            {
                "id": "node_bg",
                "type": "remove_background",
                "title": "Remove Background",
                "model_id": "wavespeed-ai/image-background-remover",
                "inputs": {"image": "https://example.com/image.png"},
            },
        ]
        project = self.save_project(project)

        response = self.client.get(f"/api/workflows/{project['id']}/plan?mode=whole_graph")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["estimated_total_cost_usd"], 0.009)
        self.assertEqual(body["cost_guard"]["status"], "blocked")
        self.assertTrue(body["cost_guard"]["blocked"])

    def test_workflow_run_blocks_before_execution_when_total_exceeds_max(self):
        project = self.create_project()
        project["settings"]["cost_guard"] = {
            "enabled": True,
            "warn_at_usd_per_run": None,
            "block_at_usd_per_run": None,
            "max_workflow_run_usd": 0.006,
            "block_on_unknown_cost": False,
        }
        project["nodes"] = [
            {
                "id": "node_image",
                "type": "text_to_image",
                "title": "Image",
                "model_id": "wavespeed-ai/z-image/turbo",
                "inputs": {"prompt": "A studio product photo"},
            },
            {
                "id": "node_bg",
                "type": "remove_background",
                "title": "Remove Background",
                "model_id": "wavespeed-ai/image-background-remover",
                "inputs": {"image": "https://example.com/image.png"},
            },
        ]
        project = self.save_project(project)

        response = self.client.post(f"/api/workflows/{project['id']}/run-all")
        self.assertEqual(response.status_code, 400)
        body = response.json()["detail"]
        self.assertEqual(body["errors"][0]["code"], "workflow_cost_guard_blocked")
        self.assertEqual(body["estimated_total_cost_usd"], 0.009)

        persisted = self.client.get(f"/api/projects/{project['id']}").json()
        self.assertEqual(persisted["nodes"][0]["status"], "idle")
        self.assertEqual(persisted["nodes"][1]["status"], "idle")


if __name__ == "__main__":
    unittest.main()
