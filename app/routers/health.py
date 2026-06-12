from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    return {
        "ok": True,
        "app": settings.app_name,
        "env": settings.app_env,
        "wavespeed_key_configured": bool(settings.wavespeed_api_key),
    }
