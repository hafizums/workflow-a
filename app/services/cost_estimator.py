from __future__ import annotations

from app.schemas import CostGuardSettings, NodeType
from app.services.registry import resolve_model_for_node

ESTIMATE_WARNING = "This is an estimate, not exact billing."


def get_estimated_base_cost(
    node_type: NodeType | str,
    model_id: str | None = None,
    project_model_overrides: dict[str, str] | None = None,
    cost_guard: CostGuardSettings | None = None,
) -> dict:
    resolved_node_type = node_type if isinstance(node_type, NodeType) else NodeType(node_type)
    resolution = resolve_model_for_node(
        node_type=resolved_node_type,
        node_model_id=model_id,
        project_model_overrides=project_model_overrides or {},
    )
    if resolution.error:
        return {
            "ok": False,
            "node_type": resolved_node_type,
            "model_id": resolution.model_id,
            "model_source": resolution.source,
            "estimated_base_cost_usd": None,
            "cost_unit": None,
            "pricing_note": None,
            "warning": ESTIMATE_WARNING,
            "enabled": False,
            "enabled_reason": resolution.error,
            "verification_status": None,
            "requires_confirmation": False,
            "blocked": False,
            "cost_guard_message": None,
            "error": resolution.error,
        }

    model = resolution.model
    estimate = model.estimated_base_cost_usd if model else None
    guard = evaluate_cost_guard(estimate, cost_guard)
    return {
        "ok": True,
        "node_type": resolved_node_type,
        "model_id": resolution.model_id,
        "model_source": resolution.source,
        "estimated_base_cost_usd": estimate,
        "cost_unit": model.cost_unit if model else None,
        "pricing_note": model.pricing_note if model else None,
        "warning": ESTIMATE_WARNING,
        "enabled": bool(model and model.enabled),
        "enabled_reason": model.enabled_reason if model else None,
        "verification_status": model.verification_status if model else None,
        **guard,
    }


def evaluate_cost_guard(estimate: float | None, cost_guard: CostGuardSettings | None = None) -> dict:
    if estimate is None or cost_guard is None or not cost_guard.enabled:
        if estimate is None and cost_guard is not None and cost_guard.enabled and cost_guard.block_on_unknown_cost:
            return {
                "requires_confirmation": True,
                "blocked": True,
                "cost_guard_message": "Estimated cost is unknown and this project blocks unknown-cost runs.",
                "status": "blocked",
                "message": "Estimated cost is unknown and this project blocks unknown-cost runs.",
                "limit_usd": None,
            }
        return {
            "requires_confirmation": False,
            "blocked": False,
            "cost_guard_message": None,
            "status": "unknown" if estimate is None else "ok",
            "message": "Estimated cost is unknown." if estimate is None else None,
            "limit_usd": None,
        }

    block_at = cost_guard.block_at_usd_per_run
    if block_at is not None and estimate >= block_at:
        message = (
            f"Estimated base cost ${estimate:.3f}/run meets or exceeds "
            f"the block threshold ${block_at:.3f}/run."
        )
        return {
            "requires_confirmation": True,
            "blocked": True,
            "cost_guard_message": message,
            "status": "blocked",
            "message": message,
            "limit_usd": block_at,
        }

    warn_at = cost_guard.warn_at_usd_per_run
    if warn_at is not None and estimate >= warn_at:
        message = (
            f"Estimated base cost ${estimate:.3f}/run meets or exceeds "
            f"the warning threshold ${warn_at:.3f}/run."
        )
        return {
            "requires_confirmation": True,
            "blocked": False,
            "cost_guard_message": message,
            "status": "warning",
            "message": message,
            "limit_usd": warn_at,
        }

    return {
        "requires_confirmation": False,
        "blocked": False,
        "cost_guard_message": None,
        "status": "ok",
        "message": None,
        "limit_usd": None,
    }


def evaluate_workflow_cost_guard(
    estimated_total_cost_usd: float | None,
    has_unknown_cost: bool,
    cost_guard: CostGuardSettings | None = None,
) -> dict:
    if cost_guard is None or not cost_guard.enabled:
        return {
            "status": "unknown" if has_unknown_cost else "ok",
            "message": "One or more runnable steps have unknown estimated cost." if has_unknown_cost else None,
            "limit_usd": None,
            "blocked": False,
            "requires_confirmation": False,
        }

    if has_unknown_cost and cost_guard.block_on_unknown_cost:
        return {
            "status": "blocked",
            "message": "Workflow includes unknown-cost steps and this project blocks unknown-cost runs.",
            "limit_usd": None,
            "blocked": True,
            "requires_confirmation": True,
        }

    if has_unknown_cost:
        return {
            "status": "unknown",
            "message": "One or more runnable steps have unknown estimated cost.",
            "limit_usd": None,
            "blocked": False,
            "requires_confirmation": False,
        }

    if estimated_total_cost_usd is None:
        return {
            "status": "unknown",
            "message": "Workflow estimated cost is unknown.",
            "limit_usd": None,
            "blocked": False,
            "requires_confirmation": False,
        }

    max_workflow = cost_guard.max_workflow_run_usd
    if max_workflow is not None and estimated_total_cost_usd >= max_workflow:
        message = (
            f"Estimated workflow cost ${estimated_total_cost_usd:.3f} meets or exceeds "
            f"the workflow block threshold ${max_workflow:.3f}."
        )
        return {
            "status": "blocked",
            "message": message,
            "limit_usd": max_workflow,
            "blocked": True,
            "requires_confirmation": True,
        }

    warn_at = cost_guard.warn_at_usd_per_run
    if warn_at is not None and estimated_total_cost_usd >= warn_at:
        message = (
            f"Estimated workflow cost ${estimated_total_cost_usd:.3f} meets or exceeds "
            f"the warning threshold ${warn_at:.3f}."
        )
        return {
            "status": "warning",
            "message": message,
            "limit_usd": warn_at,
            "blocked": False,
            "requires_confirmation": True,
        }

    return {
        "status": "ok",
        "message": None,
        "limit_usd": None,
        "blocked": False,
        "requires_confirmation": False,
    }
