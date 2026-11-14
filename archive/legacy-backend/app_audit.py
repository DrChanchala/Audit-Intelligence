"""
Audit Intelligence - Production FastAPI Backend
Engineered for ultra-low latency, full QC Lead workflow compliance,
and minimal AWS operational footprint (< $5/month).
"""

import os
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3

from database_audit import get_connection, seed_database
from inspection_report_service import InspectionReportService
from allocation_service import AllocationService
import time
from auth_service import (
    create_access_token,
    verify_password,
    hash_password,
    get_current_user,
    get_current_user_optional
)

app = FastAPI(
    title="Audit Intelligence API",
    description="Quality Assurance, QC Lead Dashboard & Non-Conformity Audit Management Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- PYDANTIC SCHEMAS -----------------

class LoginRequest(BaseModel):
    email: str
    password: str
    org_id: Optional[str] = None

class CreateOrgRequest(BaseModel):
    id: str
    name: str
    code: str
    domain: Optional[str] = None
    industry: Optional[str] = "Construction & Real Estate"
    address: Optional[str] = None

class RegisterOrgAdminRequest(BaseModel):
    org_name: str
    org_code: Optional[str] = None
    industry: Optional[str] = "Construction & Real Estate"
    address: Optional[str] = None
    admin_name: str
    admin_email: str
    admin_password: str
    admin_phone: Optional[str] = None

class CreateUserRequest(BaseModel):
    org_id: str
    email: str
    password: str
    full_name: str
    role: str
    employee_id: Optional[str] = None
    specialization: Optional[str] = None
    phone: Optional[str] = None

class ProjectCreate(BaseModel):
    id: Optional[str] = None
    code: Optional[str] = None
    name: str
    type: str = "Commercial & Residential"
    loc: str
    geo: Optional[str] = "28.5383° N, 77.3720° E"
    status: str = "live"
    progress: int = 0
    start_date: str
    end_date: str
    hold_reason: Optional[str] = None
    org_id: Optional[str] = None

class NCActionRequest(BaseModel):
    action: str  # verify, close, reopen, remind
    user: str = "Priya Deshmukh"
    note: Optional[str] = None

class ApprovalActionRequest(BaseModel):
    action: str  # approve, return
    user: str = "Priya Deshmukh"
    note: Optional[str] = None

class AllocateEngineerRequest(BaseModel):
    engineer_name: str
    user: str = "Priya Deshmukh"

class CreateAllocationRequest(BaseModel):
    project_id: str
    inspection_id: Optional[str] = None
    title: Optional[str] = None
    activity_type: Optional[str] = None
    inspection_type: Optional[str] = None
    engineer_name: Optional[str] = None
    engineer_id: Optional[str] = None
    allocated_by: Optional[str] = "Priya Deshmukh (QC Lead)"
    tower_block: Optional[str] = ""
    floor_level: Optional[str] = ""
    zone_area: Optional[str] = ""
    grid_ref: Optional[str] = ""
    element_id: Optional[str] = ""
    instructions: Optional[str] = ""
    planned_date: Optional[str] = None
    due_date: Optional[str] = None
    due_time: Optional[str] = "18:00"
    priority: Optional[str] = "High"
    checkpoint_ids: Optional[List[str]] = []
    allow_duplicate: Optional[bool] = False
    status: Optional[str] = "Allocated"

class CheckpointResultRequest(BaseModel):
    checkpoint_id: str
    result_status: str  # Pending, OK, NC, NA
    observations: Optional[str] = None
    photo_url: Optional[str] = None
    inspected_by: Optional[str] = "Inspection Engineer"

class SubmitAllocationRequest(BaseModel):
    submitted_by: Optional[str] = "Inspection Engineer"
    notes: Optional[str] = None

class ReviewAllocationRequest(BaseModel):
    decision: str  # approve, return
    reviewer_name: Optional[str] = "Priya Deshmukh (QC Lead)"
    comments: Optional[str] = None

class ReassignAllocationRequest(BaseModel):
    new_engineer: Optional[str] = None
    new_engineer_id: Optional[str] = None
    new_engineer_name: Optional[str] = None
    reason: Optional[str] = "Operational reallocation"
    new_due_date: Optional[str] = None
    actor_name: Optional[str] = "Priya Deshmukh (QC Lead)"

class ChangeStatusRequest(BaseModel):
    status: str
    reason: Optional[str] = None
    actor_name: Optional[str] = "Priya Deshmukh (QC Lead)"

class CheckpointProgressItem(BaseModel):
    checkpoint_id: str
    result_status: str  # Pending, OK, NC, NA
    observations: Optional[str] = None
    evidence_photo_url: Optional[str] = None

class SaveProgressRequest(BaseModel):
    saved_by: Optional[str] = "Inspection Engineer"
    checkpoints: List[CheckpointProgressItem]

class UploadEvidencePayload(BaseModel):
    checkpoint_id: Optional[str] = None
    data_url: Optional[str] = None
    filename: Optional[str] = None

# ----------------- HELPER FUNCTIONS -----------------

def dict_from_row(row):
    return dict(row) if row else None

# ----------------- API ENDPOINTS -----------------

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "platform": "SiteIQ Audit Intelligence",
        "timestamp": datetime.now().isoformat(),
        "database": "postgresql" if os.environ.get("DATABASE_URL") else "sqlite"
    }

