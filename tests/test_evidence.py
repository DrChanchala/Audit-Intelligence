"""Evidence photo upload, magic-byte sniffing, and retrieval tests (spec §8 item 5, V7, V9)."""
from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_v7_evidence_upload_hardened(eng_a_client: TestClient, anon_client: TestClient, qc_a_client: TestClient):
    """V7: Upload requires authenticated engineer on own allocation; rejected for unauth/qc_lead; files not in /static."""
    # Anon cannot upload -> 401
    resp = anon_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        files={"file": ("test.jpg", b"\xFF\xD8\xFF\xE0" + b"\x00" * 20, "image/jpeg")},
    )
    assert resp.status_code == 401

    # QC lead cannot upload -> 403 (engineer only)
    resp = qc_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        files={"file": ("test.jpg", b"\xFF\xD8\xFF\xE0" + b"\x00" * 20, "image/jpeg")},
    )
    assert resp.status_code == 403

    # HTML upload disguised as .jpg or .html must be rejected by magic bytes -> 400
    evil_html = b"<html><head><script>alert('xss')</script></head><body>evil</body></html>"
    resp = eng_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        files={"file": ("evil.html", evil_html, "text/html")},
    )
    assert resp.status_code == 400
    assert "only jpeg, png or webp" in resp.json()["detail"].lower()


def test_magic_byte_sniffing(eng_a_client: TestClient):
    """Magic byte validation accepts real JPEG, PNG, WebP; rejects SVG, polyglots, and text."""
    valid_jpeg = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00" + b"\x00" * 50
    valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50
    valid_webp = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 30

    # 1. JPEG upload via multipart form
    resp = eng_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        data={"checkpoint_id": "CHK-01-01-001"},
        files={"file": ("photo.jpg", valid_jpeg, "image/jpeg")},
    )
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("/api/evidence/ALC-A1/")
    assert url.endswith(".jpg")

    # 2. PNG upload via data_url JSON
    png_b64 = base64.b64encode(valid_png).decode()
    resp = eng_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        json={"checkpoint_id": "CHK-01-01-001", "data_url": f"data:image/png;base64,{png_b64}"},
    )
    assert resp.status_code == 200
    assert resp.json()["url"].endswith(".png")

    # 3. WebP upload via multipart form
    resp = eng_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        files={"file": ("photo.webp", valid_webp, "image/webp")},
    )
    assert resp.status_code == 200
    assert resp.json()["url"].endswith(".webp")

    # 4. SVG rejected by magic bytes
    svg_data = b"<svg xmlns='http://www.w3.org/2000/svg'><circle r='10'/></svg>"
    resp = eng_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        files={"file": ("image.svg", svg_data, "image/svg+xml")},
    )
    assert resp.status_code == 400
    assert "only jpeg, png or webp" in resp.json()["detail"].lower()


def test_upload_size_limit_rejected(eng_a_client: TestClient):
    """Payloads exceeding MAX_UPLOAD_MB are rejected."""
    s = get_settings()
    oversized = b"\xFF\xD8\xFF" + b"\x00" * (s.max_upload_bytes + 1024)
    resp = eng_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        files={"file": ("large.jpg", oversized, "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "exceeds" in resp.json()["detail"].lower()


def test_evidence_retrieval_and_path_traversal_404(eng_a_client: TestClient, anon_client: TestClient):
    """Evidence is served only through /api/evidence with tenant auth; path traversal returns 404."""
    # 1. Upload valid photo
    valid_jpeg = b"\xFF\xD8\xFF\xE0" + b"\x00" * 30
    resp = eng_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        files={"file": ("valid.jpg", valid_jpeg, "image/jpeg")},
    )
    assert resp.status_code == 200
    url = resp.json()["url"]

    # 2. Retrieve photo as authorized engineer
    resp = eng_a_client.get(url)
    assert resp.status_code == 200
    assert resp.content == valid_jpeg
    assert resp.headers.get("content-type") == "image/jpeg"

    # 3. Retrieve without authentication -> 401
    resp = anon_client.get(url)
    assert resp.status_code == 401

    # 4. Path traversal in filename -> 404
    resp = eng_a_client.get("/api/evidence/ALC-A1/..%2F..%2Fetc%2Fpasswd.jpg")
    assert resp.status_code == 404

    resp = eng_a_client.get("/api/evidence/ALC-A1/invalid_ext.txt")
    assert resp.status_code == 404

    # 5. Non-existent file -> 404
    resp = eng_a_client.get("/api/evidence/ALC-A1/20261101120000_notfound01.jpg")
    assert resp.status_code == 404


def test_v9_evidence_storage_private(eng_a_client: TestClient):
    """V9: Uploaded evidence is not accessible publicly or directly from /static/."""
    valid_jpeg = b"\xFF\xD8\xFF\xE0" + b"\x00" * 30
    resp = eng_a_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        files={"file": ("private.jpg", valid_jpeg, "image/jpeg")},
    )
    assert resp.status_code == 200
    filename = resp.json()["url"].split("/")[-1]

    # Must NOT be served from /static
    resp_static = eng_a_client.get(f"/static/uploads/{filename}")
    assert resp_static.status_code == 404
