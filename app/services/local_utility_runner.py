from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import imageio.v2 as imageio
import imageio_ffmpeg

from app.core.config import get_settings
from app.schemas import ArtifactRole, Asset, AssetKind, CanvasNode, NodeType, Project
from app.services.node_runner import find_asset, is_http_url
from app.services.utility_tools import RUNNABLE_LOCAL_UTILITY_NODE_TYPES


class LocalUtilityRunError(ValueError):
    pass


def is_runnable_local_utility(node_type: NodeType) -> bool:
    return node_type in RUNNABLE_LOCAL_UTILITY_NODE_TYPES


async def run_local_utility(
    *,
    node_type: NodeType,
    inputs: dict[str, Any],
    project: Project | None,
    target_node: CanvasNode | None,
) -> tuple[dict[str, Any], list[str], list[Asset]]:
    if node_type == NodeType.video_last_frame:
        return await run_video_last_frame(inputs=inputs, project=project, target_node=target_node)
    if node_type == NodeType.stitch_video:
        return await run_stitch_video(inputs=inputs, project=project, target_node=target_node)
    raise LocalUtilityRunError(f"No local runner is registered for utility node type {node_type.value}.")


async def run_video_last_frame(
    *,
    inputs: dict[str, Any],
    project: Project | None,
    target_node: CanvasNode | None,
) -> tuple[dict[str, Any], list[str], list[Asset]]:
    video_ref = str(inputs.get("video") or inputs.get("asset_id") or inputs.get("video_url") or "").strip()
    if not video_ref:
        raise LocalUtilityRunError("Video Last Frame requires a video asset or connected upstream video output.")

    settings = get_settings()
    source_asset = find_asset(project, video_ref)
    source_path, cleanup_path = await resolve_video_to_local_path(video_ref, source_asset, settings.upload_dir)

    output_format = normalize_output_format(inputs.get("output_format"))
    content_type = "image/jpeg" if output_format in {"jpg", "jpeg"} else "image/png"
    suffix = "jpg" if output_format == "jpeg" else output_format
    output_filename = f"{uuid4().hex}-last-frame.{suffix}"
    output_path = settings.upload_dir / output_filename

    try:
        await asyncio.to_thread(extract_last_frame, source_path, output_path)
    except Exception as exc:
        raise LocalUtilityRunError(f"Could not extract the last video frame: {exc}") from exc
    finally:
        if cleanup_path:
            cleanup_path.unlink(missing_ok=True)

    public_url = f"/uploads/{output_filename}"
    asset = Asset(
        kind=AssetKind.image,
        filename=output_filename,
        content_type=content_type,
        local_path=str(output_path),
        public_url=public_url,
        metadata={
            "utility": NodeType.video_last_frame.value,
            "source_video": video_ref,
            "output_format": output_format,
        },
    )
    asset.lineage.created_by = "local_utility"
    asset.lineage.source_node_id = target_node.id if target_node else None
    asset.lineage.source_artifact_ids = [source_asset.id] if source_asset else []
    asset.view.role = ArtifactRole.output

    raw_output = {
        "utility": NodeType.video_last_frame.value,
        "output_url": public_url,
        "source_video": video_ref,
        "source_asset_id": source_asset.id if source_asset else None,
    }
    return raw_output, [public_url], [asset]


async def run_stitch_video(
    *,
    inputs: dict[str, Any],
    project: Project | None,
    target_node: CanvasNode | None,
) -> tuple[dict[str, Any], list[str], list[Asset]]:
    video_refs = parse_video_refs(inputs)
    if len(video_refs) < 2:
        raise LocalUtilityRunError("Stitch Videos requires at least two video inputs.")

    settings = get_settings()
    source_paths: list[Path] = []
    cleanup_paths: list[Path] = []
    source_asset_ids: list[str] = []
    for video_ref in video_refs:
        source_asset = find_asset(project, video_ref)
        source_path, cleanup_path = await resolve_video_to_local_path(video_ref, source_asset, settings.upload_dir)
        source_paths.append(source_path)
        if cleanup_path:
            cleanup_paths.append(cleanup_path)
        if source_asset:
            source_asset_ids.append(source_asset.id)

    resolution = normalize_resolution(inputs.get("resolution"))
    fps = normalize_fps(inputs.get("fps"))
    output_filename = f"{uuid4().hex}-stitched.mp4"
    output_path = settings.upload_dir / output_filename

    try:
        await asyncio.to_thread(stitch_videos, source_paths, output_path, resolution, fps)
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise LocalUtilityRunError(f"Could not stitch videos: {exc}") from exc
    finally:
        for cleanup_path in cleanup_paths:
            cleanup_path.unlink(missing_ok=True)

    public_url = f"/uploads/{output_filename}"
    asset = Asset(
        kind=AssetKind.video,
        filename=output_filename,
        content_type="video/mp4",
        local_path=str(output_path),
        public_url=public_url,
        metadata={
            "utility": NodeType.stitch_video.value,
            "source_videos": video_refs,
            "resolution": resolution,
            "fps": fps,
            "audio_note": "Audio is omitted by the local stitch utility.",
        },
    )
    asset.lineage.created_by = "local_utility"
    asset.lineage.source_node_id = target_node.id if target_node else None
    asset.lineage.source_artifact_ids = source_asset_ids
    asset.view.role = ArtifactRole.output

    raw_output = {
        "utility": NodeType.stitch_video.value,
        "output_url": public_url,
        "source_videos": video_refs,
        "source_asset_ids": source_asset_ids,
        "resolution": resolution,
        "fps": fps,
    }
    return raw_output, [public_url], [asset]


