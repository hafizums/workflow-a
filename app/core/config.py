from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env and environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "WaveSpeed Canvas MVP"
    app_env: str = "local"
    wavespeed_api_key: str | None = Field(default=None, validation_alias="WAVESPEED_API_KEY")
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    data_dir: Path = Path("data")
    upload_dir: Path = Path("data/uploads")
    project_dir: Path = Path("data/projects")
    max_upload_mb: int = 50

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def create_runtime_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.project_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.create_runtime_dirs()
    return settings
