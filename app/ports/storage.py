from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Protocol


class AssetStorage(Protocol):
    def path_for(self, filename: str) -> Path:
        ...

    async def save_upload(self, filename: str, stream: BinaryIO) -> Path:
        ...

