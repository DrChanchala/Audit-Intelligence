"""Page routing and server-side role guards."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.core.deps import optional_principal
from app.core.security import Principal, Role
from app.db.connection import Session, get_db

router = APIRouter(include_in_schema=False)

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_TEMPLATES_DIR = _BASE_DIR / "templates"
_LEGACY_SPA_PATH = _BASE_DIR / "archive" / "legacy-spa" / "audit_intelligence.html"

templates = Jinja2Templates(directory=_TEMPLATES_DIR)
_settings = get_settings()
templates.env.globals["asset_version"] = _settings.asset_version


def _serve_legacy_spa() -> HTMLResponse:
    if _LEGACY_SPA_PATH.exists():
        return HTMLResponse(_LEGACY_SPA_PATH.read_text(encoding="utf-8"))
    return HTMLResponse("<!doctype html><html><body><h1>SiteIQ Audit Intelligence</h1></body></html>")


def _get_user_context(p: Principal | None, db: Session) -> dict | None:
    if not p:
        return None
    user_row = db.one("SELECT id, full_name, email, role, org_id FROM users WHERE id = ?", (p.user_id,))
    org_row = db.one("SELECT name FROM organizations WHERE id = ?", (p.org_id,)) if p.org_id else None
    return {
        "id": p.user_id,
        "name": user_row["full_name"] if user_row else p.user_id,
        "email": user_row["email"] if user_row else "",
        "role": p.role.value,
        "org_id": p.org_id,
        "org_name": org_row["name"] if org_row else "",
    }


def _guard(request: Request, required: Role) -> RedirectResponse | None:
    p = optional_principal(request)
    if not p:
        return RedirectResponse(f"/login?next={request.url.path}", status_code=302)
    if p.role != required:
        return RedirectResponse(p.role.home, status_code=302)
    return None


@router.get("/")
@router.get("/login")
def landing(request: Request, db: Session = Depends(get_db)):
    p = optional_principal(request)
    if p:
        return RedirectResponse(p.role.home, status_code=302)
    return templates.TemplateResponse(request=request, name="landing.html", context={"user": None})


@router.get("/admin")
@router.get("/admin-dashboard")
def admin_page(request: Request, db: Session = Depends(get_db)):
    guard = _guard(request, Role.ADMIN)
    if guard:
        return guard
    p = optional_principal(request)
    user_ctx = _get_user_context(p, db)
    return templates.TemplateResponse(request=request, name="admin.html", context={"user": user_ctx})


@router.get("/qc")
@router.get("/qc-lead")
def qc_page(request: Request):
    # In Phase 5, /qc keeps the legacy SPA until Phase 6
    guard = _guard(request, Role.QC_LEAD)
    if guard:
        return guard
    return _serve_legacy_spa()


@router.get("/engineer")
@router.get("/engineer-dashboard")
def engineer_page(request: Request):
    # In Phase 5, /engineer keeps the legacy SPA until Phase 7
    guard = _guard(request, Role.ENGINEER)
    if guard:
        return guard
    return _serve_legacy_spa()


@router.get("/dashboard")
@router.get("/inspections")
@router.get("/allocations")
def role_page_alias(request: Request):
    p = optional_principal(request)
    if not p:
        return RedirectResponse(f"/login?next={request.url.path}", status_code=302)
    return RedirectResponse(p.role.home, status_code=302)
