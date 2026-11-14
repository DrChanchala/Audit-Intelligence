"""Authentication, authorization, session hardening, and user provisioning tests (spec §4, §8 item 3, V1, V2, V6, V8)."""
from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import (
    CSRF_HEADER,
    SESSION_COOKIE,
    login_limiter,
)
from tests.conftest import PASSWORD


def test_v1_public_register_gone(anon_client: TestClient):
    """V1: POST /api/auth/register must be removed and return 410 Gone."""
    resp = anon_client.post(
        "/api/auth/register",
        json={"email": "attacker@evil.com", "password": "Password123!", "role": "admin", "org_id": "org-a"},
    )
    assert resp.status_code == 410
    assert "disabled" in resp.json()["detail"].lower()


def test_v2_org_enumeration_prevented(admin_a_client: TestClient, anon_client: TestClient):
    """V2: GET /api/auth/organizations must require auth and only return caller's own org, not all tenants."""
    # Anon cannot enumerate
    resp = anon_client.get("/api/auth/organizations")
    assert resp.status_code == 401

    # Admin of Org A only gets Org A
    resp = admin_a_client.get("/api/auth/organizations")
    assert resp.status_code == 200
    orgs = resp.json().get("organizations", [])
    assert len(orgs) == 1
    assert orgs[0]["id"] == "org-a"


def test_v6_forged_jwt_rejected(anon_client: TestClient):
    """V6: JWT signed with a forged or different secret must be rejected with 401."""
    now = int(time.time())
    forged_payload = {
        "sub": "usr-admin-a",
        "org_id": "org-a",
        "role": "admin",
        "email": "admin@alpha.com",
        "name": "Alice Admin",
        "iat": now,
        "exp": now + 3600,
        "jti": "fake-jti-12345",
    }
    forged_token = jwt.encode(forged_payload, "completely-wrong-forged-secret-key-1234567890", algorithm="HS256")

    # Bearer header
    resp = anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert resp.status_code == 401

    # Cookie
    anon_client.cookies.set(SESSION_COOKIE, forged_token)
    resp = anon_client.get("/api/auth/me")
    assert resp.status_code == 401
    anon_client.cookies.clear()


def test_v8_public_seed_gone(anon_client: TestClient):
    """V8: POST /api/seed must be removed and return 410 Gone."""
    resp = anon_client.post("/api/seed")
    assert resp.status_code == 410
    assert "disabled" in resp.json()["detail"].lower()


