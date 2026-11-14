"""Quality summary, non-conformities, and approvals routers."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import admin_or_qc, qc_lead_only
from app.core.security import Principal
from app.db.connection import Session, get_db
from app.schemas.requests import ApprovalActionRequest, NCActionRequest
from app.services import quality as svc

router = APIRouter(tags=["quality"])


@router.get("/api/summary")
def get_summary(p: Principal = Depends(admin_or_qc), db: Session = Depends(get_db)):
    return svc.summary(db, p)


@router.get("/api/ncs")
def list_ncs(
    project_id: str | None = None,
    status: str | None = None,
    sev: str | None = None,
    q: str | None = None,
    p: Principal = Depends(admin_or_qc),
    db: Session = Depends(get_db),
):
    return svc.list_ncs(db, p, project_id=project_id, status=status, sev=sev, q=q)


@router.get("/api/ncs/{code}")
def get_nc(code: str, p: Principal = Depends(admin_or_qc), db: Session = Depends(get_db)):
    return svc.nc_detail(db, p, code)


@router.post("/api/ncs/{code}/action")
def act_on_nc(
    code: str,
    req: NCActionRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return svc.nc_action(db, p, code, req.action, req.note)


@router.get("/api/approvals")
def list_approvals(
    project_id: str | None = None,
    p: Principal = Depends(admin_or_qc),
    db: Session = Depends(get_db),
):
    return svc.list_approvals(db, p, project_id=project_id)


@router.post("/api/approvals/{code}/action")
def act_on_approval(
    code: str,
    req: ApprovalActionRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return svc.approval_action(db, p, code, req.action, req.note)
