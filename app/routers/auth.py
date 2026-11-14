"""Sign-in, organization sign-up, session and user provisioning."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request, Response

from app.core.config import get_settings
from app.core.deps import admin_or_qc, any_user
from app.core.errors import Forbidden, Gone
from app.core.security import SESSION_COOKIE, Principal, Role, create_token, login_limiter, signup_limiter
from app.db.connection import Session, get_db
from app.schemas.requests import CreateUserRequest, LoginRequest, RegisterOrgAdminRequest
from app.services import auth as svc

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _session_response(response: Response, user: dict, org: dict | None, message: str) -> dict:
    s = get_settings()
    token = create_token(user)
    response.set_cookie(SESSION_COOKIE, token, max_age=s.jwt_ttl_seconds, httponly=True, secure=s.is_production,
                        samesite="lax", path="/")
    role = Role(user["role"])
    return {
        "status": "success", "message": message,
        # Kept for API clients / backwards compatibility. Browsers use the HttpOnly cookie instead.
        "access_token": token, "token_type": "bearer",
        "home": role.home,
        "user": {k: user.get(k) for k in ("id", "email", "full_name", "role", "employee_id", "specialization",
                                          "avatar_initials", "org_id")},
        "organization": org,
    }


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    login_limiter.check(f"{_client_ip(request)}:{req.email.lower()}")
    user, org = svc.authenticate(db, req.email, req.password, req.org_id)
    return _session_response(response, user, org, "Authentication successful")


@router.post("/register-org-admin")
def register_org_admin(req: RegisterOrgAdminRequest, request: Request, response: Response,
                       db: Session = Depends(get_db)):
    if not get_settings().allow_public_org_signup:
        raise Forbidden("Organization sign-up is invite-only. Contact the platform team.")
    signup_limiter.check(_client_ip(request))
    user, org = svc.register_organization(db, req)
    return _session_response(response, user, org, f"Organization '{org['name']}' created.")


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "success"}


@router.get("/me")
def me(p: Principal = Depends(any_user), db: Session = Depends(get_db)):
    user, org = svc.profile(db, p)
    return {"status": "success", "user": user, "organization": org, "home": p.role.home}


@router.get("/organizations")
def my_organization(p: Principal = Depends(any_user), db: Session = Depends(get_db)):
    """Previously public and listed every tenant. Now returns only the caller's organization."""
    _, org = svc.profile(db, p)
    return {"status": "success", "organizations": [org] if org else []}


@router.post("/organizations")
def create_organization_disabled(_: Principal = Depends(any_user)):
    raise Gone("Creating organizations from inside another organization is not supported. Use sign-up.")


@router.post("/register")
def public_register_disabled():
    """Previously let anyone create any role (incl. admin) in any org. Accounts are now provisioned by admins."""
    raise Gone("Self-registration is disabled. Ask your organization admin to create your account.")


@router.get("/users")
def list_users(role: Optional[str] = None, org_id: Optional[str] = None, p: Principal = Depends(admin_or_qc),
               db: Session = Depends(get_db)):
    # org_id is accepted for compatibility but always pinned to the caller's org.
    return {"status": "success", "users": svc.list_users(db, p, role)}


@router.post("/users")
def create_user(req: CreateUserRequest, p: Principal = Depends(admin_or_qc), db: Session = Depends(get_db)):
    user = svc.provision_user(db, p, req)
    return {"status": "success", "message": f"Account created for {user['full_name']}.", "user": user}
