"""Engineer workspace dashboard routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import any_user, engineer_only
from app.core.security import Principal
from app.db.connection import Session, get_db
from app.services import allocations as svc

router = APIRouter(prefix="/api/engineer", tags=["engineer"])


@router.get("/me/dashboard")
def my_dashboard(
    status: str | None = None,
    project: str | None = None,
    stage: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    p: Principal = Depends(engineer_only),
    db: Session = Depends(get_db),
):
    return svc.engineer_dashboard(
        db, p, status=status, project=project, stage=stage, priority=priority, search=search
    )


@router.get("/{id}/dashboard")
def engineer_dashboard_by_id(
    id: str,
    status: str | None = None,
    project: str | None = None,
    stage: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    p: Principal = Depends(any_user),
    db: Session = Depends(get_db),
):
    return svc.engineer_dashboard(
        db, p, engineer_ref=id, status=status, project=project, stage=stage, priority=priority, search=search
    )
