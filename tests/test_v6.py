import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import CanvasEdge, CanvasNode, NodeType, Project
from app.services.portable_project import clone_project, export_project, project_from_import_data
from app.services.template_store import create_template_from_project
from app.services.workflow_resolver import build_graph, build_workflow_plan


class EdgeCompatibilityTests(unittest.TestCase):
    def test_v6_edge_shape_is_accepted_by_schema(self):
        edge = CanvasEdge.model_validate(
            {
                "id": "edge_v6",
                "source_node_id": "node_source",
                "target_node_id": "node_target",
                "source_handle": "output",
                "target_handle": "last_image",
                "source_output": "output",
                "target_input": "last_image",
            }
        )
        self.assertEqual(edge.source_node_id, "node_source")
        self.assertEqual(edge.target_node_id, "node_target")
        self.assertEqual(edge.source_output, "output")
        self.assertEqual(edge.target_input, "last_image")

    def test_old_alias_based_edge_still_normalizes(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_a", type=NodeType.text_to_image, title="A"),
                CanvasNode(id="node_b", type=NodeType.image_to_image, title="B"),
            ],
            edges=[CanvasEdge.model_validate({"id": "edge_old", "from": "node_a", "to": "node_b"})],
        )
        graph = build_graph(project)
        self.assertFalse(graph.errors)
        self.assertEqual(graph.edges[0].source_node_id, "node_a")
        self.assertEqual(graph.edges[0].target_node_id, "node_b")
        self.assertEqual(graph.edges[0].target_input, "image")

    def test_workflow_plan_preserves_explicit_target_input(self):
        project = Project(
            nodes=[
                CanvasNode(
                    id="node_start",
                    type=NodeType.text_to_image,
                    title="Start",
                    output_urls=["https://example.com/start.png"],
                ),
                CanvasNode(
                    id="node_video",
                    type=NodeType.image_to_video,
                    title="Video",
                    inputs={"image": "https://example.com/first.png"},
                ),
                CanvasNode(id="node_prompt_start", type=NodeType.prompt_card, title="Start Prompt", inputs={"text": "Start image"}),
                CanvasNode(id="node_prompt_video", type=NodeType.prompt_card, title="Video Prompt", inputs={"text": "Slow move"}),
            ],
            edges=[
                CanvasEdge(id="edge_prompt_start", source_node_id="node_prompt_start", target_node_id="node_start", target_input="prompt"),
                CanvasEdge(id="edge_prompt_video", source_node_id="node_prompt_video", target_node_id="node_video", target_input="prompt"),
                CanvasEdge(
                    id="edge_last",
                    source_node_id="node_start",
                    target_node_id="node_video",
                    source_output="output",
                    target_input="last_image",
                    source_handle="output",
                    target_handle="last_image",
                )
            ],
        )
        plan = build_workflow_plan(project)
        video_step = next(step for step in plan["steps"] if step["node_id"] == "node_video")
        self.assertEqual(video_step["resolved_inputs"]["last_image"], "https://example.com/start.png")
        self.assertEqual(video_step["resolved_inputs"]["image"], "https://example.com/first.png")

    def test_workflow_plan_reports_cycle_errors(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_a", type=NodeType.text_to_image, title="A"),
                CanvasNode(id="node_b", type=NodeType.image_to_image, title="B"),
            ],
            edges=[
                CanvasEdge(id="edge_ab", source_node_id="node_a", target_node_id="node_b", target_input="image"),
                CanvasEdge(id="edge_ba", source_node_id="node_b", target_node_id="node_a", target_input="image"),
            ],
        )
        plan = build_workflow_plan(project)
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["errors"][0]["code"], "cycle_detected")

    def test_workflow_plan_reports_missing_edge_node_references(self):
        project = Project(
            nodes=[CanvasNode(id="node_a", type=NodeType.text_to_image, title="A")],
            edges=[CanvasEdge(id="edge_missing", source_node_id="node_a", target_node_id="missing", target_input="image")],
        )
        plan = build_workflow_plan(project)
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["errors"][0]["code"], "invalid_edge_target")

    def test_duplicate_edges_do_not_crash_planning(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_a", type=NodeType.text_to_image, title="A", output_urls=["https://example.com/a.png"]),
                CanvasNode(id="node_b", type=NodeType.image_to_image, title="B"),
                CanvasNode(id="node_prompt_a", type=NodeType.prompt_card, title="Prompt A", inputs={"text": "A"}),
                CanvasNode(id="node_prompt_b", type=NodeType.prompt_card, title="Prompt B", inputs={"text": "B"}),
            ],
            edges=[
                CanvasEdge(id="edge_prompt_a", source_node_id="node_prompt_a", target_node_id="node_a", target_input="prompt"),
                CanvasEdge(id="edge_prompt_b", source_node_id="node_prompt_b", target_node_id="node_b", target_input="prompt"),
                CanvasEdge(id="edge_one", source_node_id="node_a", target_node_id="node_b", target_input="image"),
                CanvasEdge(id="edge_two", source_node_id="node_a", target_node_id="node_b", target_input="image"),
            ],
        )
        plan = build_workflow_plan(project)
        self.assertTrue(plan["ok"], plan["errors"])
        self.assertEqual(len(plan["steps"][1]["incoming_edges"]), 2)
        self.assertEqual(plan["warnings"][0]["code"], "duplicate_edge")

    def test_export_import_clone_preserves_v6_edge_fields(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_a", type=NodeType.text_to_image, title="A"),
                CanvasNode(id="node_b", type=NodeType.image_to_video, title="B"),
            ],
            edges=[
                CanvasEdge(
                    id="edge_v6",
                    source_node_id="node_a",
                    target_node_id="node_b",
                    source_handle="output",
                    target_handle="last_image",
                    source_output="output",
                    target_input="last_image",
                )
            ],
        )
        exported = export_project(project)
        self.assertEqual(exported["project"]["edges"][0]["target_input"], "last_image")

        imported, warnings = project_from_import_data(exported)
        self.assertFalse(warnings)
        cloned, id_map, clone_warnings = clone_project(
            imported,
            name="Copy",
            include_outputs=True,
            include_run_history=False,
            preserve_settings=True,
            reset_runtime=True,
        )
        self.assertFalse(clone_warnings)
        edge = cloned.edges[0]
        self.assertEqual(edge.target_input, "last_image")
        self.assertEqual(edge.target_handle, "last_image")
        self.assertEqual(edge.source_node_id, id_map["nodes"]["node_a"])
        self.assertEqual(edge.target_node_id, id_map["nodes"]["node_b"])


class TemplateEdgeCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_template_from_project_preserves_v6_edge_fields(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_a", type=NodeType.text_to_image, title="A"),
                CanvasNode(id="node_b", type=NodeType.image_to_video, title="B"),
            ],
            edges=[
                CanvasEdge(
                    id="edge_template",
                    source_node_id="node_a",
                    target_node_id="node_b",
                    source_output="output",
                    target_input="last_image",
                    source_handle="output",
                    target_handle="last_image",
                )
            ],
        )
        template = await create_template_from_project(
            project,
            name="V6 Edge Template",
            description="",
            category="test",
            tags=[],
        )
        try:
            self.assertEqual(template.edges[0].target_input, "last_image")
            self.assertEqual(template.edges[0].target_handle, "last_image")
        finally:
            TestClient(app).delete(f"/api/templates/{template.id}")


if __name__ == "__main__":
    unittest.main()
