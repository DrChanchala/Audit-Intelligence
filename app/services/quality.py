"""Non-conformities, approvals, the legacy ``inspections`` register and the QC summary."""
from __future__ import annotations

from datetime import datetime

from app.core.errors import ValidationFailed
from app.core.security import Principal
from app.db.connection import Session
from app.services.tenancy import (
    approval_in_org,
    engineer_in_org,
    inspection_in_org,
    nc_in_org,
    project_in_org,
)


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- summary ----------

def summary(db: Session, p: Principal) -> dict:
    org, today = p.org_id, _today()
    base_nc = "FROM non_conformities n JOIN projects p ON n.project_id = p.id WHERE p.org_id = ?"
    base_ins = "FROM inspections i JOIN projects p ON i.project_id = p.id WHERE p.org_id = ?"
    crit = db.scalar(f"SELECT COUNT(*) {base_nc} AND n.status != 'Closed' AND n.sev = 'critical'", (org,))
    appr = db.scalar("SELECT COUNT(*) FROM approvals a JOIN projects p ON a.project_id = p.id "
                     "WHERE p.org_id = ? AND a.status = 'Pending'", (org,))
    overdue_ncs = db.scalar(f"SELECT COUNT(*) {base_nc} AND n.status != 'Closed' AND n.due_date < ?", (org, today))
    overdue_ins = db.scalar(f"SELECT COUNT(*) {base_ins} AND i.status IN ('Required', 'Allocated', 'In progress') "
                            "AND i.due_date < ?", (org, today))
    loads = db.all(f"SELECT i.eng, COUNT(*) AS active_count {base_ins} AND i.status IN ('Allocated', 'In progress') "
                   "AND i.eng IS NOT NULL GROUP BY i.eng", (org,))
    return {
        "critical_open_ncs": crit or 0, "pending_approvals": appr or 0,
        "overdue_items": (overdue_ncs or 0) + (overdue_ins or 0), "overdue_ncs": overdue_ncs or 0,
        "overdue_inspections": overdue_ins or 0, "engineer_loads": {r["eng"]: r["active_count"] for r in loads},
    }


# ---------- non-conformities ----------

def list_ncs(db: Session, p: Principal, project_id=None, status=None, sev=None, q=None) -> list[dict]:
    sql = ("SELECT n.*, p.name AS project_name, p.geo AS project_geo FROM non_conformities n "
           "JOIN projects p ON n.project_id = p.id WHERE p.org_id = ?")
    params: list = [p.org_id]
    if project_id:
        sql += " AND n.project_id = ?"
        params.append(project_id)
    if status == "open":
        sql += " AND n.status != 'Closed'"
    elif status == "closed":
        sql += " AND n.status = 'Closed'"
    elif status and status != "all":
        sql += " AND n.status = ?"
        params.append(status)
    if sev and sev != "all":
        sql += " AND n.sev = ?"
        params.append(sev)
    if q:
        sql += " AND (n.title LIKE ? OR n.code LIKE ? OR n.assigned LIKE ? OR n.zone LIKE ?)"
        params.extend([f"%{q}%"] * 4)
    sql += " ORDER BY CASE n.status WHEN 'Closed' THEN 2 ELSE 1 END, n.due_date"
    return db.all(sql, params)


def nc_detail(db: Session, p: Principal, code: str) -> dict:
    nc = dict(nc_in_org(db, p, code))
    nc["logs"] = db.all("SELECT * FROM nc_audit_logs WHERE nc_code = ? ORDER BY event_date, id", (code,))
    nc["photos"] = db.all("SELECT * FROM evidence_photos WHERE nc_code = ? ORDER BY id", (code,))
    nc["closure_approval"] = db.one("SELECT * FROM approvals WHERE ref_nc = ? AND status = 'Pending'", (code,))
    return nc


def _nc_log(db: Session, code: str, what: str, message: str) -> None:
    db.execute("INSERT INTO nc_audit_logs (nc_code, event_date, what, message) VALUES (?, ?, ?, ?)",
               (code, _today(), what, message))


def nc_action(db: Session, p: Principal, code: str, action: str, note: str | None) -> dict:
    nc = nc_in_org(db, p, code)
    who = p.actor
    if action == "verify":
        db.execute("UPDATE non_conformities SET status = 'Under verification' WHERE code = ?", (code,))
        _nc_log(db, code, "Sent for verification", f"Re-inspection scheduled by {who}")
        msg = f"NC {code} sent for verification on site"
    elif action == "close":
        db.execute("UPDATE non_conformities SET status = 'Closed', closed_date = ? WHERE code = ?", (_today(), code))
        _nc_log(db, code, f"Closed by {who}", note or "Closure verified and signed off.")
        db.execute("UPDATE approvals SET status = 'Approved' WHERE ref_nc = ?", (code,))
        db.execute("UPDATE action_items SET is_resolved = TRUE WHERE target_code = ?", (code,))
        db.execute("UPDATE projects SET upd_at = ?, upd_by = ? WHERE id = ?", (_now(), who, nc["project_id"]))
        msg = f"NC {code} officially closed"
    elif action == "reopen":
        db.execute("UPDATE non_conformities SET status = 'Reopened' WHERE code = ?", (code,))
        _nc_log(db, code, f"Reopened by {who}", note or f"Defect persists. Sent back to {nc['assigned']}")
        db.execute("UPDATE approvals SET status = 'Returned' WHERE ref_nc = ?", (code,))
        msg = f"NC {code} reopened and returned to {nc['assigned']}"
    else:  # remind
        what = "Escalation issued" if str(nc["due_date"]) < _today() else "Reminder sent"
        _nc_log(db, code, what, f"Formal notice sent to {nc['assigned']} ({note or 'SLA deadline alert'})")
        msg = f"{what} to {nc['assigned']}"
    return {"status": "success", "message": msg, "action": action, "code": code}


