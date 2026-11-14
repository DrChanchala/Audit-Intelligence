"""Organization admin console APIs and projects."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.core.deps import admin_only, admin_or_qc, any_user
from app.core.security import Principal
from app.db.connection import Session, get_db
from app.schemas.requests import ProjectCreate
from app.services import auth as auth_svc
from app.services import projects as svc

router = APIRouter(tags=["admin", "projects"])


@router.get("/api/admin/overview")
def admin_overview(p: Principal = Depends(admin_only), db: Session = Depends(get_db)):
    return {"status": "success", "kpis": auth_svc.org_kpis(db, p)}


@router.get("/api/projects")
def list_projects(status: Optional[str] = None, q: Optional[str] = None, p: Principal = Depends(any_user),
                  db: Session = Depends(get_db)):
    return svc.list_projects(db, p, status, q)


@router.post("/api/projects")
def create_project(req: ProjectCreate, p: Principal = Depends(admin_only), db: Session = Depends(get_db)):
    project = svc.create_project(db, p, req)
    return {"status": "success", "message": f"Project '{project['name']}' created.", "project": project}


@router.get("/api/projects/{project_id}")
def project_detail(project_id: str, p: Principal = Depends(admin_or_qc), db: Session = Depends(get_db)):
    return svc.project_detail(db, p, project_id)