def test_signup_sets_cookie(anon_client: TestClient):
    """Self-registration of a new organization sets HttpOnly session cookie."""
    resp = anon_client.post(
        "/api/auth/register-org-admin",
        json={
            "org_name": "New Alpha Corp",
            "org_code": "NAC",
            "industry": "Commercial Construction",
            "admin_name": "Nathan Admin",
            "admin_email": "nathan@nacorp.com",
            "admin_password": "SecurePassword123!",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["role"] == "admin"
    assert data["organization"]["name"] == "New Alpha Corp"

    # Verify cookie attributes
    set_cookie = resp.headers.get("set-cookie", "")
    assert SESSION_COOKIE in set_cookie
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie
    assert "SameSite=lax" in set_cookie or "samesite=lax" in set_cookie


def test_login_wrong_password_401(anon_client: TestClient):
    """Login with invalid password returns 401."""
    resp = anon_client.post(
        "/api/auth/login",
        json={"email": "admin@alpha.com", "password": "WrongPassword123!"},
    )
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()


def test_login_unknown_email_401(anon_client: TestClient):
    """Login with unknown email returns 401 with generic message (constant-time)."""
    resp = anon_client.post(
        "/api/auth/login",
        json={"email": "nonexistent@alpha.com", "password": "Password123!"},
    )
    assert resp.status_code == 401
    assert "invalid email or password" in resp.json()["detail"].lower()


def test_login_org_mismatch_403(anon_client: TestClient):
    """Login with valid creds but mismatched org_id returns 403."""
    resp = anon_client.post(
        "/api/auth/login",
        json={"email": "admin@alpha.com", "password": PASSWORD, "org_id": "org-b"},
    )
    assert resp.status_code == 403
    assert "does not belong" in resp.json()["detail"].lower()


def test_expired_token_rejected_401(anon_client: TestClient):
    """Expired token returns 401."""
    s = get_settings()
    now = int(time.time())
    expired_payload = {
        "sub": "usr-admin-a",
        "org_id": "org-a",
        "role": "admin",
        "email": "admin@alpha.com",
        "name": "Alice Admin",
        "iat": now - 7200,
        "exp": now - 3600,  # Expired 1 hour ago
        "jti": "expired-jti-12345",
    }
    expired_token = jwt.encode(expired_payload, s.jwt_secret, algorithm="HS256")
    resp = anon_client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


def test_cookie_post_without_csrf_header_403(test_app):
    """Cookie session making an unsafe POST without CSRF header is rejected with 403."""
    from tests.conftest import USERS, _make_client
    client = _make_client(test_app, USERS["admin_a"])
    # Delete the default CSRF and Auth headers to test pure cookie auth
    del client.headers["X-SiteIQ-CSRF"]
    del client.headers["Authorization"]

    # Mutation without CSRF header -> 403
    resp = client.post("/api/projects", json={"name": "No CSRF", "loc": "Site", "start_date": "2026-01-01", "end_date": "2026-12-31"})
    assert resp.status_code == 403
    assert "csrf" in resp.json()["detail"].lower()

    # With CSRF header -> 200
    client.headers[CSRF_HEADER] = "1"
    resp = client.post("/api/projects", json={"name": "With CSRF", "loc": "Site", "start_date": "2026-01-01", "end_date": "2026-12-31"})
    assert resp.status_code == 200


def test_rate_limiter_429(anon_client: TestClient):
    """Rapid repeated login requests trigger 429 Too Many Requests."""
    login_limiter.reset()
    try:
        # Limit is 10/min
        for _ in range(10):
            anon_client.post("/api/auth/login", json={"email": "rate_test@test.com", "password": "wrong"})
        # 11th request must be rate limited
        resp = anon_client.post("/api/auth/login", json={"email": "rate_test@test.com", "password": "wrong"})
        assert resp.status_code == 429
        assert "too many" in resp.json()["detail"].lower()
    finally:
        login_limiter.reset()


def test_provisioning_rules(admin_a_client: TestClient, qc_a_client: TestClient):
    """Test user provisioning permissions and conflicts."""
    # Admin can provision qc_lead and engineer
    resp = admin_a_client.post(
        "/api/auth/users",
        json={"email": "new_qc@alpha.com", "password": "Password123!", "full_name": "New QC", "role": "qc_lead"},
    )
    assert resp.status_code == 200

    resp = admin_a_client.post(
        "/api/auth/users",
        json={"email": "new_eng@alpha.com", "password": "Password123!", "full_name": "New Eng", "role": "engineer"},
    )
    assert resp.status_code == 200

    # QC lead can provision engineer
    resp = qc_a_client.post(
        "/api/auth/users",
        json={"email": "qc_created_eng@alpha.com", "password": "Password123!", "full_name": "QC Eng", "role": "engineer"},
    )
    assert resp.status_code == 200

    # QC lead CANNOT provision admin or qc_lead
    resp = qc_a_client.post(
        "/api/auth/users",
        json={"email": "forbidden_admin@alpha.com", "password": "Password123!", "full_name": "Bad Admin", "role": "admin"},
    )
    assert resp.status_code == 403

    resp = qc_a_client.post(
        "/api/auth/users",
        json={"email": "forbidden_qc@alpha.com", "password": "Password123!", "full_name": "Bad QC", "role": "qc_lead"},
    )
    assert resp.status_code == 403

    # Duplicate email across system returns 409
    resp = admin_a_client.post(
        "/api/auth/users",
        json={"email": "admin@alpha.com", "password": "Password123!", "full_name": "Dupe", "role": "engineer"},
    )
    assert resp.status_code == 409

    # Duplicate employee ID in same org returns 409
    resp = admin_a_client.post(
        "/api/auth/users",
        json={"email": "unique1@alpha.com", "employee_id": "EMP-A-ADM", "password": "Password123!", "full_name": "Dupe Emp", "role": "engineer"},
    )
    assert resp.status_code == 409


def test_v5_unauthenticated_endpoints_blocked(anon_client: TestClient):
    """V5: Endpoints that previously lacked auth now reject unauthenticated access with 401."""
    protected_urls = [
        ("GET", "/api/projects"),
        ("GET", "/api/summary"),
        ("GET", "/api/ncs"),
        ("GET", "/api/approvals"),
        ("GET", "/api/inspections"),
        ("GET", "/api/allocations"),
        ("GET", "/api/master-checklist"),
        ("GET", "/api/engineers"),
        ("GET", "/api/projects/prj-a1"),
        ("GET", "/api/allocations/ALC-A1"),
        ("GET", "/api/inspections/ALC-A1"),
        ("GET", "/api/ncs/NC-A1"),
    ]
    for method, url in protected_urls:
        call = getattr(anon_client, method.lower())
        resp = call(url)
        assert resp.status_code == 401, f"{method} {url} expected 401, got {resp.status_code}"


def test_v10_stored_xss_sink_prevention(qc_a_client: TestClient):
    """V10: XSS payloads in input fields are stored safely without execution and validated."""
    payload = {
        "project_id": "prj-a1",
        "engineer_id": "usr-eng-a",
        "instructions": "<script>alert('xss')</script>",
        "tower_block": "Tower <img src=x onerror=alert(1)>",
        "planned_date": "2026-11-01",
        "due_date": "2026-11-15",
        "checkpoint_ids": ["CHK-01-01-001"],
        "allow_duplicate": True,
    }
    resp = qc_a_client.post("/api/allocations", json=payload)
    assert resp.status_code == 200
    alloc_id = resp.json()["allocation_id"]

    detail = qc_a_client.get(f"/api/allocations/{alloc_id}").json()["allocation"]
    # Check that it's treated strictly as literal string, not evaluated HTML
    assert detail["instructions"] == "<script>alert('xss')</script>"
    assert "<img src=x onerror=alert(1)>" in detail["tower_block"]


def test_v12_cors_and_error_sanitization(anon_client: TestClient):
    """V12: Wildcard CORS with credentials is forbidden; unhandled exceptions return sanitized 500 ref."""
    from app.core.config import Settings
    # Production settings reject wildcard CORS
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must not contain '\\*'"):
        Settings(
            env="production",
            jwt_secret="strong-secret-key-with-over-32-chars-for-test!!",
            database_url="postgresql://usr:pass@localhost:5432/db",
            cors_origins=("*",),
        ).validate()

    # Domain error returns structured JSON, not raw Python stacktrace
    resp = anon_client.post("/api/auth/login", json={"email": "not-an-email", "password": "x"})
    assert resp.status_code == 422
    data = resp.json()
    assert "errors" in data
    assert "detail" in data