# ---------- approvals ----------

def list_approvals(db: Session, p: Principal, project_id: str | None = None) -> list[dict]:
    sql = ("SELECT a.*, p.name AS project_name FROM approvals a JOIN projects p ON a.project_id = p.id "
           "WHERE a.status = 'Pending' AND p.org_id = ?")
    params: list = [p.org_id]
    if project_id:
        sql += " AND a.project_id = ?"
        params.append(project_id)
    return db.all(sql + " ORDER BY a.at_time DESC", params)


def approval_action(db: Session, p: Principal, code: str, action: str, note: str | None) -> dict:
    ap = approval_in_org(db, p, code)
    if ap["status"] != "Pending":
        raise ValidationFailed(f"Approval {code} is already {ap['status']}.")
    who = p.actor
    if action == "approve":
        db.execute("UPDATE approvals SET status = 'Approved' WHERE code = ?", (code,))
        if ap["ref_ins"]:
            db.execute("UPDATE inspections SET status = 'Report issued' WHERE code = ?", (ap["ref_ins"],))
            db.execute("UPDATE inspection_allocations SET status = 'Report issued', approved_at = ?, updated_at = ? "
                       "WHERE allocation_id = ? AND status = 'Pending review'", (_now(), _now(), ap["ref_ins"]))
        if ap["ref_nc"]:
            db.execute("UPDATE non_conformities SET status = 'Closed', closed_date = ? WHERE code = ?",
                       (_today(), ap["ref_nc"]))
            _nc_log(db, ap["ref_nc"], f"Closed by {who}", "Signed off via approval.")
        db.execute("UPDATE projects SET upd_at = ?, upd_by = ? WHERE id = ?", (_now(), who, ap["project_id"]))
        return {"status": "success", "message": f"Approval {code} approved successfully"}
    db.execute("UPDATE approvals SET status = 'Returned' WHERE code = ?", (code,))
    if ap["ref_ins"]:
        db.execute("UPDATE inspections SET status = 'In progress' WHERE code = ?", (ap["ref_ins"],))
        db.execute("UPDATE inspection_allocations SET status = 'In progress', returned_at = ?, return_comments = ?, "
                   "updated_at = ? WHERE allocation_id = ? AND status = 'Pending review'",
                   (_now(), note or "Returned via approvals queue", _now(), ap["ref_ins"]))
    if ap["ref_nc"]:
        db.execute("UPDATE non_conformities SET status = 'Reopened' WHERE code = ?", (ap["ref_nc"],))
        _nc_log(db, ap["ref_nc"], f"Approval returned by {who}", note or "Verification evidence insufficient.")
    return {"status": "success", "message": f"Approval {code} returned to submitter"}


# ---------- legacy inspections register ----------

def list_inspections(db: Session, p: Principal, project_id=None, status=None) -> list[dict]:
    sql = ("SELECT i.*, p.name AS project_name FROM inspections i JOIN projects p ON i.project_id = p.id "
           "WHERE p.org_id = ?")
    params: list = [p.org_id]
    if project_id:
        sql += " AND i.project_id = ?"
        params.append(project_id)
    if status and status != "all":
        sql += " AND i.status = ?"
        params.append(status)
    return db.all(sql + " ORDER BY i.due_date", params)


def inspection_detail(db: Session, p: Principal, code: str) -> dict:
    ins = dict(inspection_in_org(db, p, code))
    ins["approval"] = db.one("SELECT * FROM approvals WHERE ref_ins = ? AND status = 'Pending'", (code,))
    return ins


def allocate_legacy(db: Session, p: Principal, code: str, engineer_ref: str) -> dict:
    ins = inspection_in_org(db, p, code)
    eng = engineer_in_org(db, p, engineer_ref)
    new_status = "Allocated" if ins["status"] == "Required" else ins["status"]
    db.execute("UPDATE inspections SET eng = ?, status = ? WHERE code = ?", (eng["full_name"], new_status, code))
    db.execute("UPDATE action_items SET is_resolved = TRUE WHERE target_code = ?", (code,))
    return {"status": "success", "message": f"Inspection {code} allocated to {eng['full_name']}"}


def nudge(db: Session, p: Principal, code: str) -> dict:
    ins = inspection_in_org(db, p, code)
    if not ins["eng"]:
        raise ValidationFailed("No engineer assigned to this inspection")
    return {"status": "success", "message": f"Chased engineer {ins['eng']} for inspection {code}"}


def ensure_project(db: Session, p: Principal, project_id: str) -> None:
    project_in_org(db, p, project_id)
