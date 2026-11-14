"""Health check and removed endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import Gone

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/api/health")
def health_check():
    return {"status": "ok", "app": "SiteIQ Audit Intelligence"}


@router.post("/api/seed")
def seed_disabled():
    raise Gone("Database reset via /api/seed is permanently disabled. Use scripts/seed_demo.py.")
