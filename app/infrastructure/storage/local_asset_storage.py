from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from app.core.config import Settings, get_settings


class LocalAssetStorage:
    """Local upload-directory storage adapter."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def path_for(self, filename: str) -> Path:
        return self.settings.upload_dir / filename

    async def save_upload(self, filename: str, stream: BinaryIO) -> Path:
        destination = self.path_for(filename)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            shutil.copyfileobj(stream, output)
        return destination

