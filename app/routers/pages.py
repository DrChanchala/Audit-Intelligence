"""Page routing and server-side role guards."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.deps import optional_principal
from app.core.security import Role

router = APIRouter(include_in_schema=False)
_LEGACY_SPA_PATH = Path(__file__).resolve().parent.parent.parent / "archive" / "legacy-spa" / "audit_intelligence.html"


def _serve_spa() -> HTMLResponse:
    if _LEGACY_SPA_PATH.exists():
        return HTMLResponse(_LEGACY_SPA_PATH.read_text(encoding="utf-8"))
    return HTMLResponse("<!doctype html><html><body><h1>SiteIQ Audit Intelligence</h1></body></html>")


def _guard(request: Request, required: Role):
    p = optional_principal(request)
    if not p:
        return RedirectResponse(f"/login?next={request.url.path}", status_code=302)
    if p.role != required:
        return RedirectResponse(p.role.home, status_code=302)
    return None


@router.get("/")
@router.get("/login")
def landing(request: Request):
    p = optional_principal(request)
    if p and request.url.path == "/login":
        return RedirectResponse(p.role.home, status_code=302)
    return _serve_spa()


@router.get("/admin")
@router.get("/admin-dashboard")
def admin_page(request: Request):
    r = _guard(request, Role.ADMIN)
    if r:
        return r
    return _serve_spa()


@router.get("/qc")
@router.get("/qc-lead")
def qc_page(request: Request):
    r = _guard(request, Role.QC_LEAD)
    if r:
        return r
    return _serve_spa()


@router.get("/engineer")
@router.get("/engineer-dashboard")
def engineer_page(request: Request):
    r = _guard(request, Role.ENGINEER)
    if r:
        return r
    return _serve_spa()
