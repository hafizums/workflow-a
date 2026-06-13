from __future__ import annotations

from app.application.dto.node_run_context import NodeRunContext
from app.domain.results.node_run_result import NodeRunResult
from app.ports.execution import NodeExecutor
from app.services import node_runner
from app.services.local_utility_runner import is_runnable_local_utility, run_local_utility
from app.services.registry import get_model_for_node


class NodeExecutorRegistry:
    def __init__(self, executors: list[NodeExecutor] | None = None):
        self.executors = executors or [
            LocalUtilityExecutor(),
            LlmExecutor(),
            GenericCatalogExecutor(),
            WaveSpeedModelExecutor(),
            NonRunnableUtilityExecutor(),
        ]

    def resolve(self, context: NodeRunContext) -> NodeExecutor:
        for executor in self.executors:
            if executor.supports(context):
                return executor
        raise RuntimeError(f"No executor is registered for node type {context.node_type.value}.")

    async def run(self, context: NodeRunContext) -> NodeRunResult:
        return await self.resolve(context).run(context)


class WaveSpeedModelExecutor:
    def supports(self, context: NodeRunContext) -> bool:
        if not context.effective_model_id or is_runnable_local_utility(context.node_type):
            return False
        model = get_model_for_node(context.node_type, context.effective_model_id)
        return bool(model and model.source == "curated" and context.request_metadata.get("adapter"))

    async def run(self, context: NodeRunContext) -> NodeRunResult:
        return await _run_wavespeed_facade(context)


class GenericCatalogExecutor:
    def supports(self, context: NodeRunContext) -> bool:
        if not context.effective_model_id or context.node_type.value == "llm_text":
            return False
        model = get_model_for_node(context.node_type, context.effective_model_id)
        return bool(model and model.source == "catalog" and context.request_metadata.get("adapter"))

    async def run(self, context: NodeRunContext) -> NodeRunResult:
        return await _run_wavespeed_facade(context)


class LlmExecutor:
    def supports(self, context: NodeRunContext) -> bool:
        if not context.effective_model_id:
            return False
        model = get_model_for_node(context.node_type, context.effective_model_id)
        return bool(model and "llm" in model.capability_tags and context.request_metadata.get("adapter")) if model else False

    async def run(self, context: NodeRunContext) -> NodeRunResult:
        return await _run_wavespeed_facade(context)


class LocalUtilityExecutor:
    def supports(self, context: NodeRunContext) -> bool:
        return is_runnable_local_utility(context.node_type)

    async def run(self, context: NodeRunContext) -> NodeRunResult:
        raw_output, output_urls, output_assets = await run_local_utility(
            node_type=context.node_type,
            inputs=context.resolved_inputs,
            project=context.project,
            target_node=context.node,
        )
        return NodeRunResult(
            status="success",
            model_id=context.effective_model_id,
            raw_output=raw_output,
            output_urls=output_urls,
            output_asset_ids=[asset.id for asset in output_assets],
            output_assets=output_assets,
            structured_output=raw_output,
        )


class NonRunnableUtilityExecutor:
    def supports(self, context: NodeRunContext) -> bool:
        return context.effective_model_id is None

    async def run(self, context: NodeRunContext) -> NodeRunResult:
        return NodeRunResult(
            status="skipped",
            model_id=context.effective_model_id,
            warnings=[{"code": "non_runnable_node", "message": "This node is not directly runnable."}],
        )


async def _run_wavespeed_facade(context: NodeRunContext) -> NodeRunResult:
    adapter = context.request_metadata.get("adapter")
    if adapter is None:
        raise RuntimeError("Node execution requires an external model adapter.")
    raw_output, output_urls, output_assets = await node_runner.run_wavespeed_node(
        adapter=adapter,
        model_id=context.effective_model_id,
        node_type=context.node_type,
        inputs=context.resolved_inputs,
        project=context.project,
        target_node=context.node,
    )
    text_output = node_runner.extract_text_output(raw_output)
    structured_output = raw_output if not output_urls and not text_output else {}
    return NodeRunResult(
        status="success",
        model_id=context.effective_model_id,
        raw_output=raw_output,
        output_urls=output_urls,
        output_asset_ids=[asset.id for asset in output_assets],
        output_assets=output_assets,
        text_output=text_output,
        structured_output=structured_output,
    )
