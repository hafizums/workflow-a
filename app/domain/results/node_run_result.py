from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas import Asset


@dataclass(slots=True)
class NodeRunResult:
    status: str
    model_id: str | None = None
    raw_output: dict[str, Any] = field(default_factory=dict)
    output_urls: list[str] = field(default_factory=list)
    output_asset_ids: list[str] = field(default_factory=list)
    output_assets: list[Asset] = field(default_factory=list)
    text_output: str | None = None
    structured_output: dict[str, Any] = field(default_factory=dict)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    error_message: str | None = None
