from __future__ import annotations

import unittest

from app.application.dto.node_run_context import NodeRunContext
from app.application.use_cases.node_executors import NodeExecutorRegistry
from app.application.use_cases.project_settings import ProjectSettingsUseCase
from app.domain.policies.cost_guard_policy import CostGuardPolicy
from app.domain.results.node_run_result import NodeRunResult
from app.schemas import CostGuardSettings, NodeType, ProjectSettings, ProjectSettingsUpdate


class CleanArchitectureSkeletonTests(unittest.IsolatedAsyncioTestCase):
    def test_project_settings_use_case_merges_partial_cost_guard_update(self):
        current = ProjectSettings(
            cost_guard=CostGuardSettings(
                enabled=True,
                warn_at_usd_per_run=0.25,
                block_at_usd_per_run=1.0,
                max_workflow_run_usd=2.0,
            )
        )
        payload = ProjectSettingsUpdate(cost_guard={"warn_at_usd_per_run": 0.5})

        merged = ProjectSettingsUseCase.merge(current, payload)

        self.assertTrue(merged.cost_guard.enabled)
        self.assertEqual(merged.cost_guard.warn_at_usd_per_run, 0.5)
        self.assertEqual(merged.cost_guard.block_at_usd_per_run, 1.0)
        self.assertEqual(merged.cost_guard.max_workflow_run_usd, 2.0)

    def test_cost_guard_policy_preserves_single_run_blocking_semantics(self):
        result = CostGuardPolicy().evaluate_run(
            1.0,
            CostGuardSettings(enabled=True, block_at_usd_per_run=1.0),
        )

        self.assertTrue(result["blocked"])
        self.assertEqual(result["status"], "blocked")

    async def test_node_executor_registry_selects_first_compatible_executor(self):
        class NoExecutor:
            def supports(self, context):
                return False

            async def run(self, context):
                raise AssertionError("This executor should not run")

        class YesExecutor:
            def supports(self, context):
                return True

            async def run(self, context):
                return NodeRunResult(status="success", model_id=context.effective_model_id)

        registry = NodeExecutorRegistry([NoExecutor(), YesExecutor()])
        result = await registry.run(
            NodeRunContext(
                project=None,
                node=None,
                node_type=NodeType.text_to_image,
                effective_model_id="test/model",
            )
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.model_id, "test/model")


if __name__ == "__main__":
    unittest.main()

