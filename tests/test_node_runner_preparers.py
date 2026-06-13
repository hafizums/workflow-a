import json
import unittest
from pathlib import Path

from app.schemas import Asset, AssetKind, CanvasNode, NodeType, Project
from app.services.node_runner import (
    DEEPSEEK_V4_FLASH_MODEL_ID,
    GPT_5_NANO_MODEL_ID,
    PROMPT_OPTIMIZER_MODEL_ID,
    extract_text_output,
    mark_node_success,
    prepare_image_to_3d_inputs,
    prepare_portrait_transfer_inputs,
    prepare_reference_to_image_inputs,
    prepare_reference_to_video_inputs,
    prepare_speech_to_text_inputs,
    prepare_start_end_to_video_inputs,
    prepare_text_to_video_inputs,
    prepare_video_extend_inputs,
    prepare_video_effect_inputs,
    run_wavespeed_node,
)
from app.services.wavespeed_adapter import WaveSpeedAdapter


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "wavespeed"


MODEL_FIXTURES = {
    "wavespeed-ai/wan-2.2/t2v-480p-ultra-fast": "text_to_video.json",
    "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast": "start_end_to_video.json",
    "wavespeed-ai/openai-whisper": "speech_to_text.json",
    "wavespeed-ai/qwen3-tts/text-to-speech": "text_to_speech.json",
    "wavespeed-ai/qwen3-tts/voice-design": "generate_voice.json",
    "wavespeed-ai/latentsync": "lip_sync.json",
    "wavespeed-ai/infinitetalk": "talking_avatar.json",
    "wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid": "text_to_3d.json",
    "wavespeed-ai/hunyuan3d-v2-multi-view": "image_to_3d.json",
    "wavespeed-ai/image-body-swap": "portrait_transfer.json",
    "wavespeed-ai/z-image/turbo-inpaint": "inpaint.json",
    "wavespeed-ai/z-image-turbo/image-to-image": "reference_to_image.json",
    "alibaba/wan-2.6/reference-to-video-flash": "reference_to_video.json",
    "vidu/q2-turbo/extend-video": "video_extend.json",
    "vidu/template/halloween": "video_effect.json",
}


class FakeAdapter:
    def __init__(self):
        self.calls = []

    async def upload_file(self, path):
        return f"https://wavespeed.example/uploads/{Path(path).name}"

    async def run_model(self, model_id, inputs):
        self.calls.append((model_id, inputs))
        with open(FIXTURE_DIR / MODEL_FIXTURES[model_id], encoding="utf-8") as file:
            return json.load(file)

    def extract_output_urls(self, raw_output):
        outputs = raw_output.get("outputs") or []
        return [item for item in outputs if isinstance(item, str) and item.startswith("http")]


class PromptOptimizerAdapter:
    def __init__(self):
        self.calls = []

    async def run_model(self, model_id, inputs):
        self.calls.append((model_id, dict(inputs)))
        if model_id == PROMPT_OPTIMIZER_MODEL_ID:
            return {"data": {"outputs": {"prompt": "Optimized cinematic product prompt"}}}
        return {"outputs": ["https://example.com/generated.png"]}

    def extract_output_urls(self, raw_output):
        outputs = raw_output.get("outputs") or []
        return [item for item in outputs if isinstance(item, str) and item.startswith("http")]


class LlmAdapter:
    def __init__(self):
        self.calls = []

    async def upload_file(self, path):
        return f"https://wavespeed.example/uploads/{Path(path).name}"

    async def run_llm_chat(self, model_id, inputs):
        self.calls.append((model_id, dict(inputs)))
        return {"choices": [{"message": {"content": f"Response from {model_id}"}}]}

    def extract_output_urls(self, raw_output):
        return []


class NodeRunnerPreparerTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_to_video_preparer_converts_duration_and_seed(self):
        prepared = await prepare_text_to_video_inputs(
            FakeAdapter(),
            {"prompt": "A glass sculpture forming", "duration": "8", "seed": "12"},
            None,
        )
        self.assertEqual(prepared["duration"], 8)
        self.assertEqual(prepared["seed"], 12)
        self.assertEqual(prepared["size"], "832*480")

    async def test_start_end_video_preparer_resolves_two_image_assets(self):
        project = Project(
            assets=[
                Asset(id="asset_start", kind=AssetKind.image, filename="start.png", public_url="https://example.com/start.png"),
                Asset(id="asset_end", kind=AssetKind.image, filename="end.png", public_url="https://example.com/end.png"),
            ]
        )
        prepared = await prepare_start_end_to_video_inputs(
            FakeAdapter(),
            {"prompt": "Move forward", "image": "asset_start", "last_image": "asset_end", "duration": "5"},
            project,
        )
        self.assertEqual(prepared["image"], "https://example.com/start.png")
        self.assertEqual(prepared["last_image"], "https://example.com/end.png")
        self.assertEqual(prepared["duration"], 5)

    async def test_reference_to_image_maps_reference_image_to_image(self):
        prepared = await prepare_reference_to_image_inputs(
            FakeAdapter(),
            {"prompt": "Use this pose", "reference_image": "https://example.com/ref.png"},
            None,
        )
        self.assertEqual(prepared["image"], "https://example.com/ref.png")
        self.assertNotIn("reference_image", prepared)

    async def test_image_to_image_accepts_reference_image_alias(self):
        project = Project(
            assets=[
                Asset(id="asset_ref", kind=AssetKind.image, filename="ref.png", public_url="https://example.com/ref.png")
            ]
        )
        adapter = FakeAdapter()

        await run_wavespeed_node(
            adapter,
            "wavespeed-ai/z-image-turbo/image-to-image",
            NodeType.image_to_image,
            {"prompt": "remix it", "reference_image": "asset_ref"},
            project=project,
        )

        self.assertEqual(adapter.calls[0][1]["image"], "https://example.com/ref.png")
        self.assertNotIn("reference_image", adapter.calls[0][1])

    async def test_reference_to_video_maps_reference_image_to_reference_urls(self):
        project = Project(
            assets=[
                Asset(id="asset_ref", kind=AssetKind.image, filename="ref.png", public_url="https://example.com/ref.png"),
                Asset(id="asset_audio", kind=AssetKind.audio, filename="sound.mp3", public_url="https://example.com/sound.mp3"),
            ]
        )
        prepared = await prepare_reference_to_video_inputs(
            FakeAdapter(),
            {"prompt": "Animate this reference", "reference_image": "asset_ref", "audio": "asset_audio", "duration": "10"},
            project,
        )
        self.assertEqual(prepared["reference_urls"], ["https://example.com/ref.png"])
        self.assertEqual(prepared["audio"], "https://example.com/sound.mp3")
        self.assertEqual(prepared["duration"], 10)
        self.assertEqual(prepared["size"], "1280*720")
        self.assertTrue(prepared["enable_audio"])
        self.assertNotIn("reference_image", prepared)

    async def test_video_extend_preparer_resolves_video_and_optional_image(self):
        project = Project(
            assets=[
                Asset(id="asset_video", kind=AssetKind.video, filename="clip.mp4", public_url="https://example.com/clip.mp4"),
                Asset(id="asset_image", kind=AssetKind.image, filename="end.png", public_url="https://example.com/end.png"),
            ]
        )
        prepared = await prepare_video_extend_inputs(
            FakeAdapter(),
            {
                "video": "asset_video",
                "image": "asset_image",
                "prompt": "Continue the camera move",
                "duration": "7",
                "resolution": "1080p",
            },
            project,
        )
        self.assertEqual(prepared["video"], "https://example.com/clip.mp4")
        self.assertEqual(prepared["image"], "https://example.com/end.png")
        self.assertEqual(prepared["prompt"], "Continue the camera move")
        self.assertEqual(prepared["duration"], 7)
        self.assertEqual(prepared["resolution"], "1080p")

    async def test_video_extend_rejects_invalid_duration(self):
        with self.assertRaisesRegex(Exception, "duration must be between 1 and 7"):
            await prepare_video_extend_inputs(
                FakeAdapter(),
                {"video": "https://example.com/clip.mp4", "duration": "8"},
                None,
            )

    async def test_video_effect_preparer_resolves_image_and_template(self):
        project = Project(
            assets=[
                Asset(id="asset_image", kind=AssetKind.image, filename="portrait.png", public_url="https://example.com/portrait.png")
            ]
        )
        prepared = await prepare_video_effect_inputs(
            FakeAdapter(),
            {"image": "asset_image", "template": "pumpkin_head", "bgm": False, "seed": "12"},
            project,
        )
        self.assertEqual(prepared["image"], "https://example.com/portrait.png")
        self.assertEqual(prepared["template"], "pumpkin_head")
        self.assertFalse(prepared["bgm"])
        self.assertEqual(prepared["seed"], 12)

    async def test_video_effect_rejects_invalid_template(self):
        with self.assertRaisesRegex(Exception, "template is not supported"):
            await prepare_video_effect_inputs(
                FakeAdapter(),
                {"image": "https://example.com/portrait.png", "template": "not_real"},
                None,
            )

    async def test_portrait_transfer_preparer_resolves_face_and_body_images(self):
        project = Project(
            assets=[
                Asset(id="asset_face", kind=AssetKind.image, filename="face.png", public_url="https://example.com/face.png"),
                Asset(id="asset_body", kind=AssetKind.image, filename="body.png", public_url="https://example.com/body.png"),
            ]
        )
        prepared = await prepare_portrait_transfer_inputs(
            FakeAdapter(),
            {"image": "asset_face", "body_image": "asset_body"},
            project,
        )
        self.assertEqual(prepared["image"], "https://example.com/face.png")
        self.assertEqual(prepared["body_image"], "https://example.com/body.png")

    async def test_image_to_3d_preparer_resolves_multiview_images(self):
        project = Project(
            assets=[
                Asset(id="asset_front", kind=AssetKind.image, filename="front.png", public_url="https://example.com/front.png"),
                Asset(id="asset_back", kind=AssetKind.image, filename="back.png", public_url="https://example.com/back.png"),
                Asset(id="asset_left", kind=AssetKind.image, filename="left.png", public_url="https://example.com/left.png"),
            ]
        )
        prepared = await prepare_image_to_3d_inputs(
            FakeAdapter(),
            {
                "front_image_url": "asset_front",
                "back_image_url": "asset_back",
                "left_image_url": "asset_left",
                "seed": "3",
                "num_inference_steps": "24",
                "guidance_scale": "6.5",
                "octree_resolution": "384",
                "textured_mesh": True,
            },
            project,
        )
        self.assertEqual(prepared["front_image_url"], "https://example.com/front.png")
        self.assertEqual(prepared["back_image_url"], "https://example.com/back.png")
        self.assertEqual(prepared["left_image_url"], "https://example.com/left.png")
        self.assertEqual(prepared["seed"], 3)
        self.assertEqual(prepared["num_inference_steps"], 24)
        self.assertEqual(prepared["guidance_scale"], 6.5)
        self.assertEqual(prepared["octree_resolution"], 384)
        self.assertTrue(prepared["textured_mesh"])

    async def test_speech_to_text_preparer_resolves_audio_assets(self):
        project = Project(
            assets=[
                Asset(id="asset_audio", kind=AssetKind.audio, filename="speech.mp3", public_url="https://example.com/speech.mp3")
            ]
        )
        prepared = await prepare_speech_to_text_inputs(FakeAdapter(), {"audio": "asset_audio"}, project)
        self.assertEqual(prepared["audio"], "https://example.com/speech.mp3")
        self.assertEqual(prepared["task"], "transcribe")

    async def test_enabled_v9_models_run_with_mocked_fixtures(self):
        cases = [
            (NodeType.text_to_video, "wavespeed-ai/wan-2.2/t2v-480p-ultra-fast", {"prompt": "A product reveal"}),
            (
                NodeType.start_end_to_video,
                "wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
                {"prompt": "A transition", "image": "https://example.com/a.png", "last_image": "https://example.com/b.png"},
            ),
            (NodeType.generate_voice, "wavespeed-ai/qwen3-tts/voice-design", {"text": "Hello", "voice_description": "Warm narrator"}),
            (NodeType.text_to_audio, "wavespeed-ai/qwen3-tts/text-to-speech", {"text": "Hello"}),
            (
                NodeType.lip_sync,
                "wavespeed-ai/latentsync",
                {"video": "https://example.com/talk.mp4", "audio": "https://example.com/voice.mp3"},
            ),
            (
                NodeType.talking_avatar,
                "wavespeed-ai/infinitetalk",
                {"image": "https://example.com/person.png", "audio": "https://example.com/voice.mp3"},
            ),
            (NodeType.text_to_3d, "wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid", {"prompt": "A ceramic vase"}),
            (
                NodeType.image_to_3d,
                "wavespeed-ai/hunyuan3d-v2-multi-view",
                {
                    "front_image_url": "https://example.com/front.png",
                    "back_image_url": "https://example.com/back.png",
                    "left_image_url": "https://example.com/left.png",
                },
            ),
            (
                NodeType.portrait_transfer,
                "wavespeed-ai/image-body-swap",
                {"image": "https://example.com/face.png", "body_image": "https://example.com/body.png"},
            ),
            (
                NodeType.remove_object,
                "wavespeed-ai/z-image/turbo-inpaint",
                {"prompt": "Remove the logo", "image": "https://example.com/a.png", "mask_image": "https://example.com/mask.png"},
            ),
            (
                NodeType.reference_to_image,
                "wavespeed-ai/z-image-turbo/image-to-image",
                {"prompt": "Use this composition", "reference_image": "https://example.com/ref.png"},
            ),
            (
                NodeType.reference_to_video,
                "alibaba/wan-2.6/reference-to-video-flash",
                {"prompt": "Animate this composition", "reference_image": "https://example.com/ref.png"},
            ),
            (
                NodeType.video_extend,
                "vidu/q2-turbo/extend-video",
                {"video": "https://example.com/clip.mp4", "duration": 5, "resolution": "720p"},
            ),
            (
                NodeType.video_effect,
                "vidu/template/halloween",
                {"image": "https://example.com/portrait.png", "template": "tim_burton"},
            ),
        ]
        for node_type, model_id, inputs in cases:
            with self.subTest(node_type=node_type.value):
                raw_output, output_urls, output_assets = await run_wavespeed_node(
                    FakeAdapter(),
                    model_id,
                    node_type,
                    inputs,
                )
                self.assertTrue(raw_output)
                self.assertTrue(output_urls)
                self.assertTrue(output_assets)

    async def test_speech_to_text_run_can_succeed_without_urls(self):
        node = CanvasNode(type=NodeType.speech_to_text, title="Transcribe")
        raw_output, output_urls, output_assets = await run_wavespeed_node(
            FakeAdapter(),
            "wavespeed-ai/openai-whisper",
            NodeType.speech_to_text,
            {"audio": "https://example.com/speech.mp3"},
            target_node=node,
        )
        self.assertEqual(output_urls, [])
        self.assertEqual(output_assets, [])
        self.assertEqual(extract_text_output(raw_output), "This is the transcript.")
        mark_node_success(node, "wavespeed-ai/openai-whisper", raw_output, output_urls, [])
        self.assertEqual(node.last_run["text_output"], "This is the transcript.")

    async def test_prompt_optimizer_runs_before_prompt_model_when_enabled(self):
        adapter = PromptOptimizerAdapter()
        node = CanvasNode(
            type=NodeType.text_to_image,
            title="Image",
            inputs={"use_prompt_optimizer": True},
        )

        raw_output, output_urls, output_assets = await run_wavespeed_node(
            adapter,
            "wavespeed-ai/z-image/turbo",
            NodeType.text_to_image,
            {
                "prompt": "shoe ad",
                "use_prompt_optimizer": True,
                "prompt_optimizer_style": "photographic",
                "prompt_optimizer_mode": "image",
            },
            target_node=node,
        )

        self.assertEqual([call[0] for call in adapter.calls], [PROMPT_OPTIMIZER_MODEL_ID, "wavespeed-ai/z-image/turbo"])
        self.assertEqual(adapter.calls[0][1]["text"], "shoe ad")
        self.assertEqual(adapter.calls[0][1]["style"], "photographic")
        self.assertEqual(adapter.calls[1][1]["prompt"], "Optimized cinematic product prompt")
        self.assertNotIn("use_prompt_optimizer", adapter.calls[1][1])
        self.assertEqual(output_urls, ["https://example.com/generated.png"])
        self.assertTrue(output_assets)
        self.assertEqual(raw_output["_prompt_optimizer"]["original_prompt"], "shoe ad")
        self.assertEqual(node.inputs, {"use_prompt_optimizer": True})

    async def test_llm_text_node_runs_through_chat_endpoint(self):
        adapter = LlmAdapter()
        node = CanvasNode(type=NodeType.llm_text, title="LLM")

        raw_output, output_urls, output_assets = await run_wavespeed_node(
            adapter,
            DEEPSEEK_V4_FLASH_MODEL_ID,
            NodeType.llm_text,
            {"text": "Write a headline"},
            target_node=node,
        )

        self.assertEqual(adapter.calls, [(DEEPSEEK_V4_FLASH_MODEL_ID, {"text": "Write a headline"})])
        self.assertEqual(output_urls, [])
        self.assertEqual(output_assets, [])
        self.assertEqual(extract_text_output(raw_output), f"Response from {DEEPSEEK_V4_FLASH_MODEL_ID}")

    async def test_llm_vision_node_resolves_legacy_optional_image(self):
        adapter = LlmAdapter()
        project = Project(
            assets=[
                Asset(id="asset_image", kind=AssetKind.image, filename="source.png", public_url="https://example.com/source.png")
            ]
        )

        raw_output, output_urls, output_assets = await run_wavespeed_node(
            adapter,
            GPT_5_NANO_MODEL_ID,
            NodeType.llm_vision,
            {"text": "Describe the image", "image": "asset_image"},
            project=project,
        )

        self.assertEqual(adapter.calls[0][0], GPT_5_NANO_MODEL_ID)
        self.assertEqual(adapter.calls[0][1]["text"], "Describe the image")
        self.assertEqual(adapter.calls[0][1]["images"], ["https://example.com/source.png"])
        self.assertEqual(output_urls, [])
        self.assertEqual(output_assets, [])
        self.assertEqual(extract_text_output(raw_output), f"Response from {GPT_5_NANO_MODEL_ID}")

    async def test_llm_vision_node_resolves_multiple_images(self):
        adapter = LlmAdapter()
        project = Project(
            assets=[
                Asset(id="asset_a", kind=AssetKind.image, filename="a.png", public_url="https://example.com/a.png"),
                Asset(id="asset_b", kind=AssetKind.image, filename="b.png", public_url="https://example.com/b.png"),
            ]
        )

        await run_wavespeed_node(
            adapter,
            GPT_5_NANO_MODEL_ID,
            NodeType.llm_vision,
            {"text": "Compare these images", "images": ["asset_a", "asset_b"]},
            project=project,
        )

        self.assertEqual(
            adapter.calls[0][1],
            {
                "text": "Compare these images",
                "images": ["https://example.com/a.png", "https://example.com/b.png"],
            },
        )

    def test_llm_message_content_supports_multiple_images(self):
        content = WaveSpeedAdapter._llm_message_content(
            "Compare these images",
            {"images": ["https://example.com/a.png", "https://example.com/b.png"]},
        )

        self.assertEqual(
            content,
            [
                {"type": "text", "text": "Compare these images"},
                {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
                {"type": "image_url", "image_url": {"url": "https://example.com/b.png"}},
            ],
        )


if __name__ == "__main__":
    unittest.main()
