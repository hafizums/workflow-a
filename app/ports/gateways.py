from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class ExternalModelGateway(Protocol):
    async def run_model(self, model_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        ...

    async def run_llm_chat(self, model_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        ...

    async def upload_file(self, path: Path) -> str:
        ...

