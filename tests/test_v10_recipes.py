import unittest

from app.schemas import NodeType, Project
from app.services.recipe_store import clone_recipe_graph, get_recipe, list_recipes
from app.services.utility_tools import UTILITY_NODE_TYPES
from app.services.workflow_resolver import build_graph, validate_prompt_card_inputs


class V10RecipeTests(unittest.TestCase):
    def test_builtin_recipes_load(self):
        recipes = list_recipes()
        self.assertGreaterEqual(len(recipes), 9)
        self.assertIn("recipe_product_ad_image_video", {recipe.id for recipe in recipes})

    def test_recipe_creates_valid_project_graph_parts(self):
        recipe = get_recipe("recipe_storyboard_explorer")
        nodes, edges = clone_recipe_graph(recipe)
        node_ids = {node.id for node in nodes}
        self.assertTrue(nodes)
        self.assertTrue(edges)
        self.assertTrue(all(edge.source_node_id in node_ids and edge.target_node_id in node_ids for edge in edges))

    def test_recipes_include_notes_or_disabled_placeholders_for_unavailable_capabilities(self):
        recipe = get_recipe("recipe_product_ad_image_video")
        self.assertTrue(recipe.required_capabilities)
        self.assertTrue(any(node.type.value == "export_package" for node in recipe.nodes))

    def test_recipes_cover_new_enabled_model_types(self):
        node_types = {node.type for recipe in list_recipes() for node in recipe.nodes}
        self.assertTrue(
            {
                NodeType.llm_text,
                NodeType.reference_to_video,
                NodeType.video_extend,
                NodeType.video_effect,
                NodeType.text_to_audio,
                NodeType.portrait_transfer,
                NodeType.image_to_3d,
            }.issubset(node_types)
        )

    def test_recipe_model_text_inputs_are_graph_sourced(self):
        for recipe in list_recipes():
            with self.subTest(recipe=recipe.id):
                for node in recipe.nodes:
                    if node.type in UTILITY_NODE_TYPES:
                        continue
                    self.assertNotIn("prompt", node.inputs, f"{node.id} should receive prompt from a text source node")
                    self.assertNotIn("text", node.inputs, f"{node.id} should receive text from a text source node")

    def test_recipe_prompt_requirements_have_valid_text_sources(self):
        for recipe in list_recipes():
            nodes, edges = clone_recipe_graph(recipe)
            graph = build_graph(Project(nodes=nodes, edges=edges))
            with self.subTest(recipe=recipe.id):
                self.assertFalse(graph.errors)
                prompt_errors = [error for node in nodes for error in validate_prompt_card_inputs(node, graph)]
                self.assertFalse(prompt_errors)


if __name__ == "__main__":
    unittest.main()
