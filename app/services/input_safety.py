from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.core.config import get_settings


PRIVATE_HOSTNAMES = {"localhost", "localhost.localdomain"}


class InputSafetyError(ValueError):
    pass


def is_url_private_or_local(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        return False
    if host in PRIVATE_HOSTNAMES or host.endswith(".localhost"):
        return True
    if _is_blocked_ip(host):
        return True
    try:
        infos = socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)
    except OSError:
        return False
    return any(_is_blocked_ip(info[4][0]) for info in infos)


def safe_upload_path_from_reference(value: str, upload_dir: Path | None = None) -> Path | None:
    upload_dir = (upload_dir or get_settings().upload_dir).resolve()
    parsed = urlparse(value)
    path_value = parsed.path if parsed.scheme in {"http", "https"} else value
    normalized = unquote(path_value).replace("\\", "/")
    marker = "/uploads/"
    if normalized == "/uploads":
        raise InputSafetyError("Upload path must include a filename.")
    if marker not in normalized:
        return None
    relative = normalized.rsplit(marker, 1)[-1]
    if not relative or relative.startswith("/"):
        raise InputSafetyError("Upload path must include a filename.")
    candidate = (upload_dir / relative).resolve()
    if not is_relative_to(candidate, upload_dir):
        raise InputSafetyError("Upload path escapes the upload directory.")
    return candidate


def require_upload_contained_path(path: Path, upload_dir: Path | None = None) -> Path:
    upload_dir = (upload_dir or get_settings().upload_dir).resolve()
    resolved = path.resolve()
    if not is_relative_to(resolved, upload_dir):
        raise InputSafetyError("Local file paths must be uploaded project assets.")
    return resolved


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _is_blocked_ip(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    )
