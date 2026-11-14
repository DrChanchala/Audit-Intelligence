"""Request bodies. Field names match the previous API so existing clients keep working.

Fields that used to let callers pick their identity or tenant (``user``,
``actor_name``, ``reviewer_name``, ``allocated_by``, ``org_id`` ...) are still
accepted for backwards compatibility but are ignored: identity and tenant
come from the session.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MIN_PASSWORD_LENGTH

Str100 = Field(default=None, max_length=100)


class _Body(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


# ---------- auth ----------

class LoginRequest(_Body):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    org_id: str | None = None  # optional legacy org picker; validated if present


class RegisterOrgAdminRequest(_Body):
    org_name: str = Field(min_length=2, max_length=200)
    org_code: str | None = Field(default=None, max_length=24)
    industry: str | None = Field(default="Construction & Real Estate", max_length=128)
    address: str | None = Field(default=None, max_length=500)
    admin_name: str = Field(min_length=2, max_length=128)
    admin_email: EmailStr
    admin_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)
    admin_phone: str | None = Field(default=None, max_length=32)


class CreateUserRequest(_Body):
    org_id: str | None = None  # ignored: users are always created in the caller's org
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)
    full_name: str = Field(min_length=2, max_length=128)
    role: Literal["admin", "qc_lead", "engineer"]
    employee_id: str | None = Field(default=None, max_length=64)
    specialization: str | None = Field(default=None, max_length=128)
    phone: str | None = Field(default=None, max_length=32)


# ---------- projects ----------

class ProjectCreate(_Body):
    name: str = Field(min_length=2, max_length=255)
    type: str = Field(default="Commercial & Residential", max_length=64)
    loc: str = Field(min_length=2, max_length=255)
    geo: str | None = Field(default=None, max_length=64)
    status: Literal["live", "hold", "upcoming", "completed"] = "live"
    progress: int = Field(default=0, ge=0, le=100)
    start_date: date
    end_date: date
    hold_reason: str | None = Field(default=None, max_length=500)

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v


# ---------- NCs / approvals / legacy inspections ----------

class NCActionRequest(_Body):
    action: Literal["verify", "close", "reopen", "remind"]
    note: str | None = Field(default=None, max_length=1000)


class ApprovalActionRequest(_Body):
    action: Literal["approve", "return"]
    note: str | None = Field(default=None, max_length=1000)


class AllocateEngineerRequest(_Body):
    engineer_id: str | None = Field(default=None, max_length=64)
    engineer_name: str | None = Field(default=None, max_length=100)


# ---------- allocations ----------

class CreateAllocationRequest(_Body):
    project_id: str = Field(max_length=32)
    inspection_id: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, max_length=255)
    engineer_id: str | None = Field(default=None, max_length=64)
    engineer_name: str | None = Field(default=None, max_length=100)
    tower_block: str = Field(default="", max_length=64)
    floor_level: str = Field(default="", max_length=64)
    zone_area: str = Field(default="", max_length=64)
    grid_ref: str = Field(default="", max_length=64)
    element_id: str = Field(default="", max_length=64)
    instructions: str = Field(default="", max_length=2000)
    planned_date: date | None = None
    due_date: date | None = None
    due_time: str = Field(default="18:00", max_length=16)
    priority: Literal["High", "Medium", "Low"] = "High"
    checkpoint_ids: list[str] = Field(default_factory=list, max_length=1000)
    allow_duplicate: bool = False
    status: Literal["Allocated", "Draft", "draft"] = "Allocated"


ResultStatus = Literal["Pending", "OK", "NC", "NA"]


class CheckpointResultRequest(_Body):
    checkpoint_id: str = Field(max_length=64)
    result_status: ResultStatus
    observations: str | None = Field(default=None, max_length=4000)
    photo_url: str | None = Field(default=None, max_length=512)


class CheckpointProgressItem(_Body):
    checkpoint_id: str = Field(max_length=64)
    result_status: ResultStatus = "Pending"
    observations: str | None = Field(default=None, max_length=4000)
    evidence_photo_url: str | None = Field(default=None, max_length=512)


class SaveProgressRequest(_Body):
    checkpoints: list[CheckpointProgressItem] = Field(max_length=1000)


class SubmitAllocationRequest(_Body):
    notes: str | None = Field(default=None, max_length=2000)


class ReviewAllocationRequest(_Body):
    decision: Literal["approve", "return"]
    comments: str | None = Field(default=None, max_length=4000)


class ReassignAllocationRequest(_Body):
    engineer_id: str | None = Field(default=None, max_length=64)
    new_engineer: str | None = Field(default=None, max_length=100)
    new_engineer_id: str | None = Field(default=None, max_length=64)
    new_engineer_name: str | None = Field(default=None, max_length=100)
    reason: str = Field(default="", max_length=1000)
    new_due_date: date | None = None

    @property
    def target(self) -> str:
        return self.new_engineer_id or self.engineer_id or self.new_engineer or self.new_engineer_name or ""


class ChangeStatusRequest(_Body):
    status: str = Field(max_length=40)
    reason: str | None = Field(default=None, max_length=1000)


class UploadEvidencePayload(_Body):
    checkpoint_id: str | None = Field(default=None, max_length=64)
    data_url: str | None = None
    filename: str | None = Field(default=None, max_length=200)
