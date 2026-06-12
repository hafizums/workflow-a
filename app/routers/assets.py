from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.core.config import get_settings
from app.schemas import ArtifactRole, Asset, AssetKind
from app.services.wavespeed_adapter import WaveSpeedAdapter

router = APIRouter(prefix="/api/assets", tags=["assets"])


def infer_asset_kind(content_type: str | None, filename: str) -> AssetKind:
    content_type = content_type or ""
    suffix = Path(filename).suffix.lower()
    if content_type.startswith("image/") or suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return AssetKind.image
    if content_type.startswith("video/") or suffix in {".mp4", ".mov", ".webm", ".mkv"}:
        return AssetKind.video
    if content_type.startswith("audio/") or suffix in {".mp3", ".wav", ".m4a", ".ogg", ".flac"}:
        return AssetKind.audio
    return AssetKind.other


@router.post("/upload", response_model=Asset)
async def upload_asset(request: Request, file: UploadFile = File(...), upload_to_wavespeed: bool = False):
    settings = get_settings()
    original_name = Path(file.filename or "upload.bin").name
    suffix = Path(original_name).suffix
    safe_name = f"{uuid4().hex}{suffix}"
    destination = settings.upload_dir / safe_name

    max_bytes = settings.max_upload_mb * 1024 * 1024
    total_bytes = 0

    async with aiofiles.open(destination, "wb") as output:
        while chunk := await file.read(1024 * 1024):
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                await output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"Upload exceeds {settings.max_upload_mb} MB")
            await output.write(chunk)

    public_url = str(request.url_for("uploads", path=safe_name))
    asset = Asset(
        kind=infer_asset_kind(file.content_type, original_name),
        filename=original_name,
        content_type=file.content_type,
        local_path=str(destination),
        public_url=public_url,
        metadata={"stored_filename": safe_name, "size_bytes": total_bytes},
    )
    asset.lineage.created_by = "upload"
    asset.view.role = ArtifactRole.input

    if upload_to_wavespeed:
        try:
            adapter = WaveSpeedAdapter(settings)
            asset.wavespeed_url = await adapter.upload_file(destination)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return asset
