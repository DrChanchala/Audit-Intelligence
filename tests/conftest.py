"""Test configuration, fixtures, seeded tenant data, and TestClient helpers."""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Configure environment before app imports
_TEMP_DIR = tempfile.mkdtemp(prefix="siteiq_test_")
_SQLITE_PATH = Path(_TEMP_DIR) / "test_audit.db"
_UPLOAD_DIR = Path(_TEMP_DIR) / "uploads"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_JWT_SECRET = "test-super-secret-jwt-key-for-siteiq-testing-32chars!"

os.environ["APP_ENV"] = "development"
if "DATABASE_URL" not in os.environ:
    os.environ["SQLITE_PATH"] = str(_SQLITE_PATH)
os.environ["UPLOAD_DIR"] = str(_UPLOAD_DIR)
os.environ["SITEIQ_JWT_SECRET"] = _JWT_SECRET

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.security import (
    SESSION_COOKIE,
    create_token,
    hash_password,
    login_limiter,
    signup_limiter,
)
from app.db.connection import get_database, reset_database
from app.db.schema import init_schema, load_master_checklist
from app.main import create_app

PASSWORD = "Password123!"
PASSWORD_HASH = hash_password(PASSWORD)


def _seed_test_database(db):
    with db.session() as s:
        init_schema(s)
        load_master_checklist(s)

        # Org A
        s.execute(
            "INSERT INTO organizations (id, name, code, industry) VALUES (?, ?, ?, ?)",
            ("org-a", "Org Alpha Ltd", "ALPHA", "Commercial Contracting"),
        )
        s.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("usr-admin-a", "org-a", "admin@alpha.com", PASSWORD_HASH, "Alice Admin", "admin", "EMP-A-ADM", "Admin"),
        )
        s.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("usr-qc-a", "org-a", "qc@alpha.com", PASSWORD_HASH, "Quentin QC", "qc_lead", "EMP-A-QC", "Quality"),
        )
        s.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("usr-eng-a", "org-a", "eng@alpha.com", PASSWORD_HASH, "Edward Engineer", "engineer", "EMP-A-ENG", "Civil"),
        )
        s.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("usr-eng-a2", "org-a", "eng2@alpha.com", PASSWORD_HASH, "Emma Engineer 2", "engineer", "EMP-A-ENG2", "Electrical"),
        )
        s.execute(
            "INSERT INTO projects (id, org_id, code, name, type, loc, geo, status, progress, start_date, end_date, upd_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'live', 25, '2026-01-01', '2026-12-31', ?)",
            ("prj-a1", "org-a", "PRJ-A1", "Project Alpha One", "Commercial", "Building 1", "Sector 1", "Alice Admin"),
        )
        s.execute(
            "INSERT INTO inspection_allocations (allocation_id, project_id, engineer_id, engineer_name, allocated_by, "
            "location_scope, planned_date, due_date, due_time, priority, status, linked_ins_code) "
            "VALUES (?, ?, ?, ?, ?, ?, '2026-11-01', '2026-11-10', '18:00', 'High', 'Allocated', ?)",
            ("ALC-A1", "prj-a1", "usr-eng-a", "Edward Engineer", "Quentin QC", "Tower A Floor 1", "ALC-A1"),
        )
        s.execute(
            "INSERT INTO inspections (code, project_id, title, zone, tpl, eng, due_date, status, items_count) "
            "VALUES (?, ?, 'Alpha Inspection 1', 'Tower A Floor 1', 'Substructure', 'Edward Engineer', '2026-11-10', 'Allocated', 3)",
            ("ALC-A1", "prj-a1"),
        )
        s.executemany(
            "INSERT INTO allocation_checkpoints (allocation_id, checkpoint_id, stage_id, subgroup_id, stage_name, "
            "subgroup_name, checkpoint_text_snapshot, priority, result_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')",
            [
                ("ALC-A1", "CHK-01-01-001", "STG-01", "SUB-01-01", "Substructure", "Excavation", "Soil compaction check", "H"),
                ("ALC-A1", "CHK-01-01-002", "STG-01", "SUB-01-01", "Substructure", "Excavation", "Shoring stability check", "M"),
                ("ALC-A1", "CHK-01-01-003", "STG-01", "SUB-01-01", "Substructure", "Excavation", "Dewatering drainage check", "L"),
            ],
        )
        s.execute(
            "INSERT INTO non_conformities (code, project_id, title, sev, zone, trade, assigned, raised_date, due_date, status, raised_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, '2026-11-01', ?, ?, ?)",
            ("NC-A1", "prj-a1", "Soil density below 95%", "critical", "Tower A Floor 1", "Earthworks", "Edward Engineer", "2026-11-05", "Open", "Quentin QC"),
        )
        s.execute(
            "INSERT INTO approvals (code, project_id, kind, title, by_user, at_time, ref_ins, status) "
            "VALUES (?, ?, 'Inspection report', ?, ?, '2026-11-04 10:00:00', ?, 'Pending')",
            ("AP-A1", "prj-a1", "Alpha Approval 1", "Edward Engineer", "ALC-A1"),
        )

        # Org B
        s.execute(
            "INSERT INTO organizations (id, name, code, industry) VALUES (?, ?, ?, ?)",
            ("org-b", "Org Beta Corp", "BETA", "Residential Contracting"),
        )
        s.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("usr-admin-b", "org-b", "admin@beta.com", PASSWORD_HASH, "Bob Admin", "admin", "EMP-B-ADM", "Admin"),
        )
        s.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("usr-qc-b", "org-b", "qc@beta.com", PASSWORD_HASH, "Queen QC", "qc_lead", "EMP-B-QC", "Quality"),
        )
        s.execute(
            "INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("usr-eng-b", "org-b", "eng@beta.com", PASSWORD_HASH, "Evan Engineer", "engineer", "EMP-B-ENG", "Structure"),
        )
        s.execute(
            "INSERT INTO projects (id, org_id, code, name, type, loc, geo, status, progress, start_date, end_date, upd_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'live', 10, '2026-02-01', '2026-11-30', ?)",
            ("prj-b1", "org-b", "PRJ-B1", "Project Beta One", "Residential", "Block B", "Sector 2", "Bob Admin"),
        )
        s.execute(
            "INSERT INTO inspection_allocations (allocation_id, project_id, engineer_id, engineer_name, allocated_by, "
            "location_scope, planned_date, due_date, due_time, priority, status, linked_ins_code) "
            "VALUES (?, ?, ?, ?, ?, ?, '2026-11-02', '2026-11-12', '18:00', 'High', 'Allocated', ?)",
            ("ALC-B1", "prj-b1", "usr-eng-b", "Evan Engineer", "Queen QC", "Block B Podium", "ALC-B1"),
        )
        s.execute(
            "INSERT INTO inspections (code, project_id, title, zone, tpl, eng, due_date, status, items_count) "
            "VALUES (?, ?, 'Beta Inspection 1', 'Block B Podium', 'Substructure', 'Evan Engineer', '2026-11-12', 'Allocated', 3)",
            ("ALC-B1", "prj-b1"),
        )
        s.executemany(
            "INSERT INTO allocation_checkpoints (allocation_id, checkpoint_id, stage_id, subgroup_id, stage_name, "
            "subgroup_name, checkpoint_text_snapshot, priority, result_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')",
            [
                ("ALC-B1", "CHK-01-01-001", "STG-01", "SUB-01-01", "Substructure", "Excavation", "Soil compaction check", "H"),
                ("ALC-B1", "CHK-01-01-002", "STG-01", "SUB-01-01", "Substructure", "Excavation", "Shoring stability check", "M"),
                ("ALC-B1", "CHK-01-01-003", "STG-01", "SUB-01-01", "Substructure", "Excavation", "Dewatering drainage check", "L"),
            ],
        )
        s.execute(
            "INSERT INTO non_conformities (code, project_id, title, sev, zone, trade, assigned, raised_date, due_date, status, raised_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, '2026-11-02', ?, ?, ?)",
            ("NC-B1", "prj-b1", "Rebar spacing variance", "major", "Block B Podium", "RCC", "Evan Engineer", "2026-11-06", "Open", "Queen QC"),
        )
        s.execute(
            "INSERT INTO approvals (code, project_id, kind, title, by_user, at_time, ref_ins, status) "
            "VALUES (?, ?, 'Inspection report', ?, ?, '2026-11-04 11:00:00', ?, 'Pending')",
            ("AP-B1", "prj-b1", "Beta Approval 1", "Evan Engineer", "ALC-B1"),
        )


