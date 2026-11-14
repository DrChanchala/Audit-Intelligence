"""Inspection allocation management and checklist routing."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.deps import admin_or_qc, any_user, engineer_only, qc_lead_only
from app.core.security import Principal
from app.db.connection import Session, get_db
from app.schemas.requests import (
    CheckpointResultRequest,
    CreateAllocationRequest,
    ReassignAllocationRequest,
    ReviewAllocationRequest,
    SaveProgressRequest,
    SubmitAllocationRequest,
)
from app.services import allocations as alloc_svc
from app.services import checklist as checklist_svc

router = APIRouter(tags=["allocations"])


@router.get("/api/master-checklist")
def get_master_checklist(
    stage_id: str | None = None,
    building_type: str | None = None,
    priority: str | None = None,
    q: str | None = None,
    p: Principal = Depends(admin_or_qc),
    db: Session = Depends(get_db),
):
    if not stage_id and not building_type and not priority and not q:
        return Response(content=checklist_svc.json_tree(db), media_type="application/json")
    stages = checklist_svc.filtered(
        db, stage_id=stage_id, building_type=building_type, priority=priority, search_q=q
    )
    return Response(
        content=json.dumps({"status": "success", "stages": stages}),
        media_type="application/json",
    )


@router.get("/api/engineers")
def list_engineers(p: Principal = Depends(admin_or_qc), db: Session = Depends(get_db)):
    rows = db.all(
        "SELECT id, full_name AS name, employee_id, specialization AS specialty "
        "FROM users WHERE org_id = ? AND role = 'engineer' AND status = 'active' "
        "ORDER BY full_name",
        (p.org_id,),
    )
    return {
        "status": "success",
        "engineers": [
            {
                "id": r["employee_id"] or r["id"],
                "user_id": r["id"],
                "name": r["name"],
                "role": "QC Inspection Engineer",
                "specialty": r["specialty"] or "Civil & Finishes",
            }
            for r in rows
        ],
    }


@router.get("/api/allocations")
def list_allocations(
    project_id: str | None = None,
    engineer: str | None = None,
    status: str | None = None,
    p: Principal = Depends(admin_or_qc),
    db: Session = Depends(get_db),
):
    return {
        "status": "success",
        "allocations": alloc_svc.list_allocations(
            db, p, project_id=project_id, engineer=engineer, status=status
        ),
    }


@router.post("/api/allocations")
def create_allocation(
    req: CreateAllocationRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.create_allocation(db, p, req)


@router.get("/api/allocations/{id}")
def get_allocation_detail(id: str, p: Principal = Depends(any_user), db: Session = Depends(get_db)):
    return {"status": "success", "allocation": alloc_svc.detail(db, p, id)}


@router.post("/api/allocations/{id}/checkpoint-result")
def record_checkpoint_result(
    id: str,
    req: CheckpointResultRequest,
    p: Principal = Depends(engineer_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.record_result(
        db, p, id, req.checkpoint_id, req.result_status, req.observations, req.photo_url
    )


@router.post("/api/allocations/{id}/save-progress")
def save_allocation_progress(
    id: str,
    req: SaveProgressRequest,
    p: Principal = Depends(engineer_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.save_progress(db, p, id, req.checkpoints)


@router.post("/api/allocations/{id}/submit")
def submit_allocation(
    id: str,
    req: SubmitAllocationRequest,
    p: Principal = Depends(engineer_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.submit(db, p, id, req.notes)


@router.post("/api/allocations/{id}/review")
def review_allocation(
    id: str,
    req: ReviewAllocationRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.review(db, p, id, req.decision, req.comments)


@router.post("/api/allocations/{id}/reassign")
def reassign_allocation(
    id: str,
    req: ReassignAllocationRequest,
    p: Principal = Depends(qc_lead_only),
    db: Session = Depends(get_db),
):
    return alloc_svc.reassign(db, p, id, req.target, req.reason, req.new_due_date)
