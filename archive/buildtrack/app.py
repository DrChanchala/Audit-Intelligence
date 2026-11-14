import os
import io
import uuid
import json
import shutil
from datetime import datetime, date
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Response, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from database import get_db, init_db
from progress_engine import compute_project_metrics, calculate_activity_progress
from schedule_engine import parse_schedule_excel, confirm_schedule_as_baseline
from ai_agent import ProjectAIAgent
from cv_engine import CameraVisionEngine, get_active_model_info
from export_engine import generate_excel_report
from seed_data import seed_all_data

app = FastAPI(
    title="PyCray_SiteIQ — Dual-Mode AI Construction Progress Platform",
    description="Multi-tenant construction progress monitoring platform: Mode A (Automated AI from static cameras) + Mode B (Human-verified field progress via PM review).",
    version="3.0.0"
)

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize Database on startup
init_db()

# ── Pydantic Request Schemas ──────────────────────────────────────────────────

class PMApprovalRequest(BaseModel):
    reviewer_name: str = "Project Manager"
    remarks: Optional[str] = "Approved after photographic and quantity review."

class PMModifyRequest(BaseModel):
    reviewer_name: str = "Project Manager"
    modified_quantity: float
    modified_progress_pct: Optional[float] = None
    override_reason: str = "Quantity adjusted per physical tape measurement."
    remarks: Optional[str] = "Approved with modified quantity."

class PMRejectRequest(BaseModel):
    reviewer_name: str = "Project Manager"
    reason: str = "Insufficient photographic evidence or incorrect zone."
    action: str = "RETAKE_PHOTO"  # RETAKE_PHOTO, REQUEST_INSPECTION, REJECT

class ScheduleConfirmRequest(BaseModel):
    baseline_id: str
    confirmed_by: str = "Project Manager"

class FieldVisitCreateRequest(BaseModel):
    operator_name: str
    operator_role: str = "Field Operator"
    purpose: Optional[str] = "Daily construction progress verification"

class QuantityReportRequest(BaseModel):
    reported_qty: float
    submitted_by: str = "Site Engineer"
    role: str = "Site Engineer"
    remarks: Optional[str] = "Daily site work progress reported."

class InspectionSubmitRequest(BaseModel):
    inspected_qty: float
    accepted_qty: float
    inspector: str = "QA/QC Engineer"
    status: str = "Accepted"
    comments: Optional[str] = "Quality inspection passed per project specs."
    test_results: Optional[str] = "Passed standard slump and cube test."

class AIQueryRequest(BaseModel):
    query: str
    user_role: str = "Project Manager"

class AIActionRequest(BaseModel):
    action_type: str
    payload: dict
    user_role: str = "Project Manager"

class RFICreateRequest(BaseModel):
    subject: str
    description: str
    activity_id: str
    drawing_ref: str
    raised_by: str
    assigned_to: str
    priority: str = "Medium"

class NCRCreateRequest(BaseModel):
    activity_id: str
    location: str
    description: str
    severity: str = "Moderate"
    contractor: str
    corrective_action: str
    due_date: str

class WeightageEditRequest(BaseModel):
    stage_id: str
    new_weightage: float
    modified_by: str = "Admin"
    reason: Optional[str] = "Baseline schedule re-balancing"

class GeminiKeyRequest(BaseModel):
    api_key: str


# ══════════════════════════════════════════════════════════════════════════════
# REST API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

# ── 0. AI Model Settings (Google Gemini) ──────────────────────────────────────
@app.get("/api/settings/model")
def get_model_status():
    """Returns active Vision Model status (Gemini 2.5 Flash vs Simulated)"""
    return get_active_model_info()

@app.post("/api/settings/gemini-key")
def set_gemini_api_key(req: GeminiKeyRequest):
    """
    Saves Google Gemini API key to runtime environment and persists to .env
    """
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    os.environ["GEMINI_API_KEY"] = key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"GEMINI_API_KEY={key}\n")
    return {
        "message": "Google Gemini API key activated successfully! Live visual evaluation enabled.",
        "model_info": get_active_model_info()
    }

