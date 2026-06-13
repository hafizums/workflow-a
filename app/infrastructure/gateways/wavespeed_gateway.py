from __future__ import annotations

from app.core.config import Settings
from app.services.wavespeed_adapter import WaveSpeedAdapter


class WaveSpeedGateway(WaveSpeedAdapter):
    """External model gateway backed by the existing WaveSpeed adapter."""

    def __init__(self, settings: Settings):
        super().__init__(settings)

