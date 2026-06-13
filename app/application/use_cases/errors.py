from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApplicationError(Exception):
    status_code: int
    detail: Any

    def __str__(self) -> str:
        return str(self.detail)