# ── 1. Dashboard (4-Way Progress) ─────────────────────────────────────────────
@app.get("/api/dashboard")
def get_dashboard_summary():
    """
    Returns 4-way project progress metrics:
    Planned vs AI Automated vs Field Observed vs PM Approved
    """
    metrics = compute_project_metrics()
    warnings = ProjectAIAgent.get_early_warnings()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM rfis WHERE status = 'Open'")
    open_rfis = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ncrs WHERE status = 'Open'")
    open_ncrs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM safety_records WHERE status = 'Open'")
    open_safety = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pm_reviews WHERE pm_status = 'PENDING'")
    pending_pm_reviews = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cameras WHERE status = 'Active'")
    active_cameras = cursor.fetchone()[0]

    conn.close()

    return {
        "metrics": metrics,
        "early_warnings": warnings,
        "kpis": {
            "planned_progress": metrics["planned_progress"],
            "ai_automated_progress": metrics["ai_automated_progress"],
            "field_observed_progress": metrics["field_observed_progress"],
            "pm_approved_progress": metrics["pm_approved_progress"],
            "pending_pm_reviews": pending_pm_reviews,
            "active_fixed_cameras": active_cameras,
            "open_rfis": open_rfis,
            "open_ncrs": open_ncrs,
            "open_safety_incidents": open_safety
        }
    }


# ── 2. 4-Way Progress Comparison List ─────────────────────────────────────────
@app.get("/api/progress/comparison")
def get_progress_comparison():
    """
    Returns every activity with its 4 independent progress streams and variance.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.activity_code, a.name, a.stage_id, s.name as stage_name,
               a.tower_id, t.name as tower_name, a.floor_level, a.zone,
               a.planned_qty, a.uom, a.weightage,
               a.planned_start, a.planned_finish,
               a.planned_progress_pct,
               a.ai_automated_progress_pct, a.ai_automated_confidence,
               a.field_observed_progress_pct,
               a.pm_approved_progress_pct, a.pm_approved_at,
               a.accepted_qty, a.reported_qty,
               (a.ai_automated_progress_pct - a.pm_approved_progress_pct) as ai_vs_pm_delta,
               (a.ai_automated_progress_pct - a.planned_progress_pct) as ai_vs_planned_delta
        FROM activities a
        LEFT JOIN stages s ON a.stage_id = s.id
        LEFT JOIN towers t ON a.tower_id = t.id
        ORDER BY a.weightage DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ── 3. Discrepancy Detection (Spec §32) ────────────────────────────────────────
@app.get("/api/discrepancies")
def get_discrepancies():
    """
    Identifies activities with significant variance:
    - AI Automated vs PM Approved > 5%
    - AI Automated vs Planned Target > 10%
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.activity_code, a.name, a.tower_id, t.name as tower_name,
               a.floor_level, a.planned_progress_pct, a.ai_automated_progress_pct,
               a.field_observed_progress_pct, a.pm_approved_progress_pct,
               ROUND(a.ai_automated_progress_pct - a.pm_approved_progress_pct, 1) as ai_pm_variance,
               ROUND(a.ai_automated_progress_pct - a.planned_progress_pct, 1) as ai_planned_variance
        FROM activities a
        LEFT JOIN towers t ON a.tower_id = t.id
        WHERE ABS(a.ai_automated_progress_pct - a.pm_approved_progress_pct) > 5.0
           OR ABS(a.ai_automated_progress_pct - a.planned_progress_pct) > 10.0
        ORDER BY ABS(a.ai_automated_progress_pct - a.pm_approved_progress_pct) DESC
    """)
    discrepancies = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return discrepancies


# ── 4. L4 Schedule Upload & Baseline (Spec §3-§5) ─────────────────────────────
@app.post("/api/schedule/upload")
async def upload_schedule(file: UploadFile = File(...)):
    """
    Accepts L4 Schedule Excel / CSV, parses columns, performs validation checks
    (missing fields, duplicate IDs, invalid dates/quantities, weight sum != 100%),
    stores a DRAFT in schedule_baselines and returns preview + validation report.
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only .xlsx or .csv files are supported.")

    baseline_id = f"BASE-{uuid.uuid4().hex[:8].upper()}"
    saved_filename = f"{baseline_id}_{file.filename}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse schedule
    parsed = parse_schedule_excel(saved_path, project_id="PROJ-001")
    if "error" in parsed and not parsed.get("activities"):
        raise HTTPException(status_code=400, detail=parsed["error"])

    # Store baseline record
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO schedule_baselines (
            id, project_id, version, filename, uploaded_by, status,
            total_activities, total_weight, validation_errors, validation_warnings,
            validation_report, uploaded_at
        ) VALUES (?, 'PROJ-001', 1, ?, 'User', 'DRAFT', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        baseline_id, file.filename,
        parsed['summary']['total_rows'],
        parsed['summary']['total_weight'],
        len(parsed['errors']),
        len(parsed['warnings']),
        json.dumps({
            "errors": parsed['errors'][:50],
            "warnings": parsed['warnings'][:50],
            "summary": parsed['summary']
        })
    ))
    conn.commit()
    conn.close()

    # Cache parsed result in a temporary JSON file for confirmation
    cache_path = os.path.join(UPLOAD_DIR, f"{baseline_id}_parsed.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f)

    return {
        "baseline_id": baseline_id,
        "filename": file.filename,
        "summary": parsed['summary'],
        "errors": parsed['errors'][:30],
        "warnings": parsed['warnings'][:30],
        "preview_activities": parsed['activities'][:15]
    }

@app.post("/api/schedule/confirm")
def confirm_schedule(req: ScheduleConfirmRequest):
    """
    Confirms uploaded L4 schedule draft as the active project baseline.
    Clears old activities and writes full WBS baseline to database.
    """
    cache_path = os.path.join(UPLOAD_DIR, f"{req.baseline_id}_parsed.json")
    if not os.path.exists(cache_path):
        raise HTTPException(status_code=404, detail="Parsed schedule cache not found. Please re-upload.")

    with open(cache_path, "r", encoding="utf-8") as f:
        parsed_result = json.load(f)

    result = confirm_schedule_as_baseline(
        parsed_result=parsed_result,
        baseline_id=req.baseline_id,
        confirmed_by=req.confirmed_by,
        project_id="PROJ-001"
    )
    return result

@app.get("/api/schedule/baseline")
def get_current_baseline():
    """Returns details of currently active confirmed L4 baseline."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM schedule_baselines
        ORDER BY uploaded_at DESC LIMIT 1
    """)
    baseline = cursor.fetchone()
    conn.close()
    if not baseline:
        return {"status": "NO_BASELINE", "message": "No L4 schedule has been uploaded yet."}
    return dict(baseline)


