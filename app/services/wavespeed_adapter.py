from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx

from app.core.config import Settings


class WaveSpeedAdapter:
    """Thin wrapper around the WaveSpeed Python SDK.

    This is intentionally generic so Codex can add new model types by editing
    the model registry and front-end forms, not this service.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.wavespeed_api_key:
            os.environ["WAVESPEED_API_KEY"] = settings.wavespeed_api_key

    def require_api_key(self) -> None:
        if not self.settings.wavespeed_api_key and not os.environ.get("WAVESPEED_API_KEY"):
            raise RuntimeError("WAVESPEED_API_KEY is missing. Set it in .env or in your CMD session.")

    async def run_model(self, model_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.require_api_key()
        clean_inputs = self._clean_inputs(inputs)

        def _run() -> Dict[str, Any]:
            try:
                from wavespeed import Client
            except ImportError as exc:
                raise RuntimeError("WaveSpeed SDK is not installed. Run `pip install -r requirements.txt`.") from exc

            client = Client(api_key=os.environ.get("WAVESPEED_API_KEY"))
            return client.run(model_id, clean_inputs, timeout=36000.0, poll_interval=1.0)

        try:
            output = await asyncio.to_thread(_run)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"WaveSpeed run failed for {model_id}: {exc}") from exc
        if not isinstance(output, dict):
            raise RuntimeError("WaveSpeed returned an unexpected response type.")
        return output

    async def upload_file(self, path: Path) -> str:
        self.require_api_key()
        if not path.exists():
            raise RuntimeError(f"Upload file not found: {path}")

        def _upload() -> str:
            try:
                import wavespeed
            except ImportError as exc:
                raise RuntimeError("WaveSpeed SDK is not installed. Run `pip install -r requirements.txt`.") from exc

            return wavespeed.upload(str(path))

        try:
            uploaded_url = await asyncio.to_thread(_upload)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"WaveSpeed upload failed: {exc}") from exc
        if not isinstance(uploaded_url, str) or not uploaded_url.startswith(("http://", "https://")):
            raise RuntimeError("WaveSpeed upload did not return a usable URL.")
        return uploaded_url

    async def run_llm_chat(self, model_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.require_api_key()
        text = str(inputs.get("text") or "").strip()
        if not text:
            raise RuntimeError("text is required for LLM requests.")

        image = str(inputs.get("image") or "").strip()
        if image:
            content: str | list[dict[str, Any]] = [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image}},
            ]
        else:
            content = text

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": content}],
        }
        headers = {
            "Authorization": f"Bearer {os.environ.get('WAVESPEED_API_KEY')}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=3600.0) as client:
                response = await client.post(
                    "https://llm.wavespeed.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise RuntimeError(f"WaveSpeed LLM request failed for {model_id}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"WaveSpeed LLM request failed for {model_id}: {exc}") from exc

        output = response.json()
        if not isinstance(output, dict):
            raise RuntimeError("WaveSpeed LLM returned an unexpected response type.")
        return output

    @staticmethod
    def extract_output_urls(raw_output: Dict[str, Any]) -> List[str]:
        urls: List[str] = []

        def collect(value: Any) -> None:
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                urls.append(value)
            elif isinstance(value, list):
                for item in value:
                    collect(item)
            elif isinstance(value, dict):
                for key in ("url", "uri", "file", "image", "video", "audio", "output"):
                    if key in value:
                        collect(value[key])
                if "outputs" in value:
                    collect(value["outputs"])

        collect(raw_output.get("outputs"))
        collect(raw_output.get("output"))
        collect(raw_output.get("data"))
        if not urls:
            collect(raw_output)

        # Keep order while removing duplicates.
        return list(dict.fromkeys(urls))

    @staticmethod
    def _clean_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in inputs.items() if value not in (None, "")}
