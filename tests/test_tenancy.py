"""Multi-tenancy isolation tests (spec §4, §8 item 2, V3, V4).

Verifies:
- Org B users (each role) get 404 on Org A's resources (project, allocation, inspection, NC, approval, evidence, report).
- ?org_id= / body org_id overrides are ignored.
- Engineer A2 cannot see or act upon Engineer A1's allocation (own-only isolation).
- Cross-tenant requests return 404 (never 403) to prevent tenant existence probing.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_v3_org_user_leak(admin_b_client: TestClient, qc_b_client: TestClient):
    """V3: GET /api/auth/users?org_id=X must ignore query org_id and return only caller's org users."""
    for client in (admin_b_client, qc_b_client):
        resp = client.get("/api/auth/users?org_id=org-a")
        assert resp.status_code == 200
        data = resp.json()
        users = data.get("users", [])
        assert len(users) > 0
        for u in users:
            assert u["org_id"] == "org-b"
            assert "alpha" not in u["email"]


def test_v4_cross_tenant_project_write(admin_b_client: TestClient):
    """V4: POST /api/projects with body org_id must ignore body org_id and pin to session org."""
    resp = admin_b_client.post(
        "/api/projects",
        json={
            "name": "Project Injected",
            "loc": "Injected Site",
            "org_id": "org-a",  # Attempt to inject into Org A
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    )
    assert resp.status_code == 200
    proj = resp.json()["project"]
    assert proj["org_id"] == "org-b"


@pytest.mark.parametrize("client_fixture", ["admin_b_client", "qc_b_client"])
def test_cross_tenant_project_read_404(request, client_fixture: str):
    """Org B admin/qc lead accessing Org A project gets 404."""
    client: TestClient = request.getfixturevalue(client_fixture)
    resp = client.get("/api/projects/prj-a1")
    assert resp.status_code == 404


@pytest.mark.parametrize("client_fixture", ["admin_b_client", "qc_b_client", "eng_b_client"])
def test_cross_tenant_allocation_read_404(request, client_fixture: str):
    """Org B any role accessing Org A allocation gets 404."""
    client: TestClient = request.getfixturevalue(client_fixture)
    resp = client.get("/api/allocations/ALC-A1")
    assert resp.status_code == 404


@pytest.mark.parametrize("client_fixture", ["admin_b_client", "qc_b_client"])
def test_cross_tenant_inspection_read_404(request, client_fixture: str):
    """Org B admin/qc lead accessing Org A inspection gets 404."""
    client: TestClient = request.getfixturevalue(client_fixture)
    resp = client.get("/api/inspections/ALC-A1")
    assert resp.status_code == 404


@pytest.mark.parametrize("client_fixture", ["admin_b_client", "qc_b_client"])
def test_cross_tenant_nc_read_404(request, client_fixture: str):
    """Org B admin/qc lead accessing Org A non-conformity gets 404."""
    client: TestClient = request.getfixturevalue(client_fixture)
    resp = client.get("/api/ncs/NC-A1")
    assert resp.status_code == 404


def test_cross_tenant_nc_action_404(qc_b_client: TestClient):
    """Org B QC lead performing action on Org A NC gets 404."""
    resp = qc_b_client.post("/api/ncs/NC-A1/action", json={"action": "verify", "note": "Evil note"})
    assert resp.status_code == 404


def test_cross_tenant_approval_action_404(qc_b_client: TestClient):
    """Org B QC lead approving Org A approval gets 404."""
    resp = qc_b_client.post("/api/approvals/AP-A1/action", json={"action": "approve"})
    assert resp.status_code == 404


@pytest.mark.parametrize("client_fixture", ["admin_b_client", "qc_b_client"])
def test_cross_tenant_report_read_404(request, client_fixture: str):
    """Org B admin/qc lead accessing Org A report gets 404."""
    client: TestClient = request.getfixturevalue(client_fixture)
    resp = client.get("/api/inspections/ALC-A1/report")
    assert resp.status_code == 404


@pytest.mark.parametrize("client_fixture", ["admin_b_client", "qc_b_client", "eng_b_client"])
def test_cross_tenant_evidence_read_404(request, client_fixture: str):
    """Org B roles accessing Org A evidence get 404."""
    client: TestClient = request.getfixturevalue(client_fixture)
    resp = client.get("/api/evidence/ALC-A1/sample.jpg")
    assert resp.status_code == 404


def test_cross_tenant_qc_actions_404(qc_b_client: TestClient):
    """Org B QC lead performing mutation actions on Org A inspection gets 404."""
    resp = qc_b_client.post("/api/inspections/ALC-A1/nudge", json={})
    assert resp.status_code == 404

    resp = qc_b_client.post("/api/inspections/ALC-A1/status", json={"status": "In progress"})
    assert resp.status_code == 404

    resp = qc_b_client.post("/api/inspections/ALC-A1/change-engineer", json={"engineer_id": "usr-eng-b"})
    assert resp.status_code == 404

    resp = qc_b_client.post("/api/allocations/ALC-A1/reassign", json={"engineer_id": "usr-eng-b", "reason": "Test"})
    assert resp.status_code == 404


def test_engineer_cross_allocation_isolation(eng_a2_client: TestClient):
    """Engineer A2 cannot see or modify Engineer A1's allocation (own-only isolation in same org)."""
    # Read allocation
    resp = eng_a2_client.get("/api/allocations/ALC-A1")
    assert resp.status_code == 404

    # Checkpoint result
    resp = eng_a2_client.post(
        "/api/allocations/ALC-A1/checkpoint-result",
        json={"checkpoint_id": "CHK-01-01-001", "result_status": "OK"},
    )
    assert resp.status_code == 404

    # Save progress
    resp = eng_a2_client.post(
        "/api/allocations/ALC-A1/save-progress",
        json={"checkpoints": [{"checkpoint_id": "CHK-01-01-001", "result_status": "OK"}]},
    )
    assert resp.status_code == 404

    # Submit
    resp = eng_a2_client.post("/api/allocations/ALC-A1/submit", json={})
    assert resp.status_code == 404

    # Upload evidence
    resp = eng_a2_client.post(
        "/api/allocations/ALC-A1/upload-evidence",
        data={"checkpoint_id": "CHK-01-01-001"},
        files={"file": ("test.jpg", b"\xFF\xD8\xFF\xE0" + b"\x00" * 20, "image/jpeg")},
    )
    assert resp.status_code == 404

    # Engineer dashboard does not contain ALC-A1
    resp = eng_a2_client.get("/api/engineer/me/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    alloc_ids = [a["allocation_id"] for a in data.get("allocations", [])]
    assert "ALC-A1" not in alloc_ids