@app.post("/api/seed")
def api_seed_database():
    seed_database()
    return {"status": "success", "message": "Audit Intelligence database seeded successfully"}

# ----------------- AUTHENTICATION & MULTI-TENANT ENDPOINTS -----------------

@app.get("/api/auth/organizations")
def list_organizations():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, code, domain, industry, address, status FROM organizations WHERE status = 'active' ORDER BY name ASC")
    orgs = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"status": "success", "organizations": orgs}

@app.post("/api/auth/login")
def login_endpoint(req: LoginRequest):
    email = req.email.strip().lower()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE LOWER(email) = ? AND status = 'active'", (email,))
    user_row = cur.fetchone()

    if not user_row:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user = dict(user_row)

    if req.org_id and req.org_id != "org-admin" and user["role"] != "admin" and user["org_id"] != req.org_id:
        conn.close()
        raise HTTPException(status_code=403, detail="User does not belong to the selected organization.")

    if not verify_password(req.password, user["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    cur.execute("SELECT * FROM organizations WHERE id = ?", (user["org_id"],))
    org_row = cur.fetchone()
    org = dict(org_row) if org_row else {"id": user["org_id"], "name": "Enterprise Organization", "code": "ORG"}

    now_str = datetime.now().isoformat()
    cur.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_str, user["id"]))
    conn.commit()
    conn.close()

    token = create_access_token(
        user_id=user["id"],
        org_id=user["org_id"],
        role=user["role"],
        email=user["email"],
        full_name=user["full_name"],
        employee_id=user.get("employee_id")
    )

    return {
        "status": "success",
        "message": "Authentication successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "employee_id": user.get("employee_id"),
            "specialization": user.get("specialization"),
            "avatar_initials": user.get("avatar_initials") or user["full_name"][:2].upper()
        },
        "organization": {
            "id": org["id"],
            "name": org["name"],
            "code": org["code"]
        }
    }

@app.get("/api/auth/me")
def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, org_id, email, full_name, role, employee_id, specialization, avatar_initials, phone, status, last_login_at FROM users WHERE id = ?", (user["sub"],))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User account not found")
    user_data = dict(row)

    cur.execute("SELECT id, name, code, domain, industry, address FROM organizations WHERE id = ?", (user_data["org_id"],))
    org_row = cur.fetchone()
    org_data = dict(org_row) if org_row else None
    conn.close()

    return {
        "status": "success",
        "user": user_data,
        "organization": org_data
    }

@app.get("/api/auth/users")
def list_org_users(role: Optional[str] = None, org_id: Optional[str] = None, user: Dict[str, Any] = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT id, org_id, email, full_name, role, employee_id, specialization, avatar_initials, phone, status, created_at FROM users WHERE status = 'active'"
    params = []

    target_org = org_id or user.get("org_id")
    if target_org:
        query += " AND org_id = ?"
        params.append(target_org)

    if role:
        query += " AND role = ?"
        params.append(role)

    query += " ORDER BY full_name ASC"
    cur.execute(query, params)
    raw_users = [dict(r) for r in cur.fetchall()]
    conn.close()
    for u in raw_users:
        if 'created_at' in u and u['created_at'] is not None:
            u['created_at'] = str(u['created_at'])
    return {"status": "success", "users": raw_users}

@app.post("/api/auth/register-org-admin")
def register_org_admin_endpoint(req: RegisterOrgAdminRequest):
    """
    Public endpoint to create a new Enterprise Organization and register
    its Master Administrator following the hierarchy:
    Organization -> Admins -> QC Leads -> Inspection Engineers.
    """
    org_name = req.org_name.strip()
    admin_email = req.admin_email.strip().lower()
    if not org_name:
        raise HTTPException(status_code=400, detail="Organization name is required.")
    if not admin_email or "@" not in admin_email:
        raise HTTPException(status_code=400, detail="Valid administrator email is required.")
    if len(req.admin_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"User with email '{admin_email}' already exists.")

    # Unique organization slug
    clean_slug = "".join(c.lower() if c.isalnum() else "-" for c in org_name).strip("-")[:12]
    org_id = f"org-{clean_slug}-{int(time.time()) % 1000}"
    org_code = (req.org_code or clean_slug[:8]).upper()
    domain = admin_email.split("@")[1] if "@" in admin_email else None

    cur.execute("""
        INSERT INTO organizations (id, name, code, domain, industry, address, status)
        VALUES (?, ?, ?, ?, ?, ?, 'active')
    """, (org_id, org_name, org_code, domain, req.industry, req.address))

    admin_id = f"usr-adm-{uuid.uuid4().hex[:8]}"
    hashed_pw = hash_password(req.admin_password)
    parts = req.admin_name.strip().split()
    initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper() if parts else "AD"
    emp_id = "ADM-001"

    cur.execute("""
        INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, avatar_initials, phone, status)
        VALUES (?, ?, ?, ?, ?, 'admin', ?, 'Platform & Organization Administrator', ?, ?, 'active')
    """, (admin_id, org_id, admin_email, hashed_pw, req.admin_name, emp_id, initials, req.admin_phone))

    conn.commit()
    conn.close()

    token = create_access_token(
        user_id=admin_id,
        org_id=org_id,
        role="admin",
        email=admin_email,
        full_name=req.admin_name,
        employee_id=emp_id
    )

    return {
        "status": "success",
        "message": f"Organization '{org_name}' registered successfully with Master Administrator {req.admin_name}.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": admin_id,
            "email": admin_email,
            "full_name": req.admin_name,
            "role": "admin",
            "employee_id": emp_id,
            "org_id": org_id,
            "avatar_initials": initials
        },
        "organization": {
            "id": org_id,
            "name": org_name,
            "code": org_code,
            "domain": domain,
            "industry": req.industry,
            "address": req.address
        }
    }

