import unittest

from app.schemas import Asset, AssetKind, CanvasEdge, CanvasNode, NodeType, Project
from app.services.workflow_resolver import build_execution_plan, build_workflow_plan, resolve_source_output


class V10UtilityNodeTests(unittest.TestCase):
    def test_prompt_card_resolves_into_model_prompt(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A bright product photo"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[CanvasEdge(source_node_id="node_prompt", target_node_id="node_image", target_input="prompt")],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        image_step = next(step for step in plan["steps"] if step["node_id"] == "node_image")
        self.assertEqual(image_step["resolved_inputs"]["prompt"], "A bright product photo")
        self.assertEqual([step["node_id"] for step in plan["steps"]], ["node_image"])

    def test_prompt_card_generic_input_edge_defaults_to_prompt(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A bright product photo"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[CanvasEdge(source_node_id="node_prompt", target_node_id="node_image", target_input="input")],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        image_step = next(step for step in plan["steps"] if step["node_id"] == "node_image")
        self.assertEqual(image_step["resolved_inputs"]["prompt"], "A bright product photo")

    def test_llm_text_output_can_feed_model_prompt(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "Improve this"}),
                CanvasNode(
                    id="node_llm",
                    type=NodeType.llm_text,
                    title="LLM",
                    last_run={"text_output": "A refined product prompt"},
                ),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[
                CanvasEdge(source_node_id="node_prompt", target_node_id="node_llm", target_input="text"),
                CanvasEdge(source_node_id="node_llm", target_node_id="node_image", target_input="prompt"),
            ],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        image_step = next(step for step in plan["steps"] if step["node_id"] == "node_image")
        self.assertTrue(plan["ok"])
        self.assertEqual(image_step["resolved_inputs"]["prompt"], "A refined product prompt")

    def test_unrun_llm_prompt_source_must_run_first(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "Improve this"}),
                CanvasNode(id="node_llm", type=NodeType.llm_text, title="LLM"),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[
                CanvasEdge(source_node_id="node_prompt", target_node_id="node_llm", target_input="text"),
                CanvasEdge(source_node_id="node_llm", target_node_id="node_image", target_input="prompt"),
            ],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        self.assertFalse(plan["ok"])
        self.assertEqual(plan["errors"][0]["code"], "missing_upstream_output")

    def test_asset_input_resolves_selected_asset_id(self):
        project = Project(
            assets=[Asset(id="asset_image", kind=AssetKind.image, filename="image.png")],
            nodes=[CanvasNode(id="node_asset", type=NodeType.asset_input, title="Asset", inputs={"asset_id": "asset_image"})],
        )
        self.assertEqual(resolve_source_output(project.nodes[0], project), "asset_image")

    def test_compare_board_collects_selection_without_model_resolution_error(self):
        project = Project(
            assets=[Asset(id="asset_a", kind=AssetKind.image, filename="a.png")],
            nodes=[CanvasNode(id="node_compare", type=NodeType.compare_board, title="Compare", inputs={"selected_asset_id": "asset_a"})],
        )
        plan = build_workflow_plan(project, mode="whole_graph")
        self.assertTrue(plan["ok"])
        self.assertEqual(plan["node_ids"], [])
        self.assertEqual(resolve_source_output(project.nodes[0], project), "asset_a")

    def test_execution_plan_excludes_prompt_card_but_keeps_downstream_model(self):
        project = Project(
            nodes=[
                CanvasNode(id="node_prompt", type=NodeType.prompt_card, title="Prompt", inputs={"text": "A bright product photo"}),
                CanvasNode(id="node_image", type=NodeType.text_to_image, title="Image"),
            ],
            edges=[CanvasEdge(source_node_id="node_prompt", target_node_id="node_image", target_input="prompt")],
        )
        _graph, selected_ids, warnings, errors = build_execution_plan(project, mode="from_node", node_id="node_prompt")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(selected_ids, ["node_image"])


if __name__ == "__main__":
    unittest.main()
