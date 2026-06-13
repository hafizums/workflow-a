from __future__ import annotations

from app.schemas import CostGuardSettings
from app.services.cost_estimator import evaluate_cost_guard, evaluate_workflow_cost_guard


class CostGuardPolicy:
    """Thin policy facade for existing local estimated-cost guard behavior."""

    def evaluate_run(self, estimate: float | None, cost_guard: CostGuardSettings | None = None) -> dict:
        return evaluate_cost_guard(estimate, cost_guard)

    def evaluate_workflow(
        self,
        estimated_total_cost_usd: float | None,
        has_unknown_cost: bool,
        cost_guard: CostGuardSettings | None = None,
    ) -> dict:
        return evaluate_workflow_cost_guard(estimated_total_cost_usd, has_unknown_cost, cost_guard)

