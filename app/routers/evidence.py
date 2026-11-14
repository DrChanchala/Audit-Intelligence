"""Photo evidence upload and retrieval."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse

from app.core.deps import any_user, engineer_only
from app.core.errors import ValidationFailed
from app.core.security import Principal
from app.db.connection import Session, get_db
from app.services import evidence as svc
from app.services.allocations import EDITABLE
from app.services.tenancy import allocation_in_scope

router = APIRouter(tags=["evidence"])


@router.post("/api/allocations/{id}/upload-evidence")
async def upload_evidence(
    id: str,
    request: Request,
    p: Principal = Depends(engineer_only),
    db: Session = Depends(get_db),
):
    alloc = allocation_in_scope(db, p, id)
    if alloc["status"] not in EDITABLE:
        raise ValidationFailed(f"Evidence cannot be uploaded while inspection is '{alloc['status']}'.")

    content_type = request.headers.get("content-type", "")
    checkpoint_id = None
    data = b""

    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file")
        if not file_obj or not hasattr(file_obj, "read"):
            raise ValidationFailed("No file uploaded in form field 'file'.")
        data = await file_obj.read()
        checkpoint_id = form.get("checkpoint_id")
    else:
        try:
            body = await request.json()
        except Exception as exc:
            raise ValidationFailed("Invalid JSON body.") from exc
        data_url = body.get("data_url")
        if not data_url:
            raise ValidationFailed("Missing 'data_url' in request body.")
        data = svc.decode_data_url(data_url)
        checkpoint_id = body.get("checkpoint_id")

    url = svc.store(id, data)
    return {
        "status": "success",
        "url": url,
        "checkpoint_id": checkpoint_id,
        "allocation_id": id,
    }


@router.get("/api/evidence/{alloc}/{name}")
def get_evidence(
    alloc: str,
    name: str,
    p: Principal = Depends(any_user),
    db: Session = Depends(get_db),
):
    allocation_in_scope(db, p, alloc)
    kind, target = svc.resolve(alloc, name)
    if kind == "redirect":
        return RedirectResponse(target, status_code=302)
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "jpg"
    return FileResponse(target, media_type=svc.CONTENT_TYPES.get(ext, "image/jpeg"))
