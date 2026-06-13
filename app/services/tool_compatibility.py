from __future__ import annotations

from app.schemas import CanvasNode, ModelField, ModelSpec


def required_field_names(model: ModelSpec) -> set[str]:
    return {field.name for field in model.fields if field.required}


def compatible_models_for_node(source_node: CanvasNode, all_models: list[ModelSpec]) -> list[ModelSpec]:
    source_models = [
        model
        for model in all_models
        if model.enabled
        and (
            model.node_type == source_node.type
            or (source_node.model_id and source_node.model_id in {model.id, model.default_model_id, model.model_id})
        )
    ]
    if not source_models:
        return []
    base = source_models[0]
    base_capability = base.primary_capability
    return [
        model
        for model in all_models
        if model.output_kind == base.output_kind and required_field_names(model) == required_field_names(base)
        and (not base_capability or model.primary_capability == base_capability or base_capability in model.capability_tags)
        and model.enabled
    ]


def can_compare_models(models: list[ModelSpec]) -> tuple[bool, str]:
    if len(models) < 2:
        return False, "At least two compatible enabled models are required. Use variants instead."
    output_kind = models[0].output_kind
    required = required_field_names(models[0])
    for model in models[1:]:
        if model.output_kind != output_kind:
            return False, f"Model {model.id} outputs {model.output_kind.value}, expected {output_kind.value}."
        if required_field_names(model) != required:
            return False, f"Model {model.id} has different required inputs."
    return True, ""


def can_connect_output_to_input(source_output_kind, target_input_spec: ModelField) -> tuple[bool, str]:
    expected = target_input_spec.asset_kind
    if expected is None:
        return True, ""
    if getattr(source_output_kind, "value", source_output_kind) == expected.value:
        return True, ""
    return False, f"Cannot connect {source_output_kind} output to {expected.value} input {target_input_spec.name}."
