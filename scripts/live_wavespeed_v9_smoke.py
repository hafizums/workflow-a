from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.schemas import NodeType
from app.services.node_runner import run_wavespeed_node
from app.services.wavespeed_adapter import WaveSpeedAdapter


@dataclass(frozen=True)
class LiveCase:
    name: str
    node_type: NodeType
    model_id: str
    inputs: dict[str, Any]
    required_env: tuple[str, ...] = ()


def env(name: str) -> str:
    return os.environ.get(name, "").strip()


def media(name: str) -> str:
    value = env(name)
    if value:
        return value
    if name.endswith("_URL"):
        return env(f"{name[:-4]}_PATH")
    return ""


def missing_media(name: str) -> bool:
    return not media(name)


def build_cases() -> list[LiveCase]:
    return [
        LiveCase(
            name="text_to_video",
            node_type=NodeType.text_to_video,
            model_id="wavespeed-ai/wan-2.2/t2v-480p-ultra-fast",
            inputs={
                "prompt": "A short clean product reveal on a neutral studio table",
                "negative_prompt": "",
                "size": "832*480",
                "duration": 5,
                "seed": -1,
            },
        ),
        LiveCase(
            name="start_end_to_video",
            node_type=NodeType.start_end_to_video,
            model_id="wavespeed-ai/wan-2.2/i2v-480p-ultra-fast",
            inputs={
                "image": media("V9_IMAGE_URL"),
                "last_image": media("V9_SECOND_IMAGE_URL"),
                "prompt": "Smooth camera motion from first frame to final frame",
                "duration": 5,
                "seed": -1,
            },
            required_env=("V9_IMAGE_URL", "V9_SECOND_IMAGE_URL"),
        ),
        LiveCase(
            name="speech_to_text",
            node_type=NodeType.speech_to_text,
            model_id="wavespeed-ai/openai-whisper",
            inputs={
                "audio": media("V9_AUDIO_URL"),
                "language": "auto",
                "task": "transcribe",
                "enable_timestamps": False,
                "prompt": "",
                "enable_sync_mode": False,
            },
            required_env=("V9_AUDIO_URL",),
        ),
        LiveCase(
            name="generate_voice",
            node_type=NodeType.generate_voice,
            model_id="wavespeed-ai/qwen3-tts/voice-design",
            inputs={
                "text": "Welcome to the V9 live smoke test.",
                "voice_description": "Warm, clear studio narrator",
                "language": "English",
            },
        ),
        LiveCase(
            name="lip_sync",
            node_type=NodeType.lip_sync,
            model_id="wavespeed-ai/latentsync",
            inputs={"video": media("V9_VIDEO_URL"), "audio": media("V9_AUDIO_URL")},
            required_env=("V9_VIDEO_URL", "V9_AUDIO_URL"),
        ),
        LiveCase(
            name="talking_avatar",
            node_type=NodeType.talking_avatar,
            model_id="wavespeed-ai/infinitetalk",
            inputs={
                "image": media("V9_IMAGE_URL"),
                "audio": media("V9_AUDIO_URL"),
                "prompt": "Natural expression",
                "resolution": "480p",
                "seed": -1,
            },
            required_env=("V9_IMAGE_URL", "V9_AUDIO_URL"),
        ),
        LiveCase(
            name="text_to_3d",
            node_type=NodeType.text_to_3d,
            model_id="wavespeed-ai/hunyuan-3d-v3.1/text-to-3d-rapid",
            inputs={"prompt": "A small ceramic vase with soft bevels"},
        ),
        LiveCase(
            name="remove_object",
            node_type=NodeType.remove_object,
            model_id="wavespeed-ai/z-image/turbo-inpaint",
            inputs={
                "prompt": "Remove the marked object and reconstruct the background",
                "image": media("V9_IMAGE_URL"),
                "mask_image": media("V9_MASK_IMAGE_URL"),
                "size": "1024*1024",
            },
            required_env=("V9_IMAGE_URL", "V9_MASK_IMAGE_URL"),
        ),
        LiveCase(
            name="reference_to_image",
            node_type=NodeType.reference_to_image,
            model_id="wavespeed-ai/z-image-turbo/image-to-image",
            inputs={
                "reference_image": media("V9_IMAGE_URL"),
                "prompt": "Create a fresh product poster using this composition",
                "size": "1024*1024",
                "strength": 0.6,
                "seed": -1,
                "output_format": "jpeg",
            },
            required_env=("V9_IMAGE_URL",),
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live WaveSpeed smoke tests for V9-enabled models.")
    parser.add_argument("--case", action="append", help="Case name to run. Repeatable. Defaults to all runnable cases.")
    parser.add_argument(
        "--confirm-spend-credits",
        action="store_true",
        help="Required. Live WaveSpeed calls may spend credits.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    if not args.confirm_spend_credits:
        print("Refusing to run live WaveSpeed calls without --confirm-spend-credits.")
        return 2

    adapter = WaveSpeedAdapter(get_settings())
    selected = set(args.case or [])
    cases = [case for case in build_cases() if not selected or case.name in selected]
    if selected and len(cases) != len(selected):
        known = ", ".join(case.name for case in build_cases())
        print(f"Unknown case requested. Known cases: {known}")
        return 2

    results = []
    for case in cases:
        missing = [name for name in case.required_env if missing_media(name)]
        if missing:
            results.append(
                {
                    "case": case.name,
                    "status": "skipped",
                    "missing_env": missing,
                    "note": "Set the listed *_URL variable or matching *_PATH variable.",
                }
            )
            continue
        print(f"Running {case.name} -> {case.model_id}")
        try:
            raw_output, output_urls, output_assets = await run_wavespeed_node(
                adapter=adapter,
                model_id=case.model_id,
                node_type=case.node_type,
                inputs=case.inputs,
            )
            results.append(
                {
                    "case": case.name,
                    "status": "ok",
                    "model_id": case.model_id,
                    "output_urls": output_urls,
                    "asset_filenames": [asset.filename for asset in output_assets],
                    "raw_output": raw_output,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "case": case.name,
                    "status": "error",
                    "model_id": case.model_id,
                    "error": str(exc),
                }
            )

    print(json.dumps(results, indent=2))
    return 0 if all(item["status"] in {"ok", "skipped"} for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
