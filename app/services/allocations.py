"""Stage-based inspection allocation lifecycle.

    Draft -> Allocated -> In progress -> Pending review -> Report issued
                              ^                 |
                              +---- returned ---+

* QC Leads create, reassign, change status and review.
* Engineers record findings and submit, only on allocations assigned to them.
* Every actor name in the audit trail comes from the session.
* SQL is portable (ON CONFLICT upserts instead of SQLite-only INSERT OR
  REPLACE / GROUP_CONCAT, which failed on PostgreSQL).
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

from app.core.errors import Conflict, ValidationFailed
from app.core.security import Principal, Role
from app.db.connection import Row, Session
from app.schemas.requests import CheckpointProgressItem, CreateAllocationRequest
from app.services import checklist
from app.services.tenancy import (
    allocation_in_scope,
    engineer_in_org,
    engineer_keys,
    project_in_org,
)

EDITABLE = ("Allocated", "In progress", "Returned for Reinspection")
LOCKED = ("Pending review", "Report issued", "Done")
QC_SETTABLE_STATUS = {
    "on hold": "On hold", "on_hold": "On hold", "in progress": "In progress", "in_progress": "In progress",
    "returned": "Returned for Reinspection", "returned for reinspection": "Returned for Reinspection",
    "done": "Done", "closed": "Done", "allocated": "Allocated", "draft": "Draft",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _audit(db: Session, alloc_id: str, actor: str, action: str, prev: str | None, new: str | None, remarks: str) -> None:
    db.execute(
        "INSERT INTO inspection_audit_events (allocation_id, actor_name, action, previous_status, new_status, "
        "timestamp, remarks) VALUES (?, ?, ?, ?, ?, ?, ?)", (alloc_id, actor, action, prev, new, _now(), remarks))


def _set_status(db: Session, alloc_id: str, status: str, extra_sql: str = "", extra: Iterable = ()) -> None:
    db.execute(f"UPDATE inspection_allocations SET status = ?, updated_at = ?{extra_sql} WHERE allocation_id = ?",
               (status, _now(), *extra, alloc_id))
    db.execute("UPDATE inspections SET status = ? WHERE code = ?", (status, alloc_id))


def _stats(db: Session, alloc_id: str) -> dict:
    r = db.one(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN result_status = 'OK' THEN 1 ELSE 0 END) AS ok, "
        "SUM(CASE WHEN result_status = 'NC' THEN 1 ELSE 0 END) AS nc, "
        "SUM(CASE WHEN result_status = 'NA' THEN 1 ELSE 0 END) AS na "
        "FROM allocation_checkpoints WHERE allocation_id = ?", (alloc_id,))
    total, ok, nc, na = (r["total"] or 0), (r["ok"] or 0), (r["nc"] or 0), (r["na"] or 0)
    done = ok + nc + na
    return {"total": total, "ok": ok, "nc": nc, "na": na, "pending": total - done, "completed": done,
            "progress_pct": round(done / total * 100, 1) if total else 0,
            "compliance_pct": round(ok / (ok + nc) * 100, 1) if (ok + nc) else 0}


def _sync_mirror_counts(db: Session, alloc_id: str) -> dict:
    s = _stats(db, alloc_id)
    db.execute("UPDATE inspections SET items_pass = ?, items_nc = ?, items_na = ? WHERE code = ?",
               (s["ok"], s["nc"], s["na"], alloc_id))
    return s


# ---------- identifiers ----------

def next_inspection_id(db: Session, p: Principal, project_id: str) -> str:
    project = project_in_org(db, p, project_id)
    num = project["code"].replace("PRJ-", "")
    prefix = f"INS-{num}-"
    codes = [r[0] for r in db.all("SELECT code FROM inspections WHERE code LIKE ?", (prefix + "%",))]
    codes += [r[0] for r in db.all("SELECT allocation_id FROM inspection_allocations WHERE allocation_id LIKE ?",
                                   (prefix + "%",))]
    seqs = [int(c.rsplit("-", 1)[-1]) for c in codes if c.rsplit("-", 1)[-1].isdigit()]
    return f"{prefix}{(max(seqs) + 1) if seqs else 1:04d}"


# ---------- create ----------

def create_allocation(db: Session, p: Principal, req: CreateAllocationRequest) -> dict:
    is_draft = req.status.lower() == "draft"
    project = project_in_org(db, p, req.project_id)
    pid = project["id"]
    if project["status"] == "completed":
        raise ValidationFailed("Cannot allocate inspections to a Completed project.")
    if project["status"] == "hold":
        raise ValidationFailed(f"Project is on Hold: {project['hold_reason'] or 'Stop-work active'}.")

    engineer = None
    ref = req.engineer_id or req.engineer_name
    if ref:
        engineer = engineer_in_org(db, p, ref)
    elif not is_draft:
        raise ValidationFailed("Inspection Engineer must be selected before activating an inspection.")
    if not is_draft and not req.checkpoint_ids:
        raise ValidationFailed("At least one inspection checkpoint must be selected.")

    planned = req.planned_date or date.today()
    due = req.due_date or planned
    if due < planned:
        raise ValidationFailed("Inspection due date cannot precede the planned inspection date.")

    chks = checklist.checkpoints_by_ids(db, req.checkpoint_ids)
    missing = set(req.checkpoint_ids) - {c["checkpoint_id"] for c in chks}
    if missing:
        raise ValidationFailed(f"Unknown checkpoint id(s): {', '.join(sorted(missing)[:5])}")

    location = " · ".join(x for x in (req.tower_block, req.floor_level, req.zone_area, req.grid_ref,
                                      req.element_id) if x) or "General Site Area"
    eng_id = engineer["id"] if engineer else None
    eng_name = engineer["full_name"] if engineer else "Unassigned"

    existing = None
    if req.inspection_id:
        existing = db.one("SELECT * FROM inspection_allocations WHERE allocation_id = ? AND project_id = ?",
                          (req.inspection_id, pid))
        if not existing:
            raise ValidationFailed("Inspection ID does not belong to this project.")
        if existing["status"] != "Draft":
            raise Conflict(f"Inspection {req.inspection_id} is already {existing['status']}; it cannot be redefined.")
    alloc_id = existing["allocation_id"] if existing else next_inspection_id(db, p, pid)

    if not is_draft and not existing and not req.allow_duplicate and eng_id:
        wanted = sorted(req.checkpoint_ids)
        for a in db.all("SELECT allocation_id FROM inspection_allocations WHERE project_id = ? AND location_scope = ? "
                        "AND engineer_id = ? AND status IN ('Allocated', 'In progress')", (pid, location, eng_id)):
            ids = sorted(r[0] for r in db.all("SELECT checkpoint_id FROM allocation_checkpoints WHERE allocation_id = ?",
                                              (a["allocation_id"],)))
            if ids == wanted:
                raise Conflict(f"Duplicate allocation prevented: {a['allocation_id']} already covers this scope.")

    status = "Draft" if is_draft else "Allocated"
    now = _now()
    values = (pid, eng_id, eng_name, p.actor, location, req.tower_block, req.floor_level, req.zone_area, req.grid_ref,
              req.element_id, req.instructions, planned.isoformat(), due.isoformat(), req.due_time, req.priority,
              status)
    if existing:
        db.execute(
            "UPDATE inspection_allocations SET project_id = ?, engineer_id = ?, engineer_name = ?, allocated_by = ?, "
            "location_scope = ?, tower_block = ?, floor_level = ?, zone_area = ?, grid_ref = ?, element_id = ?, "
            "instructions = ?, planned_date = ?, due_date = ?, due_time = ?, priority = ?, status = ?, updated_at = ? "
            "WHERE allocation_id = ?", (*values, now, alloc_id))
        db.execute("DELETE FROM allocation_checkpoints WHERE allocation_id = ?", (alloc_id,))
    else:
        db.execute(
            "INSERT INTO inspection_allocations (allocation_id, project_id, engineer_id, engineer_name, allocated_by, "
            "location_scope, tower_block, floor_level, zone_area, grid_ref, element_id, instructions, planned_date, "
            "due_date, due_time, priority, status, created_at, updated_at, linked_ins_code) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (alloc_id, *values, now, now, alloc_id))

    db.executemany(
        "INSERT INTO allocation_checkpoints (allocation_id, checkpoint_id, stage_id, subgroup_id, stage_name, "
        "subgroup_name, checkpoint_text_snapshot, priority, result_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')",
        [(alloc_id, c["checkpoint_id"], c["stage_id"], c["subgroup_id"], c["stage_name"], c["subgroup_name"],
          c["checkpoint_description"], c["priority"]) for c in chks])

    stages = list(dict.fromkeys(c["stage_name"] for c in chks))
    subgroups = list(dict.fromkeys(c["subgroup_name"] for c in chks))
    title = (req.title or "").strip() or (
        (stages[0] if len(stages) == 1 else f"{stages[0]} (+{len(stages) - 1} stages)") if stages else "Quality Inspection")
    tpl = subgroups[0] if len(subgroups) == 1 else (f"{len(chks)} Checkpoints" if chks else "Checklist Pending")
    db.execute(
        "INSERT INTO inspections (code, project_id, title, zone, tpl, eng, due_date, status, items_count, items_pass, "
        "items_nc, items_na) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0) "
        "ON CONFLICT (code) DO UPDATE SET title = excluded.title, zone = excluded.zone, tpl = excluded.tpl, "
        "eng = excluded.eng, due_date = excluded.due_date, status = excluded.status, items_count = excluded.items_count",
        (alloc_id, pid, title, location, tpl, eng_name if engineer else None, due.isoformat(), status, len(chks)))
    action = "SAVE_DRAFT" if is_draft else ("ACTIVATE" if existing else "CREATE_INSPECTION")
    _audit(db, alloc_id, p.actor, action, existing["status"] if existing else None, status,
           f"{len(chks)} checkpoints across {len(stages)} stage(s) to {eng_name} at {location}")

    return {
        "allocation_id": alloc_id, "inspection_id": alloc_id, "project_id": pid, "project_name": project["name"],
        "engineer_name": eng_name, "engineer_id": eng_id, "status": status, "checkpoint_count": len(chks),
        "stages": stages, "subgroups": subgroups, "planned_date": planned.isoformat(), "due_date": due.isoformat(),
        "location_scope": location, "created_at": now, "title": title, "tpl": tpl,
        "message": f"Inspection {alloc_id} {'saved as draft' if is_draft else 'created and allocated'}.",
    }


# ---------- read ----------

def detail(db: Session, p: Principal, alloc_id: str) -> dict:
    alloc = dict(allocation_in_scope(db, p, alloc_id))
    proj = db.one("SELECT type, loc, geo FROM projects WHERE id = ?", (alloc["project_id"],))
    alloc.update({"project_type": proj["type"], "project_loc": proj["loc"], "project_geo": proj["geo"]})
    alloc.pop("org_id", None)
    alloc["checkpoints"] = db.all("SELECT * FROM allocation_checkpoints WHERE allocation_id = ? ORDER BY id",
                                  (alloc_id,))
    alloc["stats"] = _stats(db, alloc_id)
    alloc["audit_trail"] = db.all("SELECT * FROM inspection_audit_events WHERE allocation_id = ? ORDER BY event_id",
                                  (alloc_id,))
    alloc["reviews"] = db.all("SELECT * FROM inspection_reviews WHERE allocation_id = ? ORDER BY review_id DESC",
                              (alloc_id,))
    return alloc


_LIST_SQL = (
    "SELECT a.*, p.name AS project_name, p.code AS project_code, "
    "COALESCE(c.total, 0) AS total_checkpoints, COALESCE(c.ok, 0) AS ok_count, COALESCE(c.nc, 0) AS nc_count, "
    "COALESCE(c.na, 0) AS na_count, COALESCE(c.pending, 0) AS pending_count "
    "FROM inspection_allocations a JOIN projects p ON a.project_id = p.id "
    "LEFT JOIN (SELECT allocation_id, COUNT(*) AS total, "
    "  SUM(CASE WHEN result_status = 'OK' THEN 1 ELSE 0 END) AS ok, "
    "  SUM(CASE WHEN result_status = 'NC' THEN 1 ELSE 0 END) AS nc, "
    "  SUM(CASE WHEN result_status = 'NA' THEN 1 ELSE 0 END) AS na, "
    "  SUM(CASE WHEN result_status = 'Pending' OR result_status IS NULL THEN 1 ELSE 0 END) AS pending "
    "  FROM allocation_checkpoints GROUP BY allocation_id) c ON c.allocation_id = a.allocation_id "
    "WHERE p.org_id = ?"
)


def list_allocations(db: Session, p: Principal, project_id=None, engineer=None, status=None) -> list[dict]:
    sql, params = _LIST_SQL, [p.org_id]
    if project_id:
        sql += " AND a.project_id = ?"
        params.append(project_id)
    if engineer:
        sql += " AND (a.engineer_id = ? OR a.engineer_name = ?)"
        params.extend([engineer, engineer])
    if status and status != "all":
        sql += " AND a.status = ?"
        params.append(status)
    return db.all(sql + " ORDER BY a.due_date, a.created_at DESC", params)


def engineer_dashboard(db: Session, p: Principal, engineer_ref: str | None = None, status=None, project=None,
                       stage=None, priority=None, search=None) -> dict:
    if p.role == Role.ENGINEER:
        user = db.one("SELECT id, full_name, employee_id, specialization FROM users WHERE id = ?", (p.user_id,))
        keys = engineer_keys(p)
    else:
        user = engineer_in_org(db, p, engineer_ref or "")
        keys = tuple(k for k in (user["id"], user["employee_id"]) if k)
    profile = {"id": user["employee_id"] or user["id"], "user_id": user["id"], "name": user["full_name"],
               "role": "QC Inspection Engineer", "specialty": user["specialization"] or "Civil & Finishes"}

    rows = db.all(_LIST_SQL + f" AND a.engineer_id IN ({db.in_clause(keys)}) AND a.status != 'Draft' "
                  "ORDER BY a.due_date, a.created_at DESC", [p.org_id, *keys])
    ids = [r["allocation_id"] for r in rows]
    stage_map: dict[str, dict[str, list]] = {}
    if ids:
        for r in db.all(f"SELECT DISTINCT allocation_id, stage_name, subgroup_name FROM allocation_checkpoints "
                        f"WHERE allocation_id IN ({db.in_clause(ids)}) ORDER BY allocation_id, stage_name, subgroup_name",
                        ids):
            m = stage_map.setdefault(r["allocation_id"], {"stages": [], "subgroups": []})
            if r["stage_name"] not in m["stages"]:
                m["stages"].append(r["stage_name"])
            if r["subgroup_name"] not in m["subgroups"]:
                m["subgroups"].append(r["subgroup_name"])

    today = date.today().isoformat()
    metrics = {"allocated": 0, "in_progress": 0, "due_today": 0, "overdue": 0, "submitted": 0, "total": len(rows)}
    out = []
    sf = (status or "all").lower().replace("_", " ")
    for r in rows:
        a = dict(r)
        info = stage_map.get(a["allocation_id"], {"stages": [], "subgroups": []})
        a.update(info)
        a["primary_stage"] = info["stages"][0] if info["stages"] else "General Inspection"
        a["primary_subgroup"] = info["subgroups"][0] if info["subgroups"] else "Checkpoints"
        total = a["total_checkpoints"] or 0
        a["completed_count"] = (a["ok_count"] or 0) + (a["nc_count"] or 0) + (a["na_count"] or 0)
        a["progress_pct"] = round(a["completed_count"] / total * 100, 1) if total else 0
        active = a["status"] not in LOCKED
        a["is_overdue"] = bool(active and a["due_date"] and a["due_date"] < today)
        a["is_due_today"] = bool(active and a["due_date"] == today)
        if a["status"] == "Allocated":
            metrics["allocated"] += 1
        elif a["status"] == "In progress":
            metrics["in_progress"] += 1
        elif a["status"] in ("Pending review", "Report issued"):
            metrics["submitted"] += 1
        metrics["due_today"] += a["is_due_today"]
        metrics["overdue"] += a["is_overdue"]

        keep = {
            "all": True, "allocated": a["status"] == "Allocated", "in progress": a["status"] == "In progress",
            "due today": a["is_due_today"], "overdue": a["is_overdue"],
            "submitted": a["status"] in ("Pending review", "Report issued"),
            "pending review": a["status"] in ("Pending review", "Report issued"),
        }.get(sf, a["status"].lower() == sf)
        if keep and project and project != "all":
            keep = project.lower() in (a["project_id"].lower(), a["project_code"].lower())
        if keep and stage and stage != "all":
            keep = any(stage.lower() in s.lower() for s in a["stages"])
        if keep and priority and priority != "all":
            keep = a["priority"].lower() == priority.lower()
        if keep and search:
            blob = " ".join([a["allocation_id"], a["project_name"], a["location_scope"], *a["stages"],
                             *a["subgroups"]]).lower()
            keep = search.lower().strip() in blob
        if keep:
            out.append(a)
    return {"status": "success", "engineer": profile, "metrics": metrics, "inspections": out,
            "total_assigned": len(rows), "filtered_count": len(out)}


# ---------- engineer execution ----------

def _require_editable(alloc: Row) -> None:
    if alloc["status"] not in EDITABLE:
        raise ValidationFailed(f"Findings cannot be edited while the inspection is '{alloc['status']}'.")


def _validate_finding(alloc_id: str, cid: str, status: str, obs: str | None, photo: str | None) -> None:
    if status == "NC" and not (obs or "").strip():
        raise ValidationFailed(f"Observation remarks are mandatory for Non-Compliant checkpoint {cid}.")
    if status == "NA" and not (obs or "").strip():
        raise ValidationFailed(f"Justification is mandatory for Not Applicable checkpoint {cid}.")
    if photo and not photo.startswith(f"/api/evidence/{alloc_id}/"):
        raise ValidationFailed("Evidence must be uploaded through the evidence endpoint.")


def _start_if_needed(db: Session, p: Principal, alloc: Row, action: str) -> str:
    if alloc["status"] == "Allocated":
        _set_status(db, alloc["allocation_id"], "In progress")
        _audit(db, alloc["allocation_id"], p.actor, action, "Allocated", "In progress", "Inspection work commenced")
        return "In progress"
    return alloc["status"]


def save_progress(db: Session, p: Principal, alloc_id: str, items: list[CheckpointProgressItem]) -> dict:
    alloc = allocation_in_scope(db, p, alloc_id)
    _require_editable(alloc)
    now = _now()
    for it in items:
        _validate_finding(alloc_id, it.checkpoint_id, it.result_status, it.observations, it.evidence_photo_url)
        db.execute(
            "UPDATE allocation_checkpoints SET result_status = ?, observations = ?, evidence_photo_url = ?, "
            "inspected_at = ?, inspected_by = ? WHERE allocation_id = ? AND checkpoint_id = ?",
            (it.result_status, it.observations or "", it.evidence_photo_url or "", now, p.actor, alloc_id,
             it.checkpoint_id))
    new_status = _start_if_needed(db, p, alloc, "SAVE_PROGRESS")
    stats = _sync_mirror_counts(db, alloc_id)
    return {"status": "success", "allocation_id": alloc_id, "allocation_status": new_status, "updated_at": now,
            "stats": stats}


def record_result(db: Session, p: Principal, alloc_id: str, cid: str, status: str, obs: str | None,
                  photo: str | None) -> dict:
    item = CheckpointProgressItem(checkpoint_id=cid, result_status=status, observations=obs, evidence_photo_url=photo)
    res = save_progress(db, p, alloc_id, [item])
    return {"status": "success", "allocation_id": alloc_id, "checkpoint_id": cid, "result_status": status,
            "allocation_status": res["allocation_status"], "timestamp": res["updated_at"]}


def submit(db: Session, p: Principal, alloc_id: str, notes: str | None) -> dict:
    alloc = allocation_in_scope(db, p, alloc_id)
    _require_editable(alloc)
    c = db.one(
        "SELECT SUM(CASE WHEN result_status = 'Pending' OR result_status IS NULL THEN 1 ELSE 0 END) AS pending, "
        "SUM(CASE WHEN result_status IN ('NC', 'NA') AND (observations IS NULL OR TRIM(observations) = '') "
        "THEN 1 ELSE 0 END) AS missing, COUNT(*) AS total FROM allocation_checkpoints WHERE allocation_id = ?",
        (alloc_id,))
    if not c["total"]:
        raise ValidationFailed("This inspection has no checkpoints to submit.")
    if c["pending"]:
        raise ValidationFailed(f"Cannot submit: {c['pending']} checkpoint(s) remain pending.")
    if c["missing"]:
        raise ValidationFailed(f"Cannot submit: {c['missing']} NC/NA checkpoint(s) lack remarks.")
    now = _now()
    _set_status(db, alloc_id, "Pending review", ", submitted_at = ?", (now,))
    ap_code = f"AP-{alloc_id}"[:32]
    db.execute(
        "INSERT INTO approvals (code, project_id, kind, title, by_user, at_time, ref_ins, status) "
        "VALUES (?, ?, 'Inspection report', ?, ?, ?, ?, 'Pending') "
        "ON CONFLICT (code) DO UPDATE SET status = 'Pending', at_time = excluded.at_time, by_user = excluded.by_user",
        (ap_code, alloc["project_id"], f"Stage checkpoint report · {alloc['location_scope']}"[:255], p.actor, now,
         alloc_id))
    _audit(db, alloc_id, p.actor, "SUBMIT", alloc["status"], "Pending review", f"Submitted for QC review. {notes or ''}")
    return {"status": "success", "allocation_id": alloc_id, "new_status": "Pending review",
            "approval_code": ap_code, "submitted_at": now}


# ---------- QC lead actions ----------

def review(db: Session, p: Principal, alloc_id: str, decision: str, comments: str | None) -> dict:
    alloc = allocation_in_scope(db, p, alloc_id)
    if alloc["status"] != "Pending review":
        raise ValidationFailed(f"Only inspections pending review can be reviewed (current: {alloc['status']}).")
    now = _now()
    if decision == "approve":
        new_status = "Report issued"
        _set_status(db, alloc_id, new_status, ", approved_at = ?", (now,))
        db.execute("UPDATE approvals SET status = 'Approved' WHERE ref_ins = ? AND status = 'Pending'", (alloc_id,))
        msg = f"Inspection {alloc_id} approved. Formal report issued."
    else:
        if not (comments or "").strip():
            raise ValidationFailed("Review comments are mandatory when returning an inspection.")
        new_status = "In progress"
        _set_status(db, alloc_id, new_status, ", returned_at = ?, return_comments = ?", (now, comments))
        db.execute("UPDATE approvals SET status = 'Returned' WHERE ref_ins = ? AND status = 'Pending'", (alloc_id,))
        msg = f"Inspection {alloc_id} returned to {alloc['engineer_name']}."
    db.execute("INSERT INTO inspection_reviews (allocation_id, reviewer_name, decision, comments, reviewed_at) "
               "VALUES (?, ?, ?, ?, ?)", (alloc_id, p.actor, decision.capitalize(), comments, now))
    _audit(db, alloc_id, p.actor, "REVIEW", alloc["status"], new_status, comments or decision)
    return {"status": "success", "allocation_id": alloc_id, "decision": decision, "new_status": new_status,
            "message": msg, "reviewed_at": now}


def reassign(db: Session, p: Principal, alloc_id: str, target: str, reason: str, new_due: date | None) -> dict:
    alloc = allocation_in_scope(db, p, alloc_id)
    if not reason.strip():
        raise ValidationFailed("Reassignment reason is mandatory.")
    eng = engineer_in_org(db, p, target)
    due = new_due.isoformat() if new_due else alloc["due_date"]
    db.execute("UPDATE inspection_allocations SET engineer_id = ?, engineer_name = ?, due_date = ?, updated_at = ? "
               "WHERE allocation_id = ?", (eng["id"], eng["full_name"], due, _now(), alloc_id))
    db.execute("UPDATE inspections SET eng = ?, due_date = ? WHERE code = ?", (eng["full_name"], due, alloc_id))
    remarks = f"Reassigned from {alloc['engineer_name']} to {eng['full_name']}. Reason: {reason.strip()}."
    _audit(db, alloc_id, p.actor, "CHANGE_ENGINEER", alloc["status"], alloc["status"], remarks)
    return {"status": "success", "allocation_id": alloc_id, "previous_engineer": alloc["engineer_name"],
            "new_engineer": eng["full_name"], "new_engineer_id": eng["id"], "reason": reason.strip(),
            "due_date": due, "inspection_status": alloc["status"], "reassigned_by": p.actor,
            "reassigned_at": _now(), "message": remarks}


def change_status(db: Session, p: Principal, alloc_id: str, status: str, reason: str | None) -> dict:
    canonical = QC_SETTABLE_STATUS.get(status.lower().strip())
    if not canonical:
        raise ValidationFailed("Unsupported status. Use review to approve reports.")
    alloc = allocation_in_scope(db, p, alloc_id)
    if alloc["status"] == "Report issued":
        raise ValidationFailed("Issued reports cannot change status.")
    _set_status(db, alloc_id, canonical)
    remarks = reason or f"Status changed from {alloc['status']} to {canonical}."
    _audit(db, alloc_id, p.actor, "UPDATE_STATUS", alloc["status"], canonical, remarks)
    return {"status": "success", "allocation_id": alloc_id, "previous_status": alloc["status"],
            "new_status": canonical, "updated_at": _now(), "remarks": remarks}
