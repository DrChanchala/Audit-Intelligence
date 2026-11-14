"""FastAPI dependencies for authentication and role-based access.

Every protected endpoint declares exactly which roles may call it:

    @router.post("/x")
    def x(p: Principal = Depends(require_roles(Role.QC_LEAD))): ...

Browser sessions use an HttpOnly cookie (not readable by page scripts, so
XSS cannot steal it). Unsafe methods on cookie sessions must carry the
custom CSRF header, which cross-site pages cannot send. API clients may use
``Authorization: Bearer <token>`` instead (no CSRF needed).
"""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, Request

from app.core.errors import Forbidden, Unauthorized
from app.core.security import CSRF_HEADER, SESSION_COOKIE, Principal, Role, decode_token

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _token_from(request: Request) -> tuple[str | None, bool]:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None, False
    return request.cookies.get(SESSION_COOKIE), True


def optional_principal(request: Request) -> Principal | None:
    token, _ = _token_from(request)
    if not token:
        return None
    try:
        return decode_token(token)
    except Unauthorized:
        return None


def get_principal(request: Request) -> Principal:
    token, via_cookie = _token_from(request)
    if not token:
        raise Unauthorized("Authentication required. Please sign in.")
    principal = decode_token(token)
    if via_cookie and request.method not in _SAFE_METHODS and request.headers.get(CSRF_HEADER) != "1":
        raise Forbidden("Missing CSRF header.")
    return principal


def require_roles(*roles: Role) -> Callable[..., Principal]:
    allowed = set(roles)

    def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise Forbidden("Your role is not permitted to perform this action.")
        return principal

    return _dep


any_user = require_roles(Role.ADMIN, Role.QC_LEAD, Role.ENGINEER)
admin_only = require_roles(Role.ADMIN)
qc_lead_only = require_roles(Role.QC_LEAD)
engineer_only = require_roles(Role.ENGINEER)
admin_or_qc = require_roles(Role.ADMIN, Role.QC_LEAD)
