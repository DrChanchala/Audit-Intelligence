"""Projects, scoped to the caller's organization."""
from __future__ import annotations

import uuid
from datetime import datetime

from app.core.security import Principal, Role
from app.db.connection import Session
from app.schemas.requests import ProjectCreate
from app.services.tenancy import engineer_keys, project_in_org


def list_projects(db: Session, p: Principal, status: str | None = None, q: str | None = None) -> list[dict]:
    sql = "SELECT * FROM projects WHERE org_id = ?"
    params: list = [p.org_id]
    if p.role == Role.ENGINEER:
        keys = engineer_keys(p)
        sql += (f" AND id IN (SELECT project_id FROM inspection_allocations WHERE engineer_id IN ({db.in_clause(keys)}))")
        params.extend(keys)
    if status and status != "all":
        sql += " AND status = ?"
        params.append(status)
    if q:
        sql += " AND (name LIKE ? OR code LIKE ? OR loc LIKE ?)"
        params.extend([f"%{q}%"] * 3)
    projects = [dict(r) for r in db.all(sql + " ORDER BY name", params)]
    if not projects:
        return []

    ids = [pr["id"] for pr in projects]
    marks = db.in_clause(ids)
    nc_counts = {r["project_id"]: r for r in db.all(
        f"SELECT project_id, COUNT(*) AS open_ncs, "
        f"SUM(CASE WHEN sev = 'critical' THEN 1 ELSE 0 END) AS critical_ncs "
        f"FROM non_conformities WHERE status != 'Closed' AND project_id IN ({marks}) GROUP BY project_id", ids)}
    ins_counts = {r["project_id"]: r["n"] for r in db.all(
        f"SELECT project_id, COUNT(*) AS n FROM inspection_allocations "
        f"WHERE status IN ('Allocated', 'In progress', 'Pending review') AND project_id IN ({marks}) "
        f"GROUP BY project_id", ids)}
    for pr in projects:
        nc = nc_counts.get(pr["id"])
        pr["open_ncs"] = (nc["open_ncs"] if nc else 0) or 0
        pr["critical_ncs"] = (nc["critical_ncs"] if nc else 0) or 0
        pr["active_inspections"] = ins_counts.get(pr["id"], 0)
    return projects


def _next_project_code(db: Session) -> str:
    # Project codes are globally unique (DB constraint); take the next free number.
    rows = db.all("SELECT code FROM projects WHERE code LIKE 'PRJ-%'")
    nums = [int(r["code"][4:]) for r in rows if r["code"][4:].isdigit()]
    return f"PRJ-{(max(nums) + 1) if nums else 1:04d}"


def create_project(db: Session, p: Principal, req: ProjectCreate) -> dict:
    pid = f"prj-{uuid.uuid4().hex[:12]}"
    code = _next_project_code(db)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "INSERT INTO projects (id, code, name, type, loc, geo, status, progress, start_date, end_date, hold_reason, "
        "closed_extra, upd_at, upd_by, org_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)",
        (pid, code, req.name, req.type, req.loc, req.geo or "—", req.status, req.progress,
         req.start_date.isoformat(), req.end_date.isoformat(), req.hold_reason, now, p.actor, p.org_id),
    )
    return dict(project_in_org(db, p, pid))


def project_detail(db: Session, p: Principal, project_id: str) -> dict:
    proj = dict(project_in_org(db, p, project_id))
    pid = proj["id"]
    proj["ncs"] = db.all("SELECT * FROM non_conformities WHERE project_id = ? ORDER BY due_date", (pid,))
    proj["inspections"] = db.all("SELECT * FROM inspections WHERE project_id = ? ORDER BY due_date", (pid,))
    proj["approvals"] = db.all(
        "SELECT * FROM approvals WHERE project_id = ? AND status = 'Pending' ORDER BY at_time DESC", (pid,))
    proj["actions"] = db.all(
        "SELECT * FROM action_items WHERE project_id = ? AND is_resolved = FALSE ORDER BY due_date", (pid,))
    return proj
