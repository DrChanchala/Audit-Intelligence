"""API response contracts test suite (spec §8 item 7).

Asserts that endpoint response keys match or are a superset of the legacy API response shapes
(from archive/legacy-backend/app_audit.py and allocation_service.py), ensuring backwards
compatibility for all existing frontend components.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD


def test_auth_login_contract(anon_client: TestClient):
    """POST /api/auth/login contract shape."""
    resp = anon_client.post("/api/auth/login", json={"email": "admin@alpha.com", "password": PASSWORD})
    assert resp.status_code == 200
    data = resp.json()
    assert {"status", "message", "access_token", "token_type", "user", "organization", "home"}.issubset(data.keys())
    assert {"id", "email", "full_name", "role", "org_id"}.issubset(data["user"].keys())


def test_auth_me_contract(admin_a_client: TestClient):
    """GET /api/auth/me contract shape."""
    resp = admin_a_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert {"status", "user", "organization", "home"}.issubset(data.keys())
    assert {"id", "email", "full_name", "role", "org_id"}.issubset(data["user"].keys())


def test_admin_overview_contract(admin_a_client: TestClient):
    """GET /api/admin/overview contract shape."""
    resp = admin_a_client.get("/api/admin/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert {"status", "kpis"}.issubset(data.keys())
    assert {"projects", "live_projects", "active_inspections"}.issubset(data["kpis"].keys())


def test_projects_contract(admin_a_client: TestClient):
    """GET /api/projects contract shape (legacy returns a JSON list of project dicts)."""
    resp = admin_a_client.get("/api/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert isinstance(projects, list)
    assert len(projects) > 0
    p = projects[0]
    assert {"id", "code", "name", "type", "status", "loc", "geo", "progress"}.issubset(p.keys())


def test_summary_contract(qc_a_client: TestClient):
    """GET /api/summary contract shape (legacy returns KPI dictionary)."""
    resp = qc_a_client.get("/api/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert {
        "critical_open_ncs",
        "pending_approvals",
        "overdue_items",
        "overdue_ncs",
        "overdue_inspections",
        "engineer_loads",
    }.issubset(data.keys())


def test_ncs_contract(qc_a_client: TestClient):
    """GET /api/ncs and /api/ncs/{code} contract shapes (legacy returns a list of dicts)."""
    resp = qc_a_client.get("/api/ncs")
    assert resp.status_code == 200
    ncs = resp.json()
    assert isinstance(ncs, list)
    assert len(ncs) > 0
    nc = ncs[0]
    assert {"code", "title", "sev", "status", "project_id", "zone", "trade", "assigned", "due_date"}.issubset(nc.keys())

    # Single NC detail
    code = nc["code"]
    detail_resp = qc_a_client.get(f"/api/ncs/{code}")
    assert detail_resp.status_code == 200
    detail_nc = detail_resp.json()
    assert {"code", "title", "sev", "status"}.issubset(detail_nc.keys())


def test_approvals_contract(qc_a_client: TestClient):
    """GET /api/approvals contract shape (legacy returns a list of approval dicts)."""
    resp = qc_a_client.get("/api/approvals")
    assert resp.status_code == 200
    approvals = resp.json()
    assert isinstance(approvals, list)
    assert len(approvals) > 0
    ap = approvals[0]
    assert {"code", "project_id", "kind", "title", "by_user", "status"}.issubset(ap.keys())


def test_inspections_contract(qc_a_client: TestClient):
    """GET /api/inspections contract shape (legacy returns a list of inspection dicts)."""
    resp = qc_a_client.get("/api/inspections")
    assert resp.status_code == 200
    inspections = resp.json()
    assert isinstance(inspections, list)
    assert len(inspections) > 0
    ins = inspections[0]
    assert {"code", "project_id", "title", "status", "zone", "tpl", "due_date"}.issubset(ins.keys())


def test_engineers_contract(qc_a_client: TestClient):
    """GET /api/engineers contract shape (must match legacy registry shape)."""
    resp = qc_a_client.get("/api/engineers")
    assert resp.status_code == 200
    data = resp.json()
    assert {"status", "engineers"}.issubset(data.keys())
    assert len(data["engineers"]) > 0
    eng = data["engineers"][0]
    assert {"id", "name", "specialty"}.issubset(eng.keys())


def test_allocations_contract(qc_a_client: TestClient):
    """GET /api/allocations and GET /api/allocations/{id} contract shapes."""
    resp = qc_a_client.get("/api/allocations")
    assert resp.status_code == 200
    data = resp.json()
    assert {"status", "allocations"}.issubset(data.keys())
    assert len(data["allocations"]) > 0
    alloc = data["allocations"][0]
    assert {"allocation_id", "project_id", "engineer_name", "status"}.issubset(alloc.keys())

    # Detail contract
    aid = alloc["allocation_id"]
    detail_resp = qc_a_client.get(f"/api/allocations/{aid}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert {"status", "allocation"}.issubset(detail_data.keys())
    alloc_obj = detail_data["allocation"]
    assert {"allocation_id", "project_id", "engineer_id", "engineer_name", "status", "checkpoints"}.issubset(alloc_obj.keys())
    assert len(alloc_obj["checkpoints"]) > 0
    chk = alloc_obj["checkpoints"][0]
    assert {"checkpoint_id", "result_status", "checkpoint_text_snapshot"}.issubset(chk.keys())


def test_engineer_dashboard_contract(eng_a_client: TestClient):
    """GET /api/engineer/me/dashboard contract shape (matches legacy get_engineer_dashboard_data)."""
    resp = eng_a_client.get("/api/engineer/me/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert {"status", "engineer", "metrics", "inspections", "total_assigned", "filtered_count"}.issubset(data.keys())
    assert {"id", "name", "role", "specialty"}.issubset(data["engineer"].keys())
    assert {"allocated", "in_progress", "due_today", "overdue", "submitted"}.issubset(data["metrics"].keys())
