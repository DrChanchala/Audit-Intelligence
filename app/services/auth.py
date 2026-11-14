"""Organizations, users and sign-in."""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from app.core.errors import Conflict, Forbidden, Unauthorized, ValidationFailed
from app.core.security import Principal, Role, hash_password, verify_password_constant_time
from app.db.connection import Session
from app.schemas.requests import CreateUserRequest, RegisterOrgAdminRequest

USER_PUBLIC_COLUMNS = ("id, org_id, email, full_name, role, employee_id, specialization, "
                       "avatar_initials, phone, status, created_at, last_login_at")

# Which roles each role may provision. QC leads may add engineers only.
PROVISIONING_RULES = {
    Role.ADMIN: {Role.ADMIN, Role.QC_LEAD, Role.ENGINEER},
    Role.QC_LEAD: {Role.ENGINEER},
}


def _initials(name: str) -> str:
    parts = name.split()
    return ("".join(p[0] for p in parts[:2]) or "U").upper()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def public_user(row: dict) -> dict:
    return {k: row.get(k) for k in ("id", "org_id", "email", "full_name", "role", "employee_id", "specialization",
                                    "avatar_initials", "phone", "status", "created_at", "last_login_at")}


def public_org(row: dict | None) -> dict | None:
    if not row:
        return None
    return {k: row.get(k) for k in ("id", "name", "code", "domain", "industry", "address")}


def _email_taken(db: Session, email: str) -> bool:
    return bool(db.scalar("SELECT 1 FROM users WHERE LOWER(email) = LOWER(?)", (email,)))


def _next_employee_id(db: Session, org_id: str, role: Role) -> str:
    prefix = {"admin": "ADM", "qc_lead": "QCL", "engineer": "ENG"}[role.value]
    count = db.scalar("SELECT COUNT(*) FROM users WHERE org_id = ? AND role = ?", (org_id, role.value)) or 0
    return f"{prefix}-{count + 1:03d}"


def _insert_user(db: Session, *, org_id: str, email: str, password: str, full_name: str, role: Role,
                 employee_id: str | None, specialization: str | None, phone: str | None) -> dict:
    user = {
        "id": _new_id("usr"), "org_id": org_id, "email": email.lower(), "full_name": full_name, "role": role.value,
        "employee_id": employee_id or _next_employee_id(db, org_id, role), "specialization": specialization,
        "avatar_initials": _initials(full_name), "phone": phone, "status": "active",
    }
    db.execute(
        "INSERT INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, "
        "avatar_initials, phone, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')",
        (user["id"], org_id, user["email"], hash_password(password), full_name, role.value, user["employee_id"],
         specialization, user["avatar_initials"], phone),
    )
    return user


def register_organization(db: Session, req: RegisterOrgAdminRequest) -> tuple[dict, dict]:
    if _email_taken(db, req.admin_email):
        raise Conflict("An account with this email already exists.")
    slug = re.sub(r"[^A-Z0-9]", "", (req.org_code or req.org_name).upper())[:10] or "ORG"
    code = slug
    suffix = 1
    while db.scalar("SELECT 1 FROM organizations WHERE code = ?", (code,)):
        suffix += 1
        code = f"{slug}{suffix}"
    org = {"id": _new_id("org"), "name": req.org_name, "code": code, "domain": req.admin_email.split("@")[1],
           "industry": req.industry, "address": req.address}
    db.execute("INSERT INTO organizations (id, name, code, domain, industry, address, status) "
               "VALUES (?, ?, ?, ?, ?, ?, 'active')",
               (org["id"], org["name"], org["code"], org["domain"], org["industry"], org["address"]))
    user = _insert_user(db, org_id=org["id"], email=req.admin_email, password=req.admin_password,
                        full_name=req.admin_name, role=Role.ADMIN, employee_id="ADM-001",
                        specialization="Organization Administration", phone=req.admin_phone)
    return user, org


def authenticate(db: Session, email: str, password: str, org_id: str | None = None) -> tuple[dict, dict | None]:
    row = db.one("SELECT * FROM users WHERE LOWER(email) = LOWER(?) AND status = 'active'", (email,))
    if not verify_password_constant_time(password, row["password_hash"] if row else None):
        raise Unauthorized("Invalid email or password.")
    if org_id and org_id != row["org_id"]:
        raise Forbidden("User does not belong to the selected organization.")
    db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["id"]))
    org = db.one("SELECT * FROM organizations WHERE id = ?", (row["org_id"],))
    return dict(row), public_org(org)


def provision_user(db: Session, p: Principal, req: CreateUserRequest) -> dict:
    target = Role(req.role)
    if target not in PROVISIONING_RULES.get(p.role, set()):
        raise Forbidden(f"A {p.role.label} cannot create {target.label} accounts.")
    if _email_taken(db, req.email):
        raise Conflict("An account with this email already exists.")
    if req.employee_id and db.scalar("SELECT 1 FROM users WHERE org_id = ? AND employee_id = ?",
                                     (p.org_id, req.employee_id)):
        raise Conflict("Employee ID is already in use in your organization.")
    return _insert_user(db, org_id=p.org_id, email=req.email, password=req.password, full_name=req.full_name,
                        role=target, employee_id=req.employee_id, specialization=req.specialization, phone=req.phone)


def list_users(db: Session, p: Principal, role: str | None = None) -> list[dict]:
    sql = f"SELECT {USER_PUBLIC_COLUMNS} FROM users WHERE org_id = ? AND status = 'active'"
    params: list = [p.org_id]
    if role:
        if role not in {r.value for r in Role}:
            raise ValidationFailed("Unknown role filter.")
        sql += " AND role = ?"
        params.append(role)
    return [public_user(r) for r in db.all(sql + " ORDER BY full_name", params)]


def profile(db: Session, p: Principal) -> tuple[dict, dict | None]:
    user = db.one(f"SELECT {USER_PUBLIC_COLUMNS} FROM users WHERE id = ? AND org_id = ?", (p.user_id, p.org_id))
    if not user:
        raise Unauthorized("Account no longer exists.")
    return public_user(user), public_org(db.one("SELECT * FROM organizations WHERE id = ?", (p.org_id,)))


def org_kpis(db: Session, p: Principal) -> dict:
    roles = {r["role"]: r["n"] for r in db.all(
        "SELECT role, COUNT(*) AS n FROM users WHERE org_id = ? AND status = 'active' GROUP BY role", (p.org_id,))}
    projects = db.one(
        "SELECT COUNT(*) AS total, SUM(CASE WHEN status = 'live' THEN 1 ELSE 0 END) AS live "
        "FROM projects WHERE org_id = ?", (p.org_id,))
    active = db.scalar(
        "SELECT COUNT(*) FROM inspection_allocations a JOIN projects p ON a.project_id = p.id "
        "WHERE p.org_id = ? AND a.status IN ('Allocated', 'In progress', 'Pending review')", (p.org_id,))
    return {
        "projects": projects["total"] or 0, "live_projects": projects["live"] or 0,
        "admins": roles.get("admin", 0), "qc_leads": roles.get("qc_lead", 0), "engineers": roles.get("engineer", 0),
        "active_inspections": active or 0,
    }
