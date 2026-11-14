"""SiteIQ Audit Intelligence Application Factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db.connection import get_database
from app.db.schema import init_schema, load_master_checklist
from app.routers import (
    admin,
    allocations,
    auth,
    engineer,
    evidence,
    health,
    inspections,
    pages,
    quality,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure schema and master checklist exist
    db = get_database()
    with db.session() as s:
        init_schema(s)
        load_master_checklist(s)
    yield
    # Shutdown
    db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate()

    app = FastAPI(
        title="SiteIQ Audit Intelligence",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS: only if explicitly configured (none by default, same-origin app)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Security & caching headers middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(self), geolocation=(self)")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob: https://*.supabase.co; "
            "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
        )
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        ctype = response.headers.get("content-type", "")
        if "text/html" in ctype:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        elif request.url.path.startswith("/static/"):
            if "v=" in request.url.query:
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                response.headers["Cache-Control"] = "no-cache"

        return response

    install_error_handlers(app)

    # Include API and page routers
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(quality.router)
    app.include_router(inspections.router)
    app.include_router(allocations.router)
    app.include_router(engineer.router)
    app.include_router(evidence.router)
    app.include_router(health.router)
    app.include_router(pages.router)

    # Mount static assets
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app


app = create_app()