@app.post("/api/auth/organizations")
def create_organization_endpoint(req: CreateOrgRequest, user: Dict[str, Any] = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only System Administrators can create new organizations.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO organizations (id, name, code, domain, industry, address) VALUES (?, ?, ?, ?, ?, ?)", (req.id, req.name, req.code, req.domain, req.industry, req.address))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Organization '{req.name}' created successfully."}

@app.post("/api/auth/register")
def register_user_endpoint(req: CreateUserRequest):
    """
    Public registration endpoint allowing team members to create new logins
    under an existing enterprise organization.
    """
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email address is required.")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"User with email '{email}' already exists.")

    cur.execute("SELECT id, name FROM organizations WHERE id = ?", (req.org_id,))
    org_row = cur.fetchone()
    if not org_row:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Organization '{req.org_id}' not found.")

    org_dict = dict(org_row)
    user_id = f"usr-{uuid.uuid4().hex[:8]}"
    hashed_pw = hash_password(req.password)
    parts = req.full_name.strip().split()
    initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper() if parts else "QC"
    cur.execute("SELECT COUNT(*) as count FROM users")
    count_row = cur.fetchone()
    next_num = ((dict(count_row)["count"] if count_row else 1) + 1001)
    emp_id = req.employee_id or f"EMP-{next_num}"

    cur.execute("""
        INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, avatar_initials, phone, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """, (user_id, req.org_id, email, hashed_pw, req.full_name, req.role, emp_id, req.specialization, initials, req.phone))
    conn.commit()
    conn.close()

    token = create_access_token(
        user_id=user_id,
        org_id=req.org_id,
        role=req.role,
        email=email,
        full_name=req.full_name,
        employee_id=emp_id
    )

    return {
        "status": "success",
        "message": f"Account created successfully for {req.full_name}.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email,
            "full_name": req.full_name,
            "role": req.role,
            "employee_id": emp_id,
            "org_id": req.org_id,
            "avatar_initials": initials
        },
        "organization": org_dict
    }

