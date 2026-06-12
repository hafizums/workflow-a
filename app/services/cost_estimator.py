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
        return {
            "requires_confirmation": False,
            "blocked": False,
            "cost_guard_message": None,
        }

    block_at = cost_guard.block_at_usd_per_run
    if block_at is not None and estimate >= block_at:
        return {
            "requires_confirmation": True,
            "blocked": True,
            "cost_guard_message": f"Estimated base cost ${estimate:.3f}/run meets or exceeds the block threshold ${block_at:.3f}/run.",
        }

    warn_at = cost_guard.warn_at_usd_per_run
    if warn_at is not None and estimate >= warn_at:
        return {
            "requires_confirmation": True,
            "blocked": False,
            "cost_guard_message": f"Estimated base cost ${estimate:.3f}/run meets or exceeds the warning threshold ${warn_at:.3f}/run.",
        }

    return {
        "requires_confirmation": False,
        "blocked": False,
        "cost_guard_message": None,
    }