# ── 5. Mode B: Field Operator Capture & Visits (Spec §12-§16) ─────────────────
@app.post("/api/field/visits")
def create_field_visit(req: FieldVisitCreateRequest):
    """Creates a new field operator visit session."""
    conn = get_db()
    cursor = conn.cursor()
    visit_id = f"VISIT-{uuid.uuid4().hex[:8].upper()}"
    cursor.execute("""
        INSERT INTO field_visits (id, project_id, operator_name, operator_role, visit_date, purpose, status)
        VALUES (?, 'PROJ-001', ?, ?, CURRENT_DATE, ?, 'IN_PROGRESS')
    """, (visit_id, req.operator_name, req.operator_role, req.purpose))
    conn.commit()
    conn.close()
    return {"visit_id": visit_id, "operator_name": req.operator_name, "status": "IN_PROGRESS"}

@app.post("/api/field/photos")
async def upload_field_photo(
    photo: UploadFile = File(...),
    activity_id: str = Form(...),
    tower_id: str = Form("TOW-A"),
    floor_level: int = Form(5),
    zone: str = Form("Zone 1"),
    operator_name: str = Form("Field Operator"),
    operator_quantity: Optional[float] = Form(0.0),
    operator_uom: Optional[str] = Form("m2"),
    operator_remarks: Optional[str] = Form("")
):
    """
    Mode B entry point (Spec §12-§16):
    1. Uploads field photo to static/uploads/
    2. Runs AI Image Validation (Spec §13, §14, §34)
    3. If valid, runs AI Schedule Evaluation (Spec §15, §16, §36)
    4. Creates record in PM Review Queue (Spec §17)
    """
    photo_id = f"PHOTO-{uuid.uuid4().hex[:8].upper()}"
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    saved_filename = f"{photo_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)
    public_url = f"/static/uploads/{saved_filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)

    # 1. AI Image Validation (Spec §34)
    validation = CameraVisionEngine.validate_field_photo(
        photo_id=photo_id,
        file_path=file_path,
        activity_id=activity_id,
        tower_id=tower_id,
        floor_level=floor_level
    )

    # 2. Save photo record
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO field_photos (
            id, activity_id, tower_id, floor_level, zone, file_path, file_name,
            captured_by, operator_quantity, operator_uom, operator_remarks,
            validation_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        photo_id, activity_id, tower_id, floor_level, zone, public_url, photo.filename,
        operator_name, operator_quantity, operator_uom, operator_remarks,
        validation['validation_status']
    ))
    conn.commit()
    conn.close()

    if not validation['image_valid'] or not validation['context_relevant']:
        return {
            "photo_id": photo_id,
            "image_url": public_url,
            "validation": validation,
            "status": "REJECTED_BY_AI",
            "message": validation.get("rejection_reason") or "Photo rejected during validation."
        }

    # 3. AI Evaluation against L4 Schedule (Spec §36)
    ai_eval = CameraVisionEngine.evaluate_field_photo(
        photo_id=photo_id,
        activity_id=activity_id,
        operator_qty=operator_quantity or 0.0,
        operator_uom=operator_uom or "m2"
    )

    # 4. Insert into PM Review Queue (Spec §17)
    review_id = f"REV-{uuid.uuid4().hex[:8].upper()}"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pm_reviews (
            id, photo_id, activity_id, field_operator,
            ai_progress_percent, ai_confidence, operator_quantity, operator_uom,
            pm_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', CURRENT_TIMESTAMP)
    """, (
        review_id, photo_id, activity_id, operator_name,
        ai_eval['ai_progress_percent'], ai_eval['ai_confidence'],
        operator_quantity, operator_uom
    ))
    conn.commit()
    conn.close()

    return {
        "photo_id": photo_id,
        "image_url": public_url,
        "validation": validation,
        "ai_evaluation": ai_eval,
        "pm_review_id": review_id,
        "status": "SUBMITTED_FOR_PM_REVIEW"
    }


# ── 6. Mode B: Project Manager Review Queue (Spec §17-§19, §37) ───────────────
@app.get("/api/pm/reviews")
def get_pm_reviews(status: Optional[str] = None):
    """Lists PM review items (Pending, Approved, Rejected)."""
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT r.*, p.file_path as image_url, p.floor_level, p.zone, p.tower_id,
               p.operator_remarks,
               a.activity_code, a.name as activity_name, a.planned_qty, a.uom,
               a.planned_start, a.planned_finish,
               v.validation_status, v.validation_confidence
        FROM pm_reviews r
        JOIN field_photos p ON r.photo_id = p.id
        LEFT JOIN activities a ON r.activity_id = a.id
        LEFT JOIN image_validations v ON p.id = v.photo_id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND r.pm_status = ?"
        params.append(status)
    query += " ORDER BY r.created_at DESC"

    cursor.execute(query, params)
    reviews = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return reviews

@app.post("/api/pm/reviews/{review_id}/approve")
def pm_approve_review(review_id: str, req: PMApprovalRequest):
    """
    Project Manager approves the field observation (Spec §18, §37).
    This establishes official Human-Verified / PM-Approved Progress!
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pm_reviews WHERE id = ?", (review_id,))
    rev = cursor.fetchone()
    if not rev:
        conn.close()
        raise HTTPException(status_code=404, detail="Review item not found")

    act_id = rev['activity_id']
    cursor.execute("SELECT * FROM activities WHERE id = ?", (act_id,))
    act = cursor.fetchone()

    planned_qty = float(act['planned_qty'] or 100.0) if act else 100.0
    operator_qty = float(rev['operator_quantity'] or 0.0)

    # Approved quantity & progress
    approved_qty = operator_qty if operator_qty > 0 else planned_qty * (float(rev['ai_progress_percent'] or 0.0) / 100.0)
    approved_pct = round((approved_qty / planned_qty * 100.0), 2) if planned_qty > 0 else 0.0

    now_iso = datetime.now().isoformat()

    # Update PM Review record
    cursor.execute("""
        UPDATE pm_reviews
        SET pm_status = 'APPROVED',
            pm_approved_quantity = ?,
            pm_approved_progress_percent = ?,
            pm_reviewer = ?,
            pm_remarks = ?,
            pm_action = 'APPROVE',
            reviewed_at = ?
        WHERE id = ?
    """, (approved_qty, approved_pct, req.reviewer_name, req.remarks, now_iso, review_id))

    # Update activity PM approved progress
    cursor.execute("""
        UPDATE activities
        SET pm_approved_progress_pct = ?,
            pm_approved_at = ?,
            accepted_qty = ?
        WHERE id = ?
    """, (approved_pct, now_iso, approved_qty, act_id))

    conn.commit()
    conn.close()

    return {
        "source_type": "FIELD_OPERATOR",
        "review_id": review_id,
        "pm_status": "APPROVED",
        "pm_approved_quantity": approved_qty,
        "pm_approved_progress_percent": approved_pct,
        "approved_by": req.reviewer_name,
        "approved_at": now_iso
    }

@app.post("/api/pm/reviews/{review_id}/modify")
def pm_modify_and_approve_review(review_id: str, req: PMModifyRequest):
    """
    Project Manager modifies the observed quantity/progress and approves (Spec §17).
    Preserves original AI & operator values for full auditability (Spec §38).
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pm_reviews WHERE id = ?", (review_id,))
    rev = cursor.fetchone()
    if not rev:
        conn.close()
        raise HTTPException(status_code=404, detail="Review item not found")

    act_id = rev['activity_id']
    cursor.execute("SELECT * FROM activities WHERE id = ?", (act_id,))
    act = cursor.fetchone()

    planned_qty = float(act['planned_qty'] or 100.0) if act else 100.0
    mod_qty = req.modified_quantity
    mod_pct = req.modified_progress_pct if req.modified_progress_pct is not None else round((mod_qty / planned_qty * 100.0), 2)
    now_iso = datetime.now().isoformat()

    cursor.execute("""
        UPDATE pm_reviews
        SET pm_status = 'APPROVED',
            pm_approved_quantity = ?,
            pm_approved_progress_percent = ?,
            pm_reviewer = ?,
            pm_remarks = ?,
            pm_action = 'MODIFY_AND_APPROVE',
            reviewed_at = ?
        WHERE id = ?
    """, (mod_qty, mod_pct, req.reviewer_name, f"{req.remarks} [Override Reason: {req.override_reason}]", now_iso, review_id))

    # Update activity
    cursor.execute("""
        UPDATE activities
        SET pm_approved_progress_pct = ?,
            pm_approved_at = ?,
            accepted_qty = ?
        WHERE id = ?
    """, (mod_pct, now_iso, mod_qty, act_id))

    # Log override in ai_observations
    cursor.execute("""
        UPDATE ai_observations
        SET human_override = 1,
            override_reason = ?,
            override_by = ?
        WHERE photo_id = ?
    """, (req.override_reason, req.reviewer_name, rev['photo_id']))

    conn.commit()
    conn.close()

    return {
        "review_id": review_id,
        "pm_status": "APPROVED",
        "action": "MODIFY_AND_APPROVE",
        "pm_approved_quantity": mod_qty,
        "pm_approved_progress_percent": mod_pct,
        "override_reason": req.override_reason,
        "approved_by": req.reviewer_name,
        "approved_at": now_iso
    }

@app.post("/api/pm/reviews/{review_id}/reject")
def pm_reject_review(review_id: str, req: PMRejectRequest):
    """Project Manager rejects observation or requests retake (Spec §17)."""
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    cursor.execute("""
        UPDATE pm_reviews
        SET pm_status = 'REJECTED',
            pm_reviewer = ?,
            pm_remarks = ?,
            pm_action = ?,
            reviewed_at = ?
        WHERE id = ?
    """, (req.reviewer_name, req.reason, req.action, now_iso, review_id))
    conn.commit()
    conn.close()
    return {
        "review_id": review_id,
        "pm_status": "REJECTED",
        "action": req.action,
        "reason": req.reason,
        "reviewed_at": now_iso
    }


# ── 7. Mode A: Static Camera AI Operations (Spec §6-§11, §35) ─────────────────
@app.get("/api/cameras")
def get_cameras():
    return CameraVisionEngine.get_active_cameras()

@app.get("/api/cameras/{camera_id}/analyze")
def analyze_camera(camera_id: str):
    """
    Runs Mode A Static Camera Automated AI Progress evaluation (Spec §35).
    Directly updates AI Automated Progress on activity without PM intervention!
    """
    analysis = CameraVisionEngine.analyze_camera_feed(camera_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Camera feed not found")
    return analysis

@app.get("/api/timelapse")
def get_timelapse(tower_id: str = "TOW-A", floor_level: int = 12):
    return CameraVisionEngine.get_time_lapse_data(tower_id, floor_level)


# ── 8. Activities List ────────────────────────────────────────────────────────
@app.get("/api/activities")
def get_activities(stage_id: Optional[str] = None, tower_id: Optional[str] = None, floor_level: Optional[int] = None):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT a.*, s.name as stage_name, t.name as tower_name
        FROM activities a
        LEFT JOIN stages s ON a.stage_id = s.id
        LEFT JOIN towers t ON a.tower_id = t.id
        WHERE 1=1
    """
    params = []
    if stage_id:
        query += " AND a.stage_id = ?"
        params.append(stage_id)
    if tower_id:
        query += " AND a.tower_id = ?"
        params.append(tower_id)
    if floor_level is not None:
        query += " AND a.floor_level = ?"
        params.append(floor_level)

    cursor.execute(query, params)
    acts = [dict(row) for row in cursor.fetchall()]

    for a in acts:
        acc_pct, rep_pct = calculate_activity_progress(a['planned_qty'], a['accepted_qty'], a['reported_qty'])
        a['physical_progress_pct'] = acc_pct
        a['reported_progress_pct'] = rep_pct
        a['earned_weight'] = round((acc_pct / 100.0) * a['weightage'], 3)

    conn.close()
    return acts


# ── 9. Auxiliary Field & Operations APIs ───────────────────────────────────────
@app.post("/api/activities/{activity_id}/report")
def report_activity_quantity(activity_id: str, req: QuantityReportRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
    act = cursor.fetchone()
    if not act:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    new_reported = req.reported_qty
    cursor.execute("""
        UPDATE activities
        SET reported_qty = ?, status = 'In Progress', inspection_status = 'Pending QA/QC', remarks = ?
        WHERE id = ?
    """, (new_reported, req.remarks, activity_id))

    cursor.execute("""
        INSERT INTO progress_updates (id, activity_id, submitted_by, role, reported_qty, remarks)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (f"UPD-{activity_id[:8]}-{os.urandom(3).hex()}", activity_id, req.submitted_by, req.role, new_reported, req.remarks))

    inspection_id = f"INSP-{os.urandom(4).hex()}"
    cursor.execute("""
        INSERT INTO inspections (id, activity_id, requested_by, status, comments)
        VALUES (?, ?, ?, 'Pending', ?)
    """, (inspection_id, activity_id, req.submitted_by, f"Inspection requested for reported {new_reported} {act['uom']}"))

    conn.commit()
    conn.close()
    return {
        "message": "Reported quantity submitted successfully. Sent to QA/QC.",
        "activity_id": activity_id,
        "reported_qty": new_reported,
        "inspection_status": "Pending QA/QC"
    }

@app.post("/api/activities/{activity_id}/inspect")
def inspect_and_accept_quantity(activity_id: str, req: InspectionSubmitRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
    act = cursor.fetchone()
    if not act:
        conn.close()
        raise HTTPException(status_code=404, detail="Activity not found")

    accepted = req.accepted_qty
    planned = float(act['planned_qty'] or 1.0)
    status = "Completed" if accepted >= planned else "In Progress"
    insp_status = "Accepted" if req.status == "Accepted" else "Rejected"

    cursor.execute("""
        UPDATE activities
        SET inspected_qty = ?, accepted_qty = ?, status = ?, inspection_status = ?, remarks = ?
        WHERE id = ?
    """, (req.inspected_qty, accepted, status, insp_status, req.comments, activity_id))

    cursor.execute("""
        INSERT INTO inspections (id, activity_id, requested_by, inspector, inspected_qty, accepted_qty, status, comments, test_results)
        VALUES (?, ?, 'Site Engineer', ?, ?, ?, ?, ?, ?)
    """, (f"INSP-DONE-{os.urandom(3).hex()}", activity_id, req.inspector, req.inspected_qty, accepted, insp_status, req.comments, req.test_results))

    conn.commit()
    conn.close()
    new_metrics = compute_project_metrics()
    return {
        "message": f"QA/QC inspection recorded. Accepted quantity updated to {accepted} {act['uom']}.",
        "new_accepted_qty": accepted,
        "activity_progress_pct": round((accepted / planned * 100.0), 2),
        "overall_project_physical_progress": new_metrics['physical_progress']
    }

@app.get("/api/stages")
def get_stages():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stages ORDER BY stage_number")
    stages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return stages

@app.get("/api/rfis")
def get_rfis():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rfis ORDER BY created_at DESC")
    rfis = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rfis

@app.post("/api/rfis")
def create_rfi(req: RFICreateRequest):
    conn = get_db()
    cursor = conn.cursor()
    rfi_id = f"RFI-{os.urandom(3).hex()}"
    num = f"RFI-GHR-{os.urandom(2).hex().upper()}"
    cursor.execute("""
        INSERT INTO rfis (id, rfi_number, subject, description, activity_id, drawing_ref, raised_by, assigned_to, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (rfi_id, num, req.subject, req.description, req.activity_id, req.drawing_ref, req.raised_by, req.assigned_to, req.priority))
    conn.commit()
    conn.close()
    return {"message": "RFI created successfully", "rfi_number": num}

@app.get("/api/ncrs")
def get_ncrs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ncrs ORDER BY created_at DESC")
    ncrs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return ncrs

@app.post("/api/ncrs")
def create_ncr(req: NCRCreateRequest):
    conn = get_db()
    cursor = conn.cursor()
    ncr_id = f"NCR-{os.urandom(3).hex()}"
    num = f"NCR-GHR-{os.urandom(2).hex().upper()}"
    cursor.execute("""
        INSERT INTO ncrs (id, ncr_number, activity_id, location, description, severity, contractor, corrective_action, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ncr_id, num, req.activity_id, req.location, req.description, req.severity, req.contractor, req.corrective_action, req.due_date))
    conn.commit()
    conn.close()
    return {"message": "NCR issued successfully", "ncr_number": num}

@app.get("/api/safety")
def get_safety_records():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM safety_records ORDER BY created_at DESC")
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return records

@app.get("/api/materials")
def get_materials():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materials")
    mats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    for m in mats:
        m['shortage_warning'] = m['current_stock'] < m['reorder_level']
    return mats

@app.post("/api/ai/query")
def process_ai_query(req: AIQueryRequest):
    return ProjectAIAgent.process_user_query(req.query, req.user_role)

@app.get("/api/ai/daily-report")
def get_daily_ai_report():
    return ProjectAIAgent.generate_daily_report()

@app.post("/api/ai/action")
def execute_ai_action(req: AIActionRequest):
    if req.action_type == "CREATE_INSPECTION":
        act_id = req.payload.get("activity_id", "ACT-TOWA-L12-SLAB")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE activities SET inspection_status = 'Pending QA/QC' WHERE id = ?", (act_id,))
        conn.commit()
        conn.close()
        return {"message": "AI Action Executed: Inspection request submitted to QA/QC queue."}
    return {"message": "Action executed successfully."}

@app.get("/api/reports/download")
def download_excel_report(report_type: str = "progress"):
    excel_bytes = generate_excel_report(report_type)
    filename = f"PyCray_SiteIQ_Report_{report_type.upper()}_2026-09-17.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/seed")
def seed_data():
    seed_all_data()
    return {"message": "PyCray_SiteIQ database seeded successfully with Dual-Mode demo records!"}


# ── Static UI Mounting ────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True)