def parse_video_refs(inputs: dict[str, Any]) -> list[str]:
    raw_value = inputs.get("videos") or inputs.get("video") or inputs.get("video_urls") or []
    if isinstance(raw_value, list):
        items = raw_value
    else:
        items = str(raw_value).replace(",", "\n").splitlines()
    return [str(item).strip() for item in items if str(item).strip()]


async def resolve_video_to_local_path(
    video_ref: str,
    source_asset: Asset | None,
    upload_dir: Path,
) -> tuple[Path, Path | None]:
    if source_asset:
        if source_asset.kind != AssetKind.video:
            raise LocalUtilityRunError(f"Expected a video asset, got {source_asset.kind.value}.")
        if source_asset.local_path:
            path = Path(source_asset.local_path)
            if path.exists():
                return path, None
        if source_asset.public_url:
            video_ref = source_asset.public_url
        elif source_asset.wavespeed_url:
            video_ref = source_asset.wavespeed_url
        else:
            raise LocalUtilityRunError("Selected video asset has no local file path or readable URL.")

    local_upload = local_upload_path(video_ref, upload_dir)
    if local_upload and local_upload.exists():
        return local_upload, None

    path = Path(video_ref)
    if path.exists():
        return path, None

    if is_http_url(video_ref):
        downloaded = await download_video(video_ref, upload_dir)
        return downloaded, downloaded

    raise LocalUtilityRunError("Video input must be a project video asset, public video URL, or existing local file path.")


def local_upload_path(value: str, upload_dir: Path) -> Path | None:
    normalized = value.replace("\\", "/")
    marker = "/uploads/"
    if marker not in normalized:
        return None
    return upload_dir / normalized.rsplit(marker, 1)[-1]


async def download_video(url: str, upload_dir: Path) -> Path:
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    suffix = Path(httpx.URL(url).path).suffix or ".mp4"
    destination = upload_dir / f"{uuid4().hex}-source-video{suffix}"
    total_bytes = 0
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if content_type and not content_type.startswith(("video/", "application/octet-stream")):
                    raise LocalUtilityRunError(f"Expected a video URL, got content type {content_type}.")
                with destination.open("wb") as output:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        total_bytes += len(chunk)
                        if total_bytes > max_bytes:
                            raise LocalUtilityRunError(f"Video download exceeds {settings.max_upload_mb} MB.")
                        output.write(chunk)
        return destination
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def normalize_output_format(value: Any) -> str:
    output_format = str(value or "png").strip().lower()
    if output_format not in {"png", "jpg", "jpeg"}:
        raise LocalUtilityRunError("output_format must be png, jpg, or jpeg.")
    return output_format


def normalize_resolution(value: Any) -> str:
    resolution = str(value or "720p").strip().lower()
    if resolution not in {"720p", "1080p"}:
        raise LocalUtilityRunError("resolution must be 720p or 1080p.")
    return resolution


def normalize_fps(value: Any) -> int:
    if value in (None, ""):
        return 24
    try:
        fps = int(value)
    except (TypeError, ValueError) as exc:
        raise LocalUtilityRunError(f"fps must be an integer, got {value!r}.") from exc
    if fps < 1 or fps > 60:
        raise LocalUtilityRunError("fps must be between 1 and 60.")
    return fps


def extract_last_frame(video_path: Path, output_path: Path) -> None:
    reader = imageio.get_reader(str(video_path))
    last_frame = None
    try:
        for frame in reader:
            last_frame = frame
    finally:
        reader.close()
    if last_frame is None:
        raise LocalUtilityRunError("The video did not contain readable frames.")
    imageio.imwrite(str(output_path), last_frame)


def stitch_videos(video_paths: list[Path], output_path: Path, resolution: str, fps: int) -> None:
    width, height = {"720p": (1280, 720), "1080p": (1920, 1080)}[resolution]
    inputs: list[str] = []
    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for index, path in enumerate(video_paths):
        inputs.extend(["-i", str(path)])
        filter_parts.append(
            f"[{index}:v:0]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{index}]"
        )
        concat_inputs.append(f"[v{index}]")
    filter_complex = ";".join(filter_parts + [f"{''.join(concat_inputs)}concat=n={len(video_paths)}:v=1:a=0[outv]"])
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-an",
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "ffmpeg failed").strip().splitlines()[-1]
        raise LocalUtilityRunError(message)
