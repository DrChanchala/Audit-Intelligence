"""Inspection photo evidence.

* Only real JPEG/PNG/WebP images are accepted (checked by magic bytes, not by
  the client-supplied filename or content type), capped at MAX_UPLOAD_MB.
* Files are never served from /static. They are read back through
  ``/api/evidence/{allocation_id}/{name}``, which re-checks tenant access.
* Storage: a local directory (mount a Railway volume at UPLOAD_DIR; the
  container filesystem is wiped on every deploy) or a *private* Supabase
  bucket, read via short-lived signed URLs.
"""
from __future__ import annotations

import base64
import binascii
import re
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import NotFound, ValidationFailed

_SIGNATURES = (
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
)
_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+\.(jpg|png|webp)$")
CONTENT_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def sniff(data: bytes) -> tuple[str, str]:
    for sig, ext, ctype in _SIGNATURES:
        if data.startswith(sig):
            return ext, ctype
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    raise ValidationFailed("Only JPEG, PNG or WebP images are accepted.")


def decode_data_url(data_url: str) -> bytes:
    payload = data_url.split(",", 1)[1] if "," in data_url else data_url
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationFailed("Invalid image data.") from exc


def _supabase():
    s = get_settings()
    if not (s.supabase_url and s.supabase_service_key):
        return None
    from supabase import create_client

    return create_client(s.supabase_url, s.supabase_service_key)


def store(allocation_id: str, data: bytes) -> str:
    s = get_settings()
    if not data:
        raise ValidationFailed("Empty upload.")
    if len(data) > s.max_upload_bytes:
        raise ValidationFailed(f"Image exceeds {s.max_upload_bytes // (1024 * 1024)} MB limit.")
    ext, ctype = sniff(data)
    name = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:10]}.{ext}"
    client = _supabase()
    if client:
        client.storage.from_(s.supabase_bucket).upload(
            path=f"{allocation_id}/{name}", file=data, file_options={"content-type": ctype})
    else:
        folder = s.upload_dir / allocation_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(data)
    return f"/api/evidence/{allocation_id}/{name}"


def resolve(allocation_id: str, name: str) -> tuple[str, Path | str]:
    """Returns ('file', path) or ('redirect', signed_url)."""
    if not _NAME_RE.match(name) or "/" in allocation_id or ".." in allocation_id:
        raise NotFound("Evidence not found.")
    s = get_settings()
    client = _supabase()
    if client:
        signed = client.storage.from_(s.supabase_bucket).create_signed_url(f"{allocation_id}/{name}", 300)
        url = signed.get("signedURL") or signed.get("signedUrl")
        if not url:
            raise NotFound("Evidence not found.")
        return "redirect", url
    path = (s.upload_dir / allocation_id / name).resolve()
    if s.upload_dir.resolve() not in path.parents or not path.is_file():
        raise NotFound("Evidence not found.")
    return "file", path
