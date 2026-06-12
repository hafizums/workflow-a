import unittest

from fastapi.testclient import TestClient

from app.main import app


class PortabilityApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.created_project_ids: list[str] = []
        self.created_template_ids: list[str] = []

    def tearDown(self):
        for template_id in self.created_template_ids:
            self.client.delete(f"/api/templates/{template_id}")
        for project_id in self.created_project_ids:
            self.client.delete(f"/api/projects/{project_id}")

    def create_project(self, name: str = "V5 Test Project") -> dict:
        response = self.client.post("/api/projects", json={"name": name})
        self.assertEqual(response.status_code, 200)
        project = response.json()
        self.created_project_ids.append(project["id"])
        return project

    def save_project(self, project: dict) -> dict:
        response = self.client.put(f"/api/projects/{project['id']}", json=project)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def populated_project(self) -> dict:
        project = self.create_project()
        project["nodes"] = [
            {
                "id": "node_source",
                "type": "text_to_image",
                "title": "Source",
                "x": 50,
                "y": 60,
                "inputs": {"prompt": "A glossy product shot"},
                "output_asset_ids": ["asset_source"],
                "output_urls": ["https://cdn.example.com/source.png"],
                "status": "success",
                "error_message": "old error",
            },
            {
                "id": "node_child",
                "type": "image_to_image",
                "title": "Child",
                "x": 380,
                "y": 80,
                "inputs": {"prompt": "Remix", "image": "https://cdn.example.com/source.png"},
            },
        ]
        project["edges"] = [
            {
                "id": "edge_source_child",
                "source_node_id": "node_source",
                "target_node_id": "node_child",
                "target_input": "image",
            }
        ]
        project["assets"] = [
            {
                "id": "asset_source",
                "kind": "image",
                "filename": "source.png",
                "local_path": "C:\\Users\\froxt\\secret\\source.png",
                "public_url": "http://localhost:8000/uploads/source.png",
                "wavespeed_url": "https://wavespeed.example/source.png",
                "metadata": {"source_node_id": "node_source"},
            }
        ]
        project["runs"] = [{"id": "run_old", "node_ids": ["node_source"], "asset_ids": ["asset_source"]}]
        return self.save_project(project)

    def test_export_endpoint_returns_portable_shape_and_strips_local_paths(self):
        project = self.populated_project()
        response = self.client.get(f"/api/projects/{project['id']}/export")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["schema"], "wavespeed_canvas_project_export")
        self.assertEqual(body["version"], 1)
        self.assertEqual(body["project"]["id"], project["id"])
        asset = body["project"]["assets"][0]
        self.assertIsNone(asset["local_path"])
        self.assertIsNone(asset["public_url"])
        self.assertEqual(asset["wavespeed_url"], "https://wavespeed.example/source.png")
        self.assertTrue(any("localhost URL" in warning for warning in body["warnings"]))
        self.assertIn("attachment", response.headers["content-disposition"])

    def test_export_can_omit_run_history(self):
        project = self.populated_project()
        response = self.client.get(f"/api/projects/{project['id']}/export?include_run_history=false")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["project"]["runs"], [])

    def test_import_accepts_valid_export_regenerates_ids_and_resets_status(self):
        project = self.populated_project()
        export = self.client.get(f"/api/projects/{project['id']}/export").json()
        response = self.client.post("/api/projects/import", json={"import_data": export, "name": "Imported Copy"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        imported = body["project"]
        self.created_project_ids.append(imported["id"])
        self.assertNotEqual(imported["id"], project["id"])
        self.assertEqual(imported["name"], "Imported Copy")
        self.assertNotEqual(imported["nodes"][0]["id"], "node_source")
        self.assertEqual(imported["nodes"][0]["status"], "idle")
        self.assertIsNone(imported["nodes"][0]["error_message"])
        self.assertEqual(imported["edges"][0]["source_node_id"], body["id_map"]["nodes"]["node_source"])
        self.assertEqual(imported["nodes"][0]["output_asset_ids"], [body["id_map"]["assets"]["asset_source"]])

    def test_import_rejects_invalid_node_type(self):
        response = self.client.post(
            "/api/projects/import",
            json={
                "import_data": {
                    "name": "Bad",
                    "nodes": [{"id": "node_bad", "type": "not_a_node", "title": "Bad"}],
                    "edges": [],
                    "assets": [],
                }
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not_a_node", response.json()["detail"])

    def test_import_rejects_edges_pointing_to_missing_nodes(self):
        response = self.client.post(
            "/api/projects/import",
            json={
                "import_data": {
                    "name": "Bad Edge",
                    "nodes": [{"id": "node_a", "type": "text_to_image", "title": "A"}],
                    "edges": [{"id": "edge_bad", "source_node_id": "node_a", "target_node_id": "missing"}],
                    "assets": [],
                }
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("missing node", response.json()["detail"])

    def test_import_warns_about_localhost_asset_urls(self):
        response = self.client.post(
            "/api/projects/import",
            json={
                "import_data": {
                    "name": "Localhost",
                    "nodes": [],
                    "edges": [],
                    "assets": [
                        {
                            "id": "asset_local",
                            "kind": "image",
                            "filename": "local.png",
                            "public_url": "http://127.0.0.1:8000/uploads/local.png",
                        }
                    ],
                }
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        project = response.json()["project"]
        self.created_project_ids.append(project["id"])
        self.assertTrue(any("localhost URL" in warning for warning in response.json()["warnings"]))
        self.assertIsNone(project["assets"][0]["public_url"])

    def test_duplicate_creates_new_project_with_remapped_ids_and_can_omit_runs(self):
        project = self.populated_project()
        response = self.client.post(
            f"/api/projects/{project['id']}/duplicate",
            json={"name": "Duplicated", "include_run_history": False},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        duplicate = body["project"]
        self.created_project_ids.append(duplicate["id"])
        self.assertNotEqual(duplicate["id"], project["id"])
        self.assertEqual(duplicate["runs"], [])
        self.assertEqual(duplicate["edges"][0]["source_node_id"], body["id_map"]["nodes"]["node_source"])


class TemplateApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.created_project_ids: list[str] = []
        self.created_template_ids: list[str] = []

    def tearDown(self):
        for template_id in self.created_template_ids:
            self.client.delete(f"/api/templates/{template_id}")
        for project_id in self.created_project_ids:
            self.client.delete(f"/api/projects/{project_id}")

    def create_project(self) -> dict:
        response = self.client.post("/api/projects", json={"name": "Template Source"})
        self.assertEqual(response.status_code, 200)
        project = response.json()
        self.created_project_ids.append(project["id"])
        project["nodes"] = [
            {
                "id": "node_tts",
                "type": "text_to_speech",
                "title": "Voiceover",
                "inputs": {"text": "Hello from a saved template."},
                "status": "success",
                "output_urls": ["https://cdn.example.com/voice.wav"],
            }
        ]
        response = self.client.put(f"/api/projects/{project['id']}", json=project)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_built_in_templates_are_listed(self):
        response = self.client.get("/api/templates")
        self.assertEqual(response.status_code, 200, response.text)
        ids = {template["id"] for template in response.json()}
        self.assertIn("template_basic_image_remix", ids)
        self.assertIn("template_voiceover_only", ids)

    def test_built_in_template_can_create_project(self):
        response = self.client.post(
            "/api/templates/template_basic_image_remix/create-project",
            json={"name": "From Basic Template"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        project = response.json()
        self.created_project_ids.append(project["id"])
        self.assertEqual(project["name"], "From Basic Template")
        self.assertEqual(len(project["nodes"]), 2)
        self.assertNotEqual(project["nodes"][0]["id"], "node_text_image")

    def test_user_template_can_be_created_from_project_and_deleted(self):
        project = self.create_project()
        response = self.client.post(
            f"/api/templates/from-project/{project['id']}",
            json={"name": "Saved Voiceover", "category": "audio", "tags": ["voice"]},
        )
        self.assertEqual(response.status_code, 200, response.text)
        template = response.json()
        self.created_template_ids.append(template["id"])
        self.assertFalse(template["builtin"])
        self.assertEqual(template["nodes"][0]["status"], "idle")
        self.assertEqual(template["nodes"][0]["output_urls"], [])

        delete_response = self.client.delete(f"/api/templates/{template['id']}")
        self.assertEqual(delete_response.status_code, 200, delete_response.text)
        self.created_template_ids.remove(template["id"])

    def test_built_in_template_cannot_be_deleted(self):
        response = self.client.delete("/api/templates/template_basic_image_remix")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Built-in templates cannot be deleted", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