@pytest.fixture(scope="session")
def test_app():
    """Initializes schema and test database once per session."""
    reset_database()
    db = get_database()
    _seed_test_database(db)
    app = create_app()
    yield app
    reset_database()
    shutil.rmtree(_TEMP_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_limiters():
    """Reset in-memory rate limiters before and after each test."""
    login_limiter.reset()
    signup_limiter.reset()
    yield
    login_limiter.reset()
    signup_limiter.reset()


def _make_client(app, user_dict: dict | None = None) -> TestClient:
    client = TestClient(app, raise_server_exceptions=False)
    if user_dict:
        token = create_token(user_dict)
        client.headers.update({
            "Authorization": f"Bearer {token}",
            "X-SiteIQ-CSRF": "1",
        })
        client.cookies.set(SESSION_COOKIE, token)
    return client


# User data dictionaries for token generation
USERS = {
    "admin_a": {"id": "usr-admin-a", "org_id": "org-a", "role": "admin", "email": "admin@alpha.com", "full_name": "Alice Admin", "employee_id": "EMP-A-ADM"},
    "qc_a": {"id": "usr-qc-a", "org_id": "org-a", "role": "qc_lead", "email": "qc@alpha.com", "full_name": "Quentin QC", "employee_id": "EMP-A-QC"},
    "eng_a": {"id": "usr-eng-a", "org_id": "org-a", "role": "engineer", "email": "eng@alpha.com", "full_name": "Edward Engineer", "employee_id": "EMP-A-ENG"},
    "eng_a2": {"id": "usr-eng-a2", "org_id": "org-a", "role": "engineer", "email": "eng2@alpha.com", "full_name": "Emma Engineer 2", "employee_id": "EMP-A-ENG2"},
    "admin_b": {"id": "usr-admin-b", "org_id": "org-b", "role": "admin", "email": "admin@beta.com", "full_name": "Bob Admin", "employee_id": "EMP-B-ADM"},
    "qc_b": {"id": "usr-qc-b", "org_id": "org-b", "role": "qc_lead", "email": "qc@beta.com", "full_name": "Queen QC", "employee_id": "EMP-B-QC"},
    "eng_b": {"id": "usr-eng-b", "org_id": "org-b", "role": "engineer", "email": "eng@beta.com", "full_name": "Evan Engineer", "employee_id": "EMP-B-ENG"},
}


@pytest.fixture
def anon_client(test_app) -> TestClient:
    return _make_client(test_app, None)


@pytest.fixture
def admin_a_client(test_app) -> TestClient:
    return _make_client(test_app, USERS["admin_a"])


@pytest.fixture
def qc_a_client(test_app) -> TestClient:
    return _make_client(test_app, USERS["qc_a"])


@pytest.fixture
def eng_a_client(test_app) -> TestClient:
    return _make_client(test_app, USERS["eng_a"])


@pytest.fixture
def eng_a2_client(test_app) -> TestClient:
    return _make_client(test_app, USERS["eng_a2"])


@pytest.fixture
def admin_b_client(test_app) -> TestClient:
    return _make_client(test_app, USERS["admin_b"])


@pytest.fixture
def qc_b_client(test_app) -> TestClient:
    return _make_client(test_app, USERS["qc_b"])


@pytest.fixture
def eng_b_client(test_app) -> TestClient:
    return _make_client(test_app, USERS["eng_b"])
