"""Legacy inspections register and reporting router."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import admin_or_qc, qc_lead_only
from app.core.errors import NotFound
from app.core.security import Principal
from app.db.connection import Session, get_db
from app.schemas.requests import (
    AllocateEngineerRequest,
    ChangeStatusRequest,
    CreateAllocationRequest,
    ReassignAllocationRequest,
)
from app.services import allocations as alloc_svc
from app.services import quality as qual_svc
from app.services import reports as report_svc

router = APIRouter(prefix="/api/inspections", tags=["inspections"])


@router.get("")
def list_inspections(
    project_id: str | None = None,
    status: str | None = None,
    p: Principal = Depends(admin_or_qc),
    db: Session = Depends(get_db),
):
    return qual_svc.list_inspections(db, p, project_id=project_id, status=status)


@router.get("/next-id")
def get_next_inspection_id(
    project_id: str,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return {"status": "success", "next_id": alloc_svc.next_inspection_id(db, p, project_id)}


@router.get("/{code}")
def get_inspection(code: str, p: Principal = Depends(admin_or_qc), db: Session = Depends(get_db)):
    return qual_svc.inspection_detail(db, p, code)


@router.post("/create")
def create_inspection(
    req: CreateAllocationRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.create_allocation(db, p, req)


@router.post("/{code}/allocate")
def allocate_inspection(
    code: str,
    req: AllocateEngineerRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    ref = req.engineer_id or req.engineer_name or ""
    return qual_svc.allocate_legacy(db, p, code, ref)


@router.post("/{code}/nudge")
def nudge_engineer(code: str, p: Principal = Depends(qc_lead_only), db: Session = Depends(get_db)):
    return qual_svc.nudge(db, p, code)


@router.post("/{code}/change-engineer")
def change_engineer(
    code: str,
    req: ReassignAllocationRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.reassign(db, p, code, req.target, req.reason, req.new_due_date)


@router.post("/{code}/status")
def change_status(
    code: str,
    req: ChangeStatusRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.change_status(db, p, code, req.status, req.reason)


@router.post("/{code}/generate-report")
def generate_report(code: str, p: Principal = Depends(qc_lead_only), db: Session = Depends(get_db)):
    return report_svc.generate(db, p, code)


@router.get("/{code}/report")
def get_report(code: str, p: Principal = Depends(admin_or_qc), db: Session = Depends(get_db)):
    rep = report_svc.latest(db, p, code)
    if not rep:
        raise NotFound("Report not found.")
    return rep
