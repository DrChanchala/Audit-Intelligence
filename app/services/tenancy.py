"""Tenant guards. Every read/write of tenant data goes through one of these.

Only ``projects`` carries org_id, so each child resource is resolved to its
project and checked against the caller's org. Resources in another tenant
raise NotFound (not Forbidden) so their existence is never confirmed.
"""
from __future__ import annotations

from app.core.errors import NotFound
from app.core.security import Principal, Role
from app.db.connection import Row, Session


def project_in_org(db: Session, p: Principal, project_id: str) -> Row:
    row = db.one("SELECT * FROM projects WHERE (id = ? OR code = ?) AND org_id = ?", (project_id, project_id, p.org_id))
    if not row:
        raise NotFound("Project not found.")
    return row


def engineer_keys(p: Principal) -> tuple[str, ...]:
    """Identifiers an allocation may use to point at this engineer (user id or employee id)."""
    return tuple(k for k in (p.user_id, p.employee_id) if k)


def allocation_in_scope(db: Session, p: Principal, allocation_id: str) -> Row:
    """Allocation visible to the caller: same org, and for engineers only their own."""
    row = db.one(
        "SELECT a.*, p.org_id AS org_id, p.name AS project_name, p.code AS project_code "
        "FROM inspection_allocations a JOIN projects p ON a.project_id = p.id "
        "WHERE a.allocation_id = ? AND p.org_id = ?",
        (allocation_id, p.org_id),
    )
    if not row:
        raise NotFound("Inspection not found.")
    if p.role == Role.ENGINEER and row["engineer_id"] not in engineer_keys(p):
        raise NotFound("Inspection not found.")
    return row


def _child(db: Session, p: Principal, table: str, key_col: str, value: str, label: str) -> Row:
    row = db.one(
        f"SELECT t.*, p.name AS project_name FROM {table} t JOIN projects p ON t.project_id = p.id "
        f"WHERE t.{key_col} = ? AND p.org_id = ?",
        (value, p.org_id),
    )
    if not row:
        raise NotFound(f"{label} not found.")
    return row


def inspection_in_org(db: Session, p: Principal, code: str) -> Row:
    return _child(db, p, "inspections", "code", code, "Inspection")


def nc_in_org(db: Session, p: Principal, code: str) -> Row:
    return _child(db, p, "non_conformities", "code", code, "Non-conformity")


def approval_in_org(db: Session, p: Principal, code: str) -> Row:
    return _child(db, p, "approvals", "code", code, "Approval")


def engineer_in_org(db: Session, p: Principal, ref: str) -> Row:
    """Resolve an engineer by user id, employee id or email within the caller's org."""
    row = db.one(
        "SELECT id, full_name, employee_id, specialization FROM users "
        "WHERE org_id = ? AND role = 'engineer' AND status = 'active' AND (id = ? OR employee_id = ? OR LOWER(email) = LOWER(?))",
        (p.org_id, ref, ref, ref),
    )
    if not row:
        # Back-compat: older clients send the engineer's display name. Accept only an unambiguous match.
        rows = db.all(
            "SELECT id, full_name, employee_id, specialization FROM users "
            "WHERE org_id = ? AND role = 'engineer' AND status = 'active' AND LOWER(full_name) = LOWER(?)",
            (p.org_id, ref),
        )
        row = rows[0] if len(rows) == 1 else None
    if not row:
        raise NotFound("Engineer not found in your organization.")
    return row
