"""Single source of truth for the schema (SQLite for local/dev, PostgreSQL in prod).

Previously the schema was split across database_audit.py, two seed scripts and
two SQL migrations, each slightly different. ``init_schema`` is idempotent
(CREATE ... IF NOT EXISTS) and matches migrations/001 + 002 + 003.

Tenancy model: ``organizations`` -> ``users`` and ``projects`` carry org_id;
every other tenant table hangs off ``projects.project_id``, so tenant checks
always resolve through the owning project. The master checklist is global,
read-only reference data.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.db.connection import Session

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "master_checklist_parsed.json"

_TYPES = {
    "sqlite": {"PK_AUTO": "INTEGER PRIMARY KEY AUTOINCREMENT", "TS": "TEXT", "DATE": "TEXT", "BOOL": "INTEGER"},
    "postgres": {"PK_AUTO": "BIGSERIAL PRIMARY KEY", "TS": "TIMESTAMPTZ", "DATE": "DATE", "BOOL": "BOOLEAN"},
}

DDL = """
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(32) NOT NULL UNIQUE,
    domain VARCHAR(128),
    industry VARCHAR(128) DEFAULT 'Construction & Real Estate',
    address TEXT,
    status VARCHAR(32) DEFAULT 'active',
    created_at {TS} DEFAULT CURRENT_TIMESTAMP,
    updated_at {TS} DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL,
    employee_id VARCHAR(64),
    specialization VARCHAR(128),
    avatar_initials VARCHAR(8),
    phone VARCHAR(32),
    status VARCHAR(32) DEFAULT 'active',
    last_login_at {TS},
    created_at {TS} DEFAULT CURRENT_TIMESTAMP,
    updated_at {TS} DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_org_role ON users(org_id, role);
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(64) NOT NULL,
    loc VARCHAR(255) NOT NULL,
    geo VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'live',
    progress INTEGER DEFAULT 0,
    start_date {DATE} NOT NULL,
    end_date {DATE} NOT NULL,
    cleared_date {DATE},
    hold_reason TEXT,
    closed_extra INTEGER DEFAULT 0,
    upd_at {TS} NOT NULL DEFAULT CURRENT_TIMESTAMP,
    upd_by VARCHAR(100) NOT NULL,
    org_id VARCHAR(64) REFERENCES organizations(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_org ON projects(org_id);
CREATE TABLE IF NOT EXISTS non_conformities (
    code VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    sev VARCHAR(16) NOT NULL,
    zone VARCHAR(64) NOT NULL,
    trade VARCHAR(64) NOT NULL,
    assigned VARCHAR(128) NOT NULL,
    raised_date {DATE} NOT NULL,
    due_date {DATE} NOT NULL,
    status VARCHAR(32) NOT NULL,
    raised_by VARCHAR(100) NOT NULL,
    closed_date {DATE}
);
CREATE INDEX IF NOT EXISTS idx_nc_project_id ON non_conformities(project_id);
CREATE TABLE IF NOT EXISTS nc_audit_logs (
    id {PK_AUTO},
    nc_code VARCHAR(32) NOT NULL REFERENCES non_conformities(code) ON DELETE CASCADE,
    event_date {DATE} NOT NULL,
    what VARCHAR(128) NOT NULL,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nc_logs_code ON nc_audit_logs(nc_code);
CREATE TABLE IF NOT EXISTS inspections (
    code VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    zone VARCHAR(255) NOT NULL,
    tpl VARCHAR(255) NOT NULL,
    eng VARCHAR(100),
    due_date {DATE} NOT NULL,
    status VARCHAR(32) NOT NULL,
    items_count INTEGER DEFAULT 0,
    items_pass INTEGER DEFAULT 0,
    items_nc INTEGER DEFAULT 0,
    items_na INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_inspections_project ON inspections(project_id);
CREATE TABLE IF NOT EXISTS approvals (
    code VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    by_user VARCHAR(100) NOT NULL,
    at_time {TS} NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ref_ins VARCHAR(32),
    ref_nc VARCHAR(32),
    status VARCHAR(20) DEFAULT 'Pending'
);
CREATE INDEX IF NOT EXISTS idx_approvals_project ON approvals(project_id);
CREATE TABLE IF NOT EXISTS action_items (
    id {PK_AUTO},
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    detail TEXT NOT NULL,
    due_date {DATE} NOT NULL,
    target_type VARCHAR(16) NOT NULL,
    target_code VARCHAR(32) NOT NULL,
    is_resolved {BOOL} DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_actions_project ON action_items(project_id);
CREATE TABLE IF NOT EXISTS evidence_photos (
    id {PK_AUTO},
    nc_code VARCHAR(32) NOT NULL REFERENCES non_conformities(code) ON DELETE CASCADE,
    stage VARCHAR(10) NOT NULL,
    photo_url VARCHAR(512),
    geo_stamp VARCHAR(64),
    time_stamp {TS},
    by_user VARCHAR(100)
);
CREATE TABLE IF NOT EXISTS inspection_reports (
    id {PK_AUTO},
    ins_code VARCHAR(32) NOT NULL REFERENCES inspections(code) ON DELETE CASCADE,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    executive_summary TEXT,
    content_markdown TEXT NOT NULL,
    model_used VARCHAR(64) NOT NULL,
    created_at {TS} NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_ins ON inspection_reports(ins_code);
CREATE TABLE IF NOT EXISTS master_stages (
    stage_id VARCHAR(16) PRIMARY KEY,
    stage_num VARCHAR(8) NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    badge VARCHAR(64),
    badge_bg VARCHAR(16),
    badge_color VARCHAR(16),
    display_order INTEGER NOT NULL,
    checklist_version VARCHAR(16) DEFAULT 'v4.0'
);
CREATE TABLE IF NOT EXISTS master_subgroups (
    subgroup_id VARCHAR(32) PRIMARY KEY,
    stage_id VARCHAR(16) NOT NULL REFERENCES master_stages(stage_id) ON DELETE CASCADE,
    subgroup_name VARCHAR(255) NOT NULL,
    display_order INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_subgroups_stage ON master_subgroups(stage_id);
CREATE TABLE IF NOT EXISTS master_checkpoints (
    checkpoint_id VARCHAR(64) PRIMARY KEY,
    subgroup_id VARCHAR(32) NOT NULL REFERENCES master_subgroups(subgroup_id) ON DELETE CASCADE,
    stage_id VARCHAR(16) NOT NULL REFERENCES master_stages(stage_id) ON DELETE CASCADE,
    checkpoint_description TEXT NOT NULL,
    priority VARCHAR(8) NOT NULL,
    applicable_building_types VARCHAR(128) NOT NULL,
    source_version VARCHAR(16) DEFAULT 'v4.0',
    display_order INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checkpoints_subgroup ON master_checkpoints(subgroup_id);
CREATE TABLE IF NOT EXISTS inspection_allocations (
    allocation_id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    engineer_id VARCHAR(64),
    engineer_name VARCHAR(100) NOT NULL,
    allocated_by VARCHAR(100) NOT NULL,
    location_scope TEXT NOT NULL,
    tower_block VARCHAR(64),
    floor_level VARCHAR(64),
    zone_area VARCHAR(64),
    grid_ref VARCHAR(64),
    element_id VARCHAR(64),
    instructions TEXT,
    planned_date {DATE} NOT NULL,
    due_date {DATE} NOT NULL,
    due_time VARCHAR(16),
    priority VARCHAR(16) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'Allocated',
    created_at {TS} NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at {TS} NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at {TS},
    approved_at {TS},
    returned_at {TS},
    return_comments TEXT,
    linked_ins_code VARCHAR(32)
);
CREATE INDEX IF NOT EXISTS idx_allocations_project ON inspection_allocations(project_id);
CREATE INDEX IF NOT EXISTS idx_allocations_engineer ON inspection_allocations(engineer_id);
CREATE TABLE IF NOT EXISTS allocation_checkpoints (
    id {PK_AUTO},
    allocation_id VARCHAR(32) NOT NULL REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE,
    checkpoint_id VARCHAR(64) NOT NULL REFERENCES master_checkpoints(checkpoint_id),
    stage_id VARCHAR(16) NOT NULL,
    subgroup_id VARCHAR(32) NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    subgroup_name VARCHAR(255) NOT NULL,
    checkpoint_text_snapshot TEXT NOT NULL,
    priority VARCHAR(8) NOT NULL,
    checklist_version VARCHAR(16) DEFAULT 'v4.0',
    result_status VARCHAR(16) DEFAULT 'Pending',
    observations TEXT,
    evidence_photo_url VARCHAR(512),
    inspected_at {TS},
    inspected_by VARCHAR(100),
    linked_nc_code VARCHAR(32)
);
CREATE INDEX IF NOT EXISTS idx_alloc_checkpoints_alloc ON allocation_checkpoints(allocation_id);
CREATE TABLE IF NOT EXISTS inspection_reviews (
    review_id {PK_AUTO},
    allocation_id VARCHAR(32) NOT NULL REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE,
    reviewer_name VARCHAR(100) NOT NULL,
    decision VARCHAR(32) NOT NULL,
    comments TEXT,
    reviewed_at {TS} NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS inspection_audit_events (
    event_id {PK_AUTO},
    allocation_id VARCHAR(32) NOT NULL REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE,
    actor_name VARCHAR(100) NOT NULL,
    action VARCHAR(64) NOT NULL,
    previous_status VARCHAR(32),
    new_status VARCHAR(32),
    timestamp {TS} NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_events_alloc ON inspection_audit_events(allocation_id);
"""


def init_schema(db: Session) -> None:
    ddl = DDL
    for key, value in _TYPES[db.dialect].items():
        ddl = ddl.replace("{" + key + "}", value)
    for stmt in (s.strip() for s in ddl.split(";")):
        if stmt:
            db.execute(stmt)


def load_master_checklist(db: Session, force: bool = False) -> int:
    """Load the global master checklist from the bundled JSON if the table is empty.

    IDs (STG-xx, SUB-xx-yy, CHK-xx-yy-zzz) match the previous seeder so
    existing allocation_checkpoints rows stay valid.
    """
    if not force and db.scalar("SELECT COUNT(*) FROM master_checkpoints"):
        return 0
    stages = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    db.execute("DELETE FROM master_checkpoints")
    db.execute("DELETE FROM master_subgroups")
    db.execute("DELETE FROM master_stages")
    stage_rows, sub_rows, chk_rows = [], [], []
    sub_order = chk_order = 0
    for s_idx, s in enumerate(stages, start=1):
        raw = s.get("id", str(s_idx).zfill(2))
        stage_id = f"STG-{raw}"
        stage_rows.append((stage_id, raw, s.get("name", f"Stage {raw}"), s.get("badge", ""),
                           s.get("bc", ""), s.get("btc", ""), s_idx))
        for g_idx, g in enumerate(s.get("groups", []), start=1):
            sub_order += 1
            sub_id = f"SUB-{raw}-{g_idx:02d}"
            sub_rows.append((sub_id, stage_id, g.get("sub", f"Subgroup {g_idx}"), sub_order))
            for i_idx, item in enumerate(g.get("items", []), start=1):
                chk_order += 1
                chk_rows.append((f"CHK-{raw}-{g_idx:02d}-{i_idx:03d}", sub_id, stage_id, item[0],
                                 item[1] if len(item) > 1 else "M", item[2] if len(item) > 2 else "all",
                                 chk_order))
    db.executemany("INSERT INTO master_stages (stage_id, stage_num, stage_name, badge, badge_bg, badge_color, "
                   "display_order) VALUES (?, ?, ?, ?, ?, ?, ?)", stage_rows)
    db.executemany("INSERT INTO master_subgroups (subgroup_id, stage_id, subgroup_name, display_order) "
                   "VALUES (?, ?, ?, ?)", sub_rows)
    db.executemany("INSERT INTO master_checkpoints (checkpoint_id, subgroup_id, stage_id, checkpoint_description, "
                   "priority, applicable_building_types, display_order) VALUES (?, ?, ?, ?, ?, ?, ?)", chk_rows)
    return len(chk_rows)
