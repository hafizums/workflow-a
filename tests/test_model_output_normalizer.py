from app.schemas import AssetKind
from app.services.model_output_normalizer import normalize_model_output
from app.services.registry import get_model_by_id


def test_nested_url_outputs_become_assets():
    model = get_model_by_id("alibaba/happyhorse-1.0/text-to-video")
    urls, assets, text, structured = normalize_model_output(
        model=model,
        model_id=model.id,
        raw_output={"data": {"output": {"video": "https://example.com/out.mp4"}}},
    )
    assert urls == ["https://example.com/out.mp4"]
    assert assets[0].kind == AssetKind.video
    assert text is None
    assert structured == {}


def test_text_only_output_does_not_fail():
    model = get_model_by_id("openai/gpt-5-nano")
    urls, assets, text, structured = normalize_model_output(
        model=model,
        model_id=model.id,
        raw_output={"choices": [{"message": {"content": "hello"}}]},
    )
    assert urls == []
    assert assets == []
    assert text == "hello"
    assert structured == {}


def test_json_only_output_is_structured():
    model = get_model_by_id("wavespeed-ai/openai-whisper")
    urls, assets, text, structured = normalize_model_output(
        model=model,
        model_id=model.id,
        raw_output={"segments": [{"text": "hello"}]},
    )
    assert urls == []
    assert assets == []
    assert text is None
    assert structured["segments"][0]["text"] == "hello"