@app.post("/api/auth/users")
def create_user_by_admin(req: CreateUserRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """Admin / Lead user creation endpoint."""
    if user.get("role") not in ("admin", "qc_lead"):
        raise HTTPException(status_code=403, detail="Only Admins and QC Leads can create users via this endpoint.")
    return register_user_endpoint(req)

@app.get("/api/summary")
def get_dashboard_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM non_conformities WHERE status != 'Closed' AND sev = 'critical'")
    crit_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM approvals WHERE status = 'Pending'")
    appr_count = cur.fetchone()[0]

    today_str = datetime.now().strftime("%Y-%m-%d")
    cur.execute("SELECT COUNT(*) FROM non_conformities WHERE status != 'Closed' AND due_date < ?", (today_str,))
    overdue_ncs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM inspections WHERE status IN ('Required','Allocated','In progress') AND due_date < ?", (today_str,))
    overdue_ins = cur.fetchone()[0]

    # Engineer workloads
    cur.execute("""
        SELECT eng, COUNT(*) as active_count
        FROM inspections
        WHERE status IN ('Allocated', 'In progress') AND eng IS NOT NULL
        GROUP BY eng
    """)
    eng_loads = {row['eng']: row['active_count'] for row in cur.fetchall()}

    conn.close()
    return {
        "critical_open_ncs": crit_count,
        "pending_approvals": appr_count,
        "overdue_items": overdue_ncs + overdue_ins,
        "overdue_ncs": overdue_ncs,
        "overdue_inspections": overdue_ins,
        "engineer_loads": eng_loads
    }

# ----------------- PROJECTS -----------------

@app.get("/api/projects")
def list_projects(status: Optional[str] = None, q: Optional[str] = None, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM projects WHERE 1=1"
    params = []

    # Enforce Multi-Tenant Organization Isolation
    if user and user.get("org_id"):
        query += " AND org_id = ?"
        params.append(user["org_id"])
    elif not user:
        # Default preview for unauthenticated demo visitors
        query += " AND (org_id = 'org-psv' OR org_id IS NULL)"

    if status and status != "all":
        query += " AND status = ?"
        params.append(status)

    if q:
        query += " AND (name LIKE ? OR code LIKE ? OR loc LIKE ? OR type LIKE ?)"
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    query += " ORDER BY name ASC"
    cur.execute(query, params)
    rows = cur.fetchall()

    projects = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    for r in rows:
        p = dict(r)
        pid = p['id']

        # Get counts for project metrics
        cur.execute("SELECT COUNT(*) FROM non_conformities WHERE project_id = ? AND status != 'Closed'", (pid,))
        open_ncs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM non_conformities WHERE project_id = ? AND status != 'Closed' AND sev = 'critical'", (pid,))
        crit_ncs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM non_conformities WHERE project_id = ? AND status != 'Closed' AND due_date < ?", (pid, today_str))
        overdue_ncs = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM approvals WHERE project_id = ? AND status = 'Pending'", (pid,))
        approvals_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM action_items WHERE project_id = ? AND is_resolved = false", (pid,))
        actions_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM action_items WHERE project_id = ? AND is_resolved = false AND due_date < ?", (pid, today_str))
        actions_overdue = cur.fetchone()[0]

        p['metrics'] = {
            "open_ncs": open_ncs,
            "crit_ncs": crit_ncs,
            "overdue_ncs": overdue_ncs,
            "approvals": approvals_count,
            "actions": actions_count,
            "actions_overdue": actions_overdue
        }
        projects.append(p)

    conn.close()
    return projects

@app.post("/api/projects")
def create_project_endpoint(req: ProjectCreate, user: Dict[str, Any] = Depends(get_current_user)):
    org_id = req.org_id or user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization ID is required to create a project.")

    conn = get_connection()
    cur = conn.cursor()

    ts = int(time.time())
    clean_name = "".join(c.lower() if c.isalnum() else "" for c in req.name)[:8] or "prj"
    pid = req.id or f"prj-{clean_name}-{ts % 1000}"
    pcode = req.code or f"PRJ-{ts % 10000:04d}"

    cur.execute("SELECT id FROM projects WHERE id = ? OR code = ?", (pid, pcode))
    if cur.fetchone():
        pid = f"prj-{clean_name}-{ts % 10000}"
        pcode = f"PRJ-{ts % 100000:05d}"

    now_iso = datetime.now().isoformat()
    actor = user.get("full_name") or "QC Lead"

    cur.execute("""
        INSERT INTO projects (id, code, name, type, loc, geo, status, progress, start_date, end_date, hold_reason, closed_extra, upd_at, upd_by, org_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
    """, (pid, pcode, req.name, req.type, req.loc, req.geo or "28.5383° N, 77.3720° E", req.status, req.progress, req.start_date, req.end_date, req.hold_reason, now_iso, actor, org_id))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Project '{req.name}' created successfully.",
        "project": {
            "id": pid,
            "code": pcode,
            "name": req.name,
            "type": req.type,
            "loc": req.loc,
            "geo": req.geo,
            "status": req.status,
            "progress": req.progress,
            "start": req.start_date,
            "end": req.end_date,
            "org_id": org_id,
            "ncs": [],
            "ins": [],
            "approvals": [],
            "actions": []
        }
    }

@app.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    p_row = cur.fetchone()
    if not p_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    p = dict(p_row)

    # Fetch NCs
    cur.execute("SELECT * FROM non_conformities WHERE project_id = ? ORDER BY due_date ASC", (project_id,))
    p['ncs'] = [dict(r) for r in cur.fetchall()]

    # Fetch Inspections
    cur.execute("SELECT * FROM inspections WHERE project_id = ? ORDER BY due_date ASC", (project_id,))
    p['inspections'] = [dict(r) for r in cur.fetchall()]

    # Fetch Approvals
    cur.execute("SELECT * FROM approvals WHERE project_id = ? AND status = 'Pending' ORDER BY at_time DESC", (project_id,))
    p['approvals'] = [dict(r) for r in cur.fetchall()]

    # Fetch Actions
    cur.execute("SELECT * FROM action_items WHERE project_id = ? AND is_resolved = false ORDER BY due_date ASC", (project_id,))
    p['actions'] = [dict(r) for r in cur.fetchall()]

    conn.close()
    return p

# ----------------- NON-CONFORMITIES (NCs) -----------------

@app.get("/api/ncs")
def list_ncs(project_id: Optional[str] = None, status: Optional[str] = None, sev: Optional[str] = None, q: Optional[str] = None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT n.*, p.name as project_name, p.geo as project_geo
        FROM non_conformities n
        JOIN projects p ON n.project_id = p.id
        WHERE 1=1
    """
    params = []

    if project_id:
        query += " AND n.project_id = ?"
        params.append(project_id)

    if status == "open":
        query += " AND n.status != 'Closed'"
    elif status == "closed":
        query += " AND n.status = 'Closed'"
    elif status and status != "all":
        query += " AND n.status = ?"
        params.append(status)

    if sev and sev != "all":
        query += " AND n.sev = ?"
        params.append(sev)

    if q:
        query += " AND (n.title LIKE ? OR n.code LIKE ? OR n.assigned LIKE ? OR n.zone LIKE ?)"
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    query += " ORDER BY CASE n.status WHEN 'Closed' THEN 2 ELSE 1 END, n.due_date ASC"
    cur.execute(query, params)
    ncs = [dict(r) for r in cur.fetchall()]
    conn.close()
    return ncs

@app.get("/api/ncs/{code}")
def get_nc_detail(code: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT n.*, p.name as project_name, p.geo as project_geo
        FROM non_conformities n
        JOIN projects p ON n.project_id = p.id
        WHERE n.code = ?
    """, (code,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="NC not found")

    nc = dict(row)

    # Fetch audit logs
    cur.execute("SELECT * FROM nc_audit_logs WHERE nc_code = ? ORDER BY event_date ASC, id ASC", (code,))
    nc['logs'] = [dict(r) for r in cur.fetchall()]

    # Fetch evidence photos
    cur.execute("SELECT * FROM evidence_photos WHERE nc_code = ? ORDER BY id ASC", (code,))
    nc['photos'] = [dict(r) for r in cur.fetchall()]

    # Check if there is an approval requesting closure
    cur.execute("SELECT * FROM approvals WHERE ref_nc = ? AND status = 'Pending'", (code,))
    ap_row = cur.fetchone()
    nc['closure_approval'] = dict(ap_row) if ap_row else None

    conn.close()
    return nc

@app.post("/api/ncs/{code}/action")
def execute_nc_action(code: str, req: NCActionRequest):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM non_conformities WHERE code = ?", (code,))
    nc_row = cur.fetchone()
    if not nc_row:
        conn.close()
        raise HTTPException(status_code=404, detail="NC not found")

    nc = dict(nc_row)
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    action = req.action.lower()
    msg = ""

    if action == "verify":
        new_status = "Under verification"
        cur.execute("UPDATE non_conformities SET status = ? WHERE code = ?", (new_status, code))
        cur.execute("INSERT INTO nc_audit_logs (nc_code, event_date, what, message) VALUES (?, ?, ?, ?)",
                    (code, today_str, "Sent for verification", f"Re-inspection scheduled by {req.user}"))
        msg = f"NC {code} sent for verification on site"

    elif action == "close":
        new_status = "Closed"
        cur.execute("UPDATE non_conformities SET status = ?, closed_date = ? WHERE code = ?", (new_status, today_str, code))
        cur.execute("INSERT INTO nc_audit_logs (nc_code, event_date, what, message) VALUES (?, ?, ?, ?)",
                    (code, today_str, f"Closed by {req.user}", "Closure verified and signed off."))
        # Clear related approvals and actions
        cur.execute("UPDATE approvals SET status = 'Approved' WHERE ref_nc = ?", (code,))
        cur.execute("UPDATE action_items SET is_resolved = true WHERE target_code = ?", (code,))
        # Update project timestamp
        cur.execute("UPDATE projects SET upd_at = ?, upd_by = ? WHERE id = ?", (now_str, req.user, nc['project_id']))
        msg = f"NC {code} officially closed"

    elif action == "reopen":
        new_status = "Reopened"
        cur.execute("UPDATE non_conformities SET status = ? WHERE code = ?", (new_status, code))
        cur.execute("INSERT INTO nc_audit_logs (nc_code, event_date, what, message) VALUES (?, ?, ?, ?)",
                    (code, today_str, f"Reopened by {req.user}", f"Defect persists. Sent back to {nc['assigned']}"))
        cur.execute("UPDATE approvals SET status = 'Returned' WHERE ref_nc = ?", (code,))
        msg = f"NC {code} reopened and returned to {nc['assigned']}"

    elif action == "remind":
        # Escalation / reminder
        is_late = nc['due_date'] < today_str
        what = "Escalation issued" if is_late else "Reminder sent"
        detail = f"Formal notice sent to subcontractor {nc['assigned']} ({req.note or 'SLA deadline alert'})"
        cur.execute("INSERT INTO nc_audit_logs (nc_code, event_date, what, message) VALUES (?, ?, ?, ?)",
                    (code, today_str, what, detail))
        msg = f"{what} to {nc['assigned']}"

    else:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Unsupported action: {req.action}")

    conn.commit()
    conn.close()
    return {"status": "success", "message": msg, "action": action, "code": code}

# ----------------- INSPECTIONS -----------------

@app.get("/api/inspections")
def list_inspections(project_id: Optional[str] = None, status: Optional[str] = None, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT i.*, p.name as project_name
        FROM inspections i
        JOIN projects p ON i.project_id = p.id
        WHERE 1=1
    """
    params = []
    if user and user.get("org_id"):
        query += " AND p.org_id = ?"
        params.append(user["org_id"])
    elif not user:
        query += " AND (p.org_id = 'org-psv' OR p.org_id IS NULL)"

    if project_id:
        query += " AND i.project_id = ?"
        params.append(project_id)
    if status and status != "all":
        query += " AND i.status = ?"
        params.append(status)

    query += " ORDER BY i.due_date ASC"
    cur.execute(query, params)
    inspections = [dict(r) for r in cur.fetchall()]
    conn.close()
    return inspections

@app.get("/api/inspections/next-id")
def get_next_inspection_id_endpoint(project_id: str = "psv"):
    try:
        next_id = AllocationService.get_next_inspection_id(project_id)
        return {"status": "success", "next_id": next_id, "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inspections/{code}")
def get_inspection_detail(code: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT i.*, p.name as project_name
        FROM inspections i
        JOIN projects p ON i.project_id = p.id
        WHERE i.code = ?
    """, (code,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Inspection not found")

    ins = dict(row)
    cur.execute("SELECT * FROM approvals WHERE ref_ins = ? AND status = 'Pending'", (code,))
    ap = cur.fetchone()
    ins['approval'] = dict(ap) if ap else None

    conn.close()
    return ins

@app.post("/api/inspections/{code}/allocate")
def allocate_engineer(code: str, req: AllocateEngineerRequest):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM inspections WHERE code = ?", (code,))
    ins_row = cur.fetchone()
    if not ins_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Inspection not found")

    ins = dict(ins_row)
    new_status = "Allocated" if ins['status'] == "Required" else ins['status']

    cur.execute("UPDATE inspections SET eng = ?, status = ? WHERE code = ?", (req.engineer_name, new_status, code))
    cur.execute("UPDATE action_items SET is_resolved = true WHERE target_code = ?", (code,))

    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Inspection {code} allocated to {req.engineer_name}"}

@app.post("/api/inspections/{code}/nudge")
def nudge_engineer(code: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT eng FROM inspections WHERE code = ?", (code,))
    row = cur.fetchone()
    conn.close()

    if not row or not row['eng']:
        raise HTTPException(status_code=400, detail="No engineer assigned to this inspection")

    return {"status": "success", "message": f"Chased engineer {row['eng']} for inspection {code}"}

@app.post("/api/inspections/{code}/generate-report")
def generate_inspection_report_endpoint(code: str, user: str = "Priya Deshmukh (QC Lead)"):
    try:
        report = InspectionReportService.generate_inspection_report(code, user_name=user)
        return {"status": "success", "report": report}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inspections/{code}/report")
def get_inspection_report_endpoint(code: str):
    report = InspectionReportService.get_latest_report(code)
    if not report:
        raise HTTPException(status_code=404, detail="No report generated yet for this inspection")
    return {"status": "success", "report": report}

# ----------------- STAGE-BASED INSPECTION ALLOCATION MODULE -----------------

@app.get("/api/master-checklist")
def get_master_checklist_endpoint(
    stage_id: Optional[str] = None,
    building_type: Optional[str] = None,
    priority: Optional[str] = None,
    q: Optional[str] = None
):
    try:
        checklist = AllocationService.get_master_checklist(
            stage_id=stage_id,
            building_type=building_type,
            priority=priority,
            search_q=q
        )
        return {"status": "success", "stages": checklist, "total_stages": len(checklist)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/allocations")
def create_allocation_endpoint(req: CreateAllocationRequest):
    try:
        result = AllocationService.create_allocation(req.dict())
        return {"status": "success", "allocation": result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/allocations")
def list_allocations_endpoint(
    project_id: Optional[str] = None,
    engineer_name: Optional[str] = None,
    status: Optional[str] = None
):
    try:
        allocations = AllocationService.list_allocations(
            project_id=project_id,
            engineer_name=engineer_name,
            status=status
        )
        return {"status": "success", "allocations": allocations, "count": len(allocations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/allocations/{allocation_id}")
def get_allocation_detail_endpoint(allocation_id: str):
    alloc = AllocationService.get_allocation_detail(allocation_id)
    if not alloc:
        raise HTTPException(status_code=404, detail=f"Allocation '{allocation_id}' not found.")
    return {"status": "success", "allocation": alloc}

@app.post("/api/allocations/{allocation_id}/checkpoint-result")
def update_checkpoint_result_endpoint(allocation_id: str, req: CheckpointResultRequest):
    try:
        res = AllocationService.update_checkpoint_result(
            alloc_id=allocation_id,
            checkpoint_id=req.checkpoint_id,
            result_status=req.result_status,
            observations=req.observations,
            photo_url=req.photo_url,
            inspected_by=req.inspected_by or "Inspection Engineer"
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/allocations/{allocation_id}/submit")
def submit_allocation_endpoint(allocation_id: str, req: SubmitAllocationRequest):
    try:
        res = AllocationService.submit_allocation(
            alloc_id=allocation_id,
            submitted_by=req.submitted_by or "Inspection Engineer",
            notes=req.notes
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/allocations/{allocation_id}/review")
def review_allocation_endpoint(allocation_id: str, req: ReviewAllocationRequest):
    try:
        res = AllocationService.review_allocation(
            alloc_id=allocation_id,
            decision=req.decision,
            reviewer_name=req.reviewer_name or "Priya Deshmukh (QC Lead)",
            comments=req.comments
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/allocations/{allocation_id}/reassign")
def reassign_allocation_endpoint(allocation_id: str, req: ReassignAllocationRequest):
    try:
        res = AllocationService.reassign_allocation(
            alloc_id=allocation_id,
            new_engineer=req.new_engineer,
            reason=req.reason or "Engineer reassigned by QC Lead",
            new_due_date=req.new_due_date,
            actor_name=req.actor_name or "Priya Deshmukh (QC Lead)"
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- REVISED INSPECTION WORKFLOW ENDPOINTS -----------------

@app.get("/api/inspections/next-id")
def get_next_inspection_id_endpoint(project_id: str = "psv"):
    try:
        next_id = AllocationService.get_next_inspection_id(project_id)
        return {"status": "success", "next_id": next_id, "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inspections/create")
def create_inspection_endpoint(req: CreateAllocationRequest):
    try:
        res = AllocationService.create_allocation(req.model_dump())
        return {"status": "success", "allocation": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inspections/{code}/change-engineer")
def change_engineer_endpoint(code: str, req: ReassignAllocationRequest):
    try:
        eng_target = req.new_engineer or req.new_engineer_name or req.new_engineer_id or ""
        res = AllocationService.reassign_allocation(
            alloc_id=code,
            new_engineer=eng_target,
            reason=req.reason or "Engineer reassigned by QC Lead",
            new_due_date=req.new_due_date,
            actor_name=req.actor_name or "Priya Deshmukh (QC Lead)"
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inspections/{code}/status")
def update_inspection_status_endpoint(code: str, req: ChangeStatusRequest):
    try:
        res = AllocationService.update_inspection_status(
            alloc_id=code,
            new_status=req.status,
            actor_name=req.actor_name or "Priya Deshmukh (QC Lead)",
            reason=req.reason
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- PHASE 6: INSPECTION ENGINEER WORKSPACE -----------------

@app.get("/api/engineers")
def list_engineers_endpoint():
    from allocation_service import ENGINEER_REGISTRY
    return {"status": "success", "engineers": list(ENGINEER_REGISTRY.values())}

@app.get("/api/engineer/{engineer_id}/dashboard")
def get_engineer_dashboard_endpoint(
    engineer_id: str,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    stage: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
):
    try:
        user_org = user.get("org_id") if user else None
        data = AllocationService.get_engineer_dashboard_data(
            engineer_id_or_name=engineer_id,
            status_filter=status,
            project_filter=project_id,
            stage_filter=stage,
            priority_filter=priority,
            search_q=search,
            org_id=user_org
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/allocations/{allocation_id}/save-progress")
def save_allocation_progress_endpoint(allocation_id: str, req: SaveProgressRequest):
    try:
        checkpoints_data = [cp.model_dump() for cp in req.checkpoints]
        res = AllocationService.save_progress(
            alloc_id=allocation_id,
            checkpoints_data=checkpoints_data,
            saved_by=req.saved_by or "Inspection Engineer"
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/allocations/{allocation_id}/upload-evidence")
async def upload_evidence_endpoint(
    allocation_id: str,
    file: Optional[UploadFile] = None,
    payload: Optional[UploadEvidencePayload] = None
):
    import base64
    import uuid

    upload_dir = os.path.join("static", "uploads", "evidence")
    os.makedirs(upload_dir, exist_ok=True)

    unique_suffix = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
    saved_url = ""
    raw_bytes = None
    content_type = "image/jpeg"
    clean_name = f"evidence_{allocation_id}_{unique_suffix}.jpg"

    if file:
        orig_ext = os.path.splitext(file.filename)[1] or ".jpg"
        clean_name = f"evidence_{allocation_id}_{unique_suffix}{orig_ext}"
        target_path = os.path.join(upload_dir, clean_name)
        raw_bytes = await file.read()
        content_type = file.content_type or "image/jpeg"
        with open(target_path, "wb") as f:
            f.write(raw_bytes)
        saved_url = f"/static/uploads/evidence/{clean_name}"
    elif payload and payload.data_url:
        data_parts = payload.data_url.split(",", 1)
        b64_data = data_parts[1] if len(data_parts) > 1 else data_parts[0]
        ext = ".jpg"
        content_type = "image/jpeg"
        if "data:image/png" in payload.data_url:
            ext = ".png"
            content_type = "image/png"
        elif "data:image/webp" in payload.data_url:
            ext = ".webp"
            content_type = "image/webp"
        clean_name = f"evidence_{allocation_id}_{unique_suffix}{ext}"
        target_path = os.path.join(upload_dir, clean_name)
        raw_bytes = base64.b64decode(b64_data)
        with open(target_path, "wb") as f:
            f.write(raw_bytes)
        saved_url = f"/static/uploads/evidence/{clean_name}"
    else:
        # Default placeholder evidence path
        clean_name = f"evidence_{allocation_id}_{unique_suffix}.jpg"
        saved_url = f"/static/uploads/evidence/{clean_name}"

    # Supabase Storage Integration (if configured)
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if supabase_url and supabase_key and raw_bytes:
        try:
            from supabase import create_client
            supabase_client = create_client(supabase_url, supabase_key)
            bucket_name = os.environ.get("SUPABASE_STORAGE_BUCKET", "inspection-evidence")
            storage_path = f"evidence/{clean_name}"
            supabase_client.storage.from_(bucket_name).upload(
                path=storage_path,
                file=raw_bytes,
                file_options={"content-type": content_type}
            )
            public_url = supabase_client.storage.from_(bucket_name).get_public_url(storage_path)
            if public_url:
                saved_url = public_url
        except Exception as sb_err:
            print(f"[WARN] Supabase storage upload failed ({sb_err}). Keeping local file: {saved_url}")

    return {
        "status": "success",
        "url": saved_url,
        "checkpoint_id": payload.checkpoint_id if payload else None,
        "allocation_id": allocation_id
    }

# ----------------- APPROVALS -----------------

@app.get("/api/approvals")
def list_approvals(project_id: Optional[str] = None, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT a.*, p.name as project_name
        FROM approvals a
        JOIN projects p ON a.project_id = p.id
        WHERE a.status = 'Pending'
    """
    params = []
    if user and user.get("org_id"):
        query += " AND p.org_id = ?"
        params.append(user["org_id"])
    elif not user:
        query += " AND (p.org_id = 'org-psv' OR p.org_id IS NULL)"

    if project_id:
        query += " AND a.project_id = ?"
        params.append(project_id)

    query += " ORDER BY a.at_time DESC"
    cur.execute(query, params)
    approvals = [dict(r) for r in cur.fetchall()]
    conn.close()
    return approvals

@app.post("/api/approvals/{code}/action")
def execute_approval_action(code: str, req: ApprovalActionRequest):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM approvals WHERE code = ?", (code,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Approval not found")

    ap = dict(row)
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if req.action == "approve":
        cur.execute("UPDATE approvals SET status = 'Approved' WHERE code = ?", (code,))

        # If it references an inspection, mark inspection as Report issued
        if ap.get('ref_ins'):
            cur.execute("UPDATE inspections SET status = 'Report issued' WHERE code = ?", (ap['ref_ins'],))

        # If it references an NC, close the NC
        if ap.get('ref_nc'):
            cur.execute("UPDATE non_conformities SET status = 'Closed', closed_date = ? WHERE code = ?", (today_str, ap['ref_nc']))
            cur.execute("INSERT INTO nc_audit_logs (nc_code, event_date, what, message) VALUES (?, ?, ?, ?)",
                        (ap['ref_nc'], today_str, f"Closed by {req.user}", "Signed off via approval."))

        # Update project timestamp
        cur.execute("UPDATE projects SET upd_at = ?, upd_by = ? WHERE id = ?", (now_str, req.user, ap['project_id']))
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Approval {code} approved successfully"}

    elif req.action == "return":
        cur.execute("UPDATE approvals SET status = 'Returned' WHERE code = ?", (code,))
        if ap.get('ref_ins'):
            cur.execute("UPDATE inspections SET status = 'In progress' WHERE code = ?", (ap['ref_ins'],))
        if ap.get('ref_nc'):
            cur.execute("UPDATE non_conformities SET status = 'Reopened' WHERE code = ?", (ap['ref_nc'],))
            cur.execute("INSERT INTO nc_audit_logs (nc_code, event_date, what, message) VALUES (?, ?, ?, ?)",
                        (ap['ref_nc'], today_str, f"Approval returned by {req.user}", req.note or "Verification evidence insufficient."))

        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Approval {code} returned to submitter"}

    conn.close()
    raise HTTPException(status_code=400, detail="Invalid approval action")

# ----------------- ROOT & STATIC SERVING -----------------

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
@app.get("/login")
@app.get("/admin")
@app.get("/admin-dashboard")
@app.get("/qc")
@app.get("/qc-lead")
@app.get("/engineer")
@app.get("/engineer-dashboard")
def read_root():
    # Serves the audit intelligence UI
    audit_html_path = os.path.join(os.path.dirname(__file__), "static", "audit_intelligence.html")
    if os.path.exists(audit_html_path):
        return FileResponse(audit_html_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "Audit Intelligence API is running. Go to /docs for Swagger specifications."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app_audit:app", host="0.0.0.0", port=port, reload=True)
