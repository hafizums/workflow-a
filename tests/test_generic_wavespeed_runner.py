import pytest

from app.schemas import NodeType, Project
from app.services.node_runner import run_wavespeed_node


class FakeAdapter:
    def __init__(self):
        self.calls = []

    async def run_model(self, model_id, inputs):
        self.calls.append((model_id, inputs))
        return {"outputs": ["https://example.com/out.mp4"]}

    async def run_llm_chat(self, model_id, inputs):
        self.calls.append((model_id, inputs))
        return {"choices": [{"message": {"content": "hello"}}]}

    async def upload_file(self, path):
        return f"https://files.example/{path.name}"


@pytest.mark.asyncio
async def test_generic_wavespeed_run_uses_exact_catalog_model_id():
    adapter = FakeAdapter()
    raw, urls, assets = await run_wavespeed_node(
        adapter=adapter,
        model_id="alibaba/happyhorse-1.0/text-to-video",
        node_type=NodeType.generic_wavespeed,
        inputs={"prompt": "A clean product reveal", "duration": 5, "resolution": "720p"},
        project=Project(),
    )
    assert adapter.calls[0][0] == "alibaba/happyhorse-1.0/text-to-video"
    assert raw["outputs"]
    assert urls == ["https://example.com/out.mp4"]
    assert assets[0].public_url == "https://example.com/out.mp4"


@pytest.mark.asyncio
async def test_old_curated_node_still_runs_with_tuned_path():
    adapter = FakeAdapter()
    await run_wavespeed_node(
        adapter=adapter,
        model_id="wavespeed-ai/z-image/turbo",
        node_type=NodeType.text_to_image,
        inputs={"prompt": "poster"},
        project=Project(),
    )
    assert adapter.calls[0][0] == "wavespeed-ai/z-image/turbo"
