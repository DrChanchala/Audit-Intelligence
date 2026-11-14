"""Inspection allocation lifecycle test suite (spec §8 item 4, V11).

Tests:
- Creation validations: engineer in org, unknown checkpoint, hold/completed project, due < planned, duplicate 409.
- Draft creation -> activation.
- Save progress: NC without remarks 400, foreign photo URL 400.
- Submit: blocked when pending checkpoints remain; submit -> status 'Pending review' & approval queued.
- Review: approve only from 'Pending review'; return requires comments; status transitions correctly.
- Reassign: requires non-empty reason.
- Lock after 'Report issued': findings cannot be modified.
- V11: Audit trail identity is taken strictly from session principal (p.actor), ignoring request body spoofs.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.connection import get_database


def test_create_allocation_validations(qc_a_client: TestClient):
    """Validation checks on allocation creation."""
    today = "2026-11-01"
    yesterday = "2026-10-31"
    tomorrow = "2026-11-02"

    # 1. Foreign engineer (engineer from Org B) -> 404
    resp = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "engineer_id": "usr-eng-b",
            "planned_date": today,
            "due_date": tomorrow,
            "checkpoint_ids": ["CHK-01-01-001"],
        },
    )
    assert resp.status_code == 404
    assert "engineer not found" in resp.json()["detail"].lower()

    # 2. Unknown checkpoint ID -> 400
    resp = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "engineer_id": "usr-eng-a",
            "planned_date": today,
            "due_date": tomorrow,
            "checkpoint_ids": ["CHK-INVALID-9999"],
        },
    )
    assert resp.status_code == 400
    assert "unknown checkpoint" in resp.json()["detail"].lower()

    # 3. Due date before planned date -> 400
    resp = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "engineer_id": "usr-eng-a",
            "planned_date": today,
            "due_date": yesterday,
            "checkpoint_ids": ["CHK-01-01-001"],
        },
    )
    assert resp.status_code == 400
    assert "cannot precede" in resp.json()["detail"].lower()

    # 4. Hold project -> 400
    db = get_database()
    with db.session() as s:
        s.execute("UPDATE projects SET status = 'hold', hold_reason = 'Safety audit ongoing' WHERE id = 'prj-a1'")

    resp = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "engineer_id": "usr-eng-a",
            "planned_date": today,
            "due_date": tomorrow,
            "checkpoint_ids": ["CHK-01-01-001"],
        },
    )
    assert resp.status_code == 400
    assert "hold" in resp.json()["detail"].lower()

    # Reset project back to live
    with db.session() as s:
        s.execute("UPDATE projects SET status = 'live', hold_reason = NULL WHERE id = 'prj-a1'")

    # 5. Completed project -> 400
    with db.session() as s:
        s.execute("UPDATE projects SET status = 'completed' WHERE id = 'prj-a1'")

    resp = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "engineer_id": "usr-eng-a",
            "planned_date": today,
            "due_date": tomorrow,
            "checkpoint_ids": ["CHK-01-01-001"],
        },
    )
    assert resp.status_code == 400
    assert "completed" in resp.json()["detail"].lower()

    # Reset project back to live
    with db.session() as s:
        s.execute("UPDATE projects SET status = 'live' WHERE id = 'prj-a1'")


def test_create_and_duplicate_prevention(qc_a_client: TestClient):
    """Creating an allocation and checking duplicate prevention 409."""
    payload = {
        "project_id": "prj-a1",
        "engineer_id": "usr-eng-a",
        "tower_block": "Tower C",
        "floor_level": "Floor 2",
        "zone_area": "Zone X",
        "planned_date": "2026-11-01",
        "due_date": "2026-11-15",
        "checkpoint_ids": ["CHK-01-01-001", "CHK-01-01-002"],
        "allow_duplicate": False,
    }
    resp1 = qc_a_client.post("/api/allocations", json=payload)
    assert resp1.status_code == 200

    # Duplicate call with allow_duplicate=False -> 409
    resp2 = qc_a_client.post("/api/allocations", json=payload)
    assert resp2.status_code == 409
    assert "duplicate allocation prevented" in resp2.json()["detail"].lower()

    # With allow_duplicate=True -> 200
    payload["allow_duplicate"] = True
    resp3 = qc_a_client.post("/api/allocations", json=payload)
    assert resp3.status_code == 200


def test_draft_to_active_lifecycle(qc_a_client: TestClient):
    """Create draft allocation, then activate it with full scope."""
    # Create draft
    resp = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "status": "Draft",
            "tower_block": "Draft Tower",
        },
    )
    assert resp.status_code == 200
    alloc_id = resp.json()["allocation_id"]
    assert resp.json()["status"] == "Draft"

    # Activate draft
    resp_act = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "inspection_id": alloc_id,
            "status": "Allocated",
            "engineer_id": "usr-eng-a",
            "tower_block": "Draft Tower",
            "checkpoint_ids": ["CHK-01-01-001"],
        },
    )
    assert resp_act.status_code == 200
    assert resp_act.json()["status"] == "Allocated"


@pytest.fixture
def lifecycle_alloc_id(qc_a_client: TestClient) -> str:
    resp = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "engineer_id": "usr-eng-a",
            "tower_block": "Lifecycle Tower",
            "floor_level": "Floor 9",
            "zone_area": "Zone Lifecycle",
            "planned_date": "2026-11-01",
            "due_date": "2026-11-15",
            "checkpoint_ids": ["CHK-01-01-001", "CHK-01-01-002", "CHK-01-01-003"],
            "allow_duplicate": True,
        },
    )
    assert resp.status_code == 200
    return resp.json()["allocation_id"]


def test_save_progress_validation(eng_a_client: TestClient, lifecycle_alloc_id: str):
    """Save progress rejects NC/NA without observations and foreign photo URLs."""
    aid = lifecycle_alloc_id
    # NC without remarks -> 400
    resp = eng_a_client.post(
        f"/api/allocations/{aid}/save-progress",
        json={"checkpoints": [{"checkpoint_id": "CHK-01-01-001", "result_status": "NC", "observations": ""}]},
    )
    assert resp.status_code == 400
    assert "remarks are mandatory" in resp.json()["detail"].lower()

    # NA without justification -> 400
    resp = eng_a_client.post(
        f"/api/allocations/{aid}/save-progress",
        json={"checkpoints": [{"checkpoint_id": "CHK-01-01-001", "result_status": "NA", "observations": "   "}]},
    )
    assert resp.status_code == 400
    assert "justification is mandatory" in resp.json()["detail"].lower()

    # Foreign photo URL -> 400
    resp = eng_a_client.post(
        f"/api/allocations/{aid}/save-progress",
        json={
            "checkpoints": [
                {
                    "checkpoint_id": "CHK-01-01-001",
                    "result_status": "OK",
                    "evidence_photo_url": "https://malicious-site.com/evil.jpg",
                }
            ]
        },
    )
    assert resp.status_code == 400
    assert "evidence must be uploaded" in resp.json()["detail"].lower()


def test_submit_and_review_lifecycle(eng_a_client: TestClient, qc_a_client: TestClient, lifecycle_alloc_id: str):
    """Full progression: save progress -> submit -> review return -> resubmit -> review approve -> locked."""
    aid = lifecycle_alloc_id
    # 1. Submit blocked while checkpoints are pending -> 400
    resp = eng_a_client.post(f"/api/allocations/{aid}/submit", json={})
    assert resp.status_code == 400
    assert "remain pending" in resp.json()["detail"].lower()

    # 2. Complete all 3 checkpoints on the allocation
    resp = eng_a_client.post(
        f"/api/allocations/{aid}/save-progress",
        json={
            "checkpoints": [
                {"checkpoint_id": "CHK-01-01-001", "result_status": "OK", "observations": "Compaction verified 98%"},
                {"checkpoint_id": "CHK-01-01-002", "result_status": "NC", "observations": "Shoring needs strut repair", "evidence_photo_url": f"/api/evidence/{aid}/shoring.jpg"},
                {"checkpoint_id": "CHK-01-01-003", "result_status": "NA", "observations": "No water table encountered"},
            ]
        },
    )
    assert resp.status_code == 200

    # 3. Submit for review -> 200, status becomes "Pending review"
    resp = eng_a_client.post(f"/api/allocations/{aid}/submit", json={"notes": "All checks finished"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_status"] == "Pending review"
    assert "approval_code" in data

    # 4. Review: return requires comments -> 400
    resp = qc_a_client.post(f"/api/allocations/{aid}/review", json={"decision": "return", "comments": "  "})
    assert resp.status_code == 400
    assert "mandatory" in resp.json()["detail"].lower()

    # 5. Review: return with comments -> status 'In progress'
    resp = qc_a_client.post(f"/api/allocations/{aid}/review", json={"decision": "return", "comments": "Please re-inspect strut"})
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "In progress"

    # 6. Re-submit
    resp = eng_a_client.post(f"/api/allocations/{aid}/submit", json={"notes": "Strut repaired and re-checked"})
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "Pending review"

    # 7. Review: approve -> status 'Report issued'
    resp = qc_a_client.post(f"/api/allocations/{aid}/review", json={"decision": "approve"})
    assert resp.status_code == 200
    assert resp.json()["new_status"] == "Report issued"

    # 8. Locked after Report issued: editing findings -> 400
    resp = eng_a_client.post(
        f"/api/allocations/{aid}/save-progress",
        json={"checkpoints": [{"checkpoint_id": "CHK-01-01-001", "result_status": "OK"}]},
    )
    assert resp.status_code == 400
    assert "cannot be edited" in resp.json()["detail"].lower()


def test_reassign_validation(qc_a_client: TestClient, lifecycle_alloc_id: str):
    """Reassign requires reason and valid engineer."""
    aid = lifecycle_alloc_id
    # Blank reason -> 400
    resp = qc_a_client.post(
        f"/api/allocations/{aid}/reassign",
        json={"engineer_id": "usr-eng-a2", "reason": "   "},
    )
    assert resp.status_code == 400
    assert "reason is mandatory" in resp.json()["detail"].lower()

    # Valid reassignment -> 200
    resp = qc_a_client.post(
        f"/api/allocations/{aid}/reassign",
        json={"engineer_id": "usr-eng-a2", "reason": "Shift handover to Emma"},
    )
    assert resp.status_code == 200
    assert resp.json()["new_engineer_id"] == "usr-eng-a2"


def test_v11_audit_trail_actor_pinned_to_session(qc_a_client: TestClient):
    """V11: Audit trail identity and allocated_by are pinned to session principal, not spoofable request bodies."""
    # Attempt to spoof allocated_by and actor in body
    resp = qc_a_client.post(
        "/api/allocations",
        json={
            "project_id": "prj-a1",
            "engineer_id": "usr-eng-a",
            "planned_date": "2026-11-01",
            "due_date": "2026-11-10",
            "checkpoint_ids": ["CHK-01-01-001"],
            "allocated_by": "Spoofed Superadmin (Hacker)",  # Should be ignored
            "actor_name": "Spoofed Superadmin (Hacker)",    # Should be ignored
        },
    )
    assert resp.status_code == 200
    alloc_id = resp.json()["allocation_id"]

    db = get_database()
    with db.session() as s:
        row = s.one("SELECT allocated_by FROM inspection_allocations WHERE allocation_id = ?", (alloc_id,))
        assert row["allocated_by"] == "Quentin QC (QC Lead)"
        assert "Spoofed" not in row["allocated_by"]

        audit_entry = s.one(
            "SELECT actor_name FROM inspection_audit_events WHERE allocation_id = ? ORDER BY event_id DESC LIMIT 1",
            (alloc_id,),
        )
        assert audit_entry["actor_name"] == "Quentin QC (QC Lead)"
        assert "Spoofed" not in audit_entry["actor_name"]
