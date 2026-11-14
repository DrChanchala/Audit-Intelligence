"""Access matrix test suite (spec §4 & §8 item 1).

Parametrises every §4 row × {anon, admin, qc_lead, engineer}.
Auto-enumerates app routes and FAILS if any /api route is missing from the matrix.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Complete matrix specification according to §4:
# (method, path_template, allowed_roles)
# allowed_roles: set of ('admin', 'qc_lead', 'engineer') or 'public' or 'gone'
MATRIX_SPEC = {
    ("POST", "/api/auth/login"): "public",
    ("POST", "/api/auth/register-org-admin"): "public",
    ("POST", "/api/auth/register"): "gone",
    ("GET", "/api/auth/organizations"): {"admin", "qc_lead", "engineer"},
    ("POST", "/api/auth/organizations"): "gone",
    ("POST", "/api/auth/logout"): {"admin", "qc_lead", "engineer"},
    ("GET", "/api/auth/me"): {"admin", "qc_lead", "engineer"},
    ("GET", "/api/auth/users"): {"admin", "qc_lead"},
    ("POST", "/api/auth/users"): {"admin", "qc_lead"},
    ("GET", "/api/admin/overview"): {"admin"},
    ("GET", "/api/projects"): {"admin", "qc_lead", "engineer"},
    ("POST", "/api/projects"): {"admin"},
    ("GET", "/api/projects/{project_id}"): {"admin", "qc_lead"},
    ("GET", "/api/summary"): {"admin", "qc_lead"},
    ("GET", "/api/ncs"): {"admin", "qc_lead"},
    ("GET", "/api/ncs/{code}"): {"admin", "qc_lead"},
    ("POST", "/api/ncs/{code}/action"): {"qc_lead"},
    ("GET", "/api/approvals"): {"admin", "qc_lead"},
    ("POST", "/api/approvals/{code}/action"): {"qc_lead"},
    ("GET", "/api/inspections"): {"admin", "qc_lead"},
    ("GET", "/api/inspections/next-id"): {"qc_lead"},
    ("GET", "/api/inspections/{code}"): {"admin", "qc_lead"},
    ("POST", "/api/inspections/create"): {"qc_lead"},
    ("POST", "/api/inspections/{code}/allocate"): {"qc_lead"},
    ("POST", "/api/inspections/{code}/nudge"): {"qc_lead"},
    ("POST", "/api/inspections/{code}/change-engineer"): {"qc_lead"},
    ("POST", "/api/inspections/{code}/status"): {"qc_lead"},
    ("POST", "/api/inspections/{code}/generate-report"): {"qc_lead"},
    ("GET", "/api/inspections/{code}/report"): {"admin", "qc_lead"},
    ("GET", "/api/master-checklist"): {"admin", "qc_lead"},
    ("GET", "/api/engineers"): {"admin", "qc_lead"},
    ("GET", "/api/allocations"): {"admin", "qc_lead"},
    ("POST", "/api/allocations"): {"qc_lead"},
    ("GET", "/api/allocations/{id}"): {"admin", "qc_lead", "engineer"},
    ("POST", "/api/allocations/{id}/checkpoint-result"): {"engineer"},
    ("POST", "/api/allocations/{id}/save-progress"): {"engineer"},
    ("POST", "/api/allocations/{id}/submit"): {"engineer"},
    ("POST", "/api/allocations/{id}/review"): {"qc_lead"},
    ("POST", "/api/allocations/{id}/reassign"): {"qc_lead"},
    ("GET", "/api/engineer/me/dashboard"): {"engineer"},
    ("GET", "/api/engineer/{id}/dashboard"): {"admin", "qc_lead", "engineer"},
    ("POST", "/api/allocations/{id}/upload-evidence"): {"engineer"},
    ("GET", "/api/evidence/{alloc}/{name}"): {"admin", "qc_lead", "engineer"},
    ("GET", "/api/health"): "public",
    ("POST", "/api/seed"): "gone",
}

# Concrete sample IDs to format path parameters
PARAMS = {
    "project_id": "prj-a1",
    "code": "ALC-A1",
    "id": "ALC-A1",
    "alloc": "ALC-A1",
    "name": "sample.jpg",
}


def test_routes_coverage():
    """Verify that every /api route in the FastAPI application is covered by the access matrix."""
    openapi = app.openapi()
    api_routes = []
    for path, methods in openapi["paths"].items():
        if path.startswith("/api"):
            for m in methods.keys():
                api_routes.append((m.upper(), path))

    missing = []
    for m, p in api_routes:
        if (m, p) not in MATRIX_SPEC:
            missing.append(f"{m} {p}")

    assert not missing, f"Missing routes in MATRIX_SPEC: {missing}"


@pytest.mark.parametrize(
    "method,path_tmpl,allowed",
    [(m, p, a) for (m, p), a in MATRIX_SPEC.items()],
)
def test_access_matrix_roles(
    method: str,
    path_tmpl: str,
    allowed,
    anon_client: TestClient,
    admin_a_client: TestClient,
    qc_a_client: TestClient,
    eng_a_client: TestClient,
):
    url = path_tmpl.format(**PARAMS)
    clients = {
        "anon": anon_client,
        "admin": admin_a_client,
        "qc_lead": qc_a_client,
        "engineer": eng_a_client,
    }

    dummy_body = {}
    if method == "POST":
        if "login" in url:
            dummy_body = {"email": "admin@alpha.com", "password": "Password123!"}
        elif "register-org-admin" in url:
            dummy_body = {
                "org_name": "Test Matrix Org",
                "admin_name": "Admin Test",
                "admin_email": "admin_matrix@test.com",
                "admin_password": "Password123!",
            }
        elif "users" in url:
            dummy_body = {
                "email": "matrix_new@test.com",
                "password": "Password123!",
                "full_name": "New User",
                "role": "engineer",
            }
        elif "projects" in url:
            dummy_body = {
                "name": "Matrix Project",
                "loc": "Site",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
            }
        elif "checkpoint-result" in url:
            dummy_body = {
                "checkpoint_id": "CHK-01-01-001",
                "result_status": "OK",
            }
        elif "save-progress" in url:
            dummy_body = {
                "checkpoints": [{"checkpoint_id": "CHK-01-01-001", "result_status": "OK"}]
            }
        elif "action" in url:
            dummy_body = {"action": "verify"}
        elif "review" in url:
            dummy_body = {"decision": "approve"}

    for role, client in clients.items():
        call = getattr(client, method.lower())
        kwargs = {}
        if method in ("POST", "PUT", "PATCH"):
            kwargs["json"] = dummy_body

        resp = call(url, **kwargs)

        if allowed == "public":
            # Public endpoint must not reject with 401 or 403
            assert resp.status_code not in (401, 403), f"{role} on {method} {url} returned {resp.status_code}"
        elif allowed == "gone":
            # Removed / disabled endpoint must return 410 Gone
            assert resp.status_code == 410, f"{role} on {method} {url} returned {resp.status_code}"
        elif role == "anon":
            # Anonymous on protected endpoint must return 401
            assert resp.status_code == 401, f"Anon on {method} {url} expected 401, got {resp.status_code}: {resp.text}"
        elif role in allowed:
            # Authorized role must not return 401 or 403
            assert resp.status_code not in (401, 403), f"{role} on {method} {url} unexpectedly forbidden: {resp.status_code}: {resp.text}"
        else:
            # Unauthorized role must return 403 Forbidden
            assert resp.status_code == 403, f"{role} on {method} {url} expected 403, got {resp.status_code}: {resp.text}"
