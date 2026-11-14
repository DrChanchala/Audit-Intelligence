"""Domain errors. Services raise these; one handler maps them to HTTP.

Keeps HTTP concerns out of services and guarantees internal exception text
never leaks to clients.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger("siteiq")


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class ValidationFailed(DomainError):
    status_code = 400


class Unauthorized(DomainError):
    status_code = 401


class Forbidden(DomainError):
    status_code = 403


class NotFound(DomainError):
    """Also used for resources in another tenant, so existence is not leaked."""
    status_code = 404


class Conflict(DomainError):
    status_code = 409


class Gone(DomainError):
    status_code = 410


class TooManyRequests(DomainError):
    status_code = 429


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = [
            {"field": ".".join(str(p) for p in e.get("loc", [])[1:]), "message": e.get("msg")}
            for e in exc.errors()
        ]
        return JSONResponse({"detail": "Invalid request.", "errors": errors}, status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        ref = uuid.uuid4().hex[:10]
        log.exception("Unhandled error ref=%s path=%s", ref, request.url.path)
        return JSONResponse({"detail": f"Internal error (ref {ref})."}, status_code=500)
