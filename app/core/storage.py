import json
from pathlib import Path
from typing import Any

import aiofiles


async def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    async with aiofiles.open(path, "r", encoding="utf-8") as file:
        content = await file.read()
    if not content.strip():
        return default
    return json.loads(content)


async def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    async with aiofiles.open(path, "w", encoding="utf-8") as file:
        await file.write(data)
