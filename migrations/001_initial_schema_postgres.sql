-- ====================================================================
-- SiteIQ — Supabase / PostgreSQL Production Schema
-- Migration: 001_initial_schema_postgres.sql
-- Compatible with PostgreSQL 14+, Supabase Managed Postgres
-- ====================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------------------
-- 1. PROJECTS TABLE
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(64) NOT NULL,
    loc VARCHAR(255) NOT NULL,
    geo VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'live',  -- live, hold, upcoming, completed
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    cleared_date DATE,
    hold_reason TEXT,
    closed_extra INTEGER DEFAULT 0,
    upd_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    upd_by VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_code ON projects(code);

-- --------------------------------------------------------------------
-- 2. NON-CONFORMITIES (NC) TABLE
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS non_conformities (
    code VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    sev VARCHAR(16) NOT NULL,    -- critical, major, minor, ofi
    zone VARCHAR(64) NOT NULL,
    trade VARCHAR(64) NOT NULL,
    assigned VARCHAR(128) NOT NULL,
    raised_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL,  -- Open, Assigned, Rectification submitted, Under verification, Reopened, Closed
    raised_by VARCHAR(100) NOT NULL,
    closed_date DATE
);

CREATE INDEX IF NOT EXISTS idx_nc_project_id ON non_conformities(project_id);
CREATE INDEX IF NOT EXISTS idx_nc_status ON non_conformities(status);
CREATE INDEX IF NOT EXISTS idx_nc_sev ON non_conformities(sev);
CREATE INDEX IF NOT EXISTS idx_nc_due_date ON non_conformities(due_date);

-- --------------------------------------------------------------------
-- 3. NC AUDIT LOGS
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nc_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    nc_code VARCHAR(32) NOT NULL REFERENCES non_conformities(code) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    what VARCHAR(128) NOT NULL,
    message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nc_logs_code ON nc_audit_logs(nc_code);

-- --------------------------------------------------------------------
-- 4. INSPECTIONS TABLE
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inspections (
    code VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    zone VARCHAR(255) NOT NULL,
    tpl VARCHAR(255) NOT NULL,
    eng VARCHAR(100),
    due_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL, -- Required, Allocated, In progress, Pending review, Report issued
    items_count INTEGER DEFAULT 0,
    items_pass INTEGER DEFAULT 0,
    items_nc INTEGER DEFAULT 0,
    items_na INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_inspections_project ON inspections(project_id);
CREATE INDEX IF NOT EXISTS idx_inspections_status ON inspections(status);
CREATE INDEX IF NOT EXISTS idx_inspections_eng ON inspections(eng);

-- --------------------------------------------------------------------
-- 5. APPROVALS TABLE
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS approvals (
    code VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    by_user VARCHAR(100) NOT NULL,
    at_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ref_ins VARCHAR(32),
    ref_nc VARCHAR(32),
    status VARCHAR(20) DEFAULT 'Pending'
);

CREATE INDEX IF NOT EXISTS idx_approvals_project ON approvals(project_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

-- --------------------------------------------------------------------
-- 6. ACTION ITEMS TABLE
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS action_items (
    id BIGSERIAL PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    detail TEXT NOT NULL,
    due_date DATE NOT NULL,
    target_type VARCHAR(16) NOT NULL, -- nc, ins, project
    target_code VARCHAR(32) NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_actions_project ON action_items(project_id);
CREATE INDEX IF NOT EXISTS idx_actions_resolved ON action_items(is_resolved);

-- --------------------------------------------------------------------
-- 7. EVIDENCE PHOTOS TABLE
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence_photos (
    id BIGSERIAL PRIMARY KEY,
    nc_code VARCHAR(32) NOT NULL REFERENCES non_conformities(code) ON DELETE CASCADE,
    stage VARCHAR(10) NOT NULL, -- before, after
    photo_url VARCHAR(512),
    geo_stamp VARCHAR(64),
    time_stamp TIMESTAMPTZ,
    by_user VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_photos_nc ON evidence_photos(nc_code);

-- --------------------------------------------------------------------
-- 8. INSPECTION REPORTS TABLE (AI GENERATED)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inspection_reports (
    id BIGSERIAL PRIMARY KEY,
    ins_code VARCHAR(32) NOT NULL REFERENCES inspections(code) ON DELETE CASCADE,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    executive_summary TEXT,
    content_markdown TEXT NOT NULL,
    model_used VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_ins ON inspection_reports(ins_code);
CREATE INDEX IF NOT EXISTS idx_reports_project ON inspection_reports(project_id);

-- --------------------------------------------------------------------
-- 9. MASTER CHECKLIST: STAGES
-- --------------------------------------------------------------------
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

CREATE INDEX IF NOT EXISTS idx_stages_order ON master_stages(display_order);

-- --------------------------------------------------------------------
-- 10. MASTER CHECKLIST: SUBGROUPS
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_subgroups (
    subgroup_id VARCHAR(32) PRIMARY KEY,
    stage_id VARCHAR(16) NOT NULL REFERENCES master_stages(stage_id) ON DELETE CASCADE,
    subgroup_name VARCHAR(255) NOT NULL,
    display_order INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_subgroups_stage ON master_subgroups(stage_id);
CREATE INDEX IF NOT EXISTS idx_subgroups_order ON master_subgroups(display_order);

-- --------------------------------------------------------------------
-- 11. MASTER CHECKLIST: CHECKPOINTS
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_checkpoints (
    checkpoint_id VARCHAR(64) PRIMARY KEY,
    subgroup_id VARCHAR(32) NOT NULL REFERENCES master_subgroups(subgroup_id) ON DELETE CASCADE,
    stage_id VARCHAR(16) NOT NULL REFERENCES master_stages(stage_id) ON DELETE CASCADE,
    checkpoint_description TEXT NOT NULL,
    priority VARCHAR(8) NOT NULL, -- H (High), M (Medium), L (Low)
    applicable_building_types VARCHAR(128) NOT NULL, -- all, luxury, commercial, hotel, etc.
    source_version VARCHAR(16) DEFAULT 'v4.0',
    display_order INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_subgroup ON master_checkpoints(subgroup_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_stage ON master_checkpoints(stage_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_priority ON master_checkpoints(priority);

-- --------------------------------------------------------------------
-- 12. INSPECTION ALLOCATIONS
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inspection_allocations (
    allocation_id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    engineer_id VARCHAR(32),
    engineer_name VARCHAR(100) NOT NULL,
    allocated_by VARCHAR(100) NOT NULL,
    location_scope TEXT NOT NULL,
    tower_block VARCHAR(64),
    floor_level VARCHAR(64),
    zone_area VARCHAR(64),
    grid_ref VARCHAR(64),
    element_id VARCHAR(64),
    instructions TEXT,
    planned_date DATE NOT NULL,
    due_date DATE NOT NULL,
    due_time VARCHAR(16),
    priority VARCHAR(16) NOT NULL, -- High, Medium, Low
    status VARCHAR(32) NOT NULL DEFAULT 'Allocated', -- Required, Allocated, In progress, Pending review, Report issued
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    returned_at TIMESTAMPTZ,
    return_comments TEXT,
    linked_ins_code VARCHAR(32)
);

CREATE INDEX IF NOT EXISTS idx_allocations_project ON inspection_allocations(project_id);
CREATE INDEX IF NOT EXISTS idx_allocations_engineer ON inspection_allocations(engineer_id);
CREATE INDEX IF NOT EXISTS idx_allocations_status ON inspection_allocations(status);
CREATE INDEX IF NOT EXISTS idx_allocations_due ON inspection_allocations(due_date);

-- --------------------------------------------------------------------
-- 13. ALLOCATION CHECKPOINTS
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS allocation_checkpoints (
    id BIGSERIAL PRIMARY KEY,
    allocation_id VARCHAR(32) NOT NULL REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE,
    checkpoint_id VARCHAR(64) NOT NULL REFERENCES master_checkpoints(checkpoint_id),
    stage_id VARCHAR(16) NOT NULL,
    subgroup_id VARCHAR(32) NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    subgroup_name VARCHAR(255) NOT NULL,
    checkpoint_text_snapshot TEXT NOT NULL,
    priority VARCHAR(8) NOT NULL,
    checklist_version VARCHAR(16) DEFAULT 'v4.0',
    result_status VARCHAR(16) DEFAULT 'Pending', -- Pending, OK, NC, NA
    observations TEXT,
    evidence_photo_url VARCHAR(512),
    inspected_at TIMESTAMPTZ,
    inspected_by VARCHAR(100),
    linked_nc_code VARCHAR(32)
);

CREATE INDEX IF NOT EXISTS idx_alloc_checkpoints_alloc ON allocation_checkpoints(allocation_id);
CREATE INDEX IF NOT EXISTS idx_alloc_checkpoints_chk ON allocation_checkpoints(checkpoint_id);
CREATE INDEX IF NOT EXISTS idx_alloc_checkpoints_result ON allocation_checkpoints(result_status);

-- --------------------------------------------------------------------
-- 14. INSPECTION REVIEWS
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inspection_reviews (
    review_id BIGSERIAL PRIMARY KEY,
    allocation_id VARCHAR(32) NOT NULL REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE,
    reviewer_name VARCHAR(100) NOT NULL,
    decision VARCHAR(32) NOT NULL, -- Approved, Returned
    comments TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reviews_alloc ON inspection_reviews(allocation_id);

-- --------------------------------------------------------------------
-- 15. INSPECTION AUDIT EVENTS
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inspection_audit_events (
    event_id BIGSERIAL PRIMARY KEY,
    allocation_id VARCHAR(32) NOT NULL REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE,
    actor_name VARCHAR(100) NOT NULL,
    action VARCHAR(64) NOT NULL,
    previous_status VARCHAR(32),
    new_status VARCHAR(32),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_events_alloc ON inspection_audit_events(allocation_id);

-- --------------------------------------------------------------------
-- SUPABASE ROW LEVEL SECURITY (RLS) POLICIES
-- --------------------------------------------------------------------
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE non_conformities ENABLE ROW LEVEL SECURITY;
ALTER TABLE nc_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspection_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_stages ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_subgroups ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspection_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE allocation_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspection_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspection_audit_events ENABLE ROW LEVEL SECURITY;

-- Allow universal read and write access policies (compatible with Supabase, Railway, and standard Postgres)
DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'projects', 'non_conformities', 'nc_audit_logs', 'inspections', 'approvals',
        'action_items', 'evidence_photos', 'inspection_reports', 'master_stages',
        'master_subgroups', 'master_checkpoints', 'inspection_allocations',
        'allocation_checkpoints', 'inspection_reviews', 'inspection_audit_events'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format('DROP POLICY IF EXISTS "Allow all access" ON %I;', tbl);
        EXECUTE format('CREATE POLICY "Allow all access" ON %I FOR ALL USING (true) WITH CHECK (true);', tbl);
    END LOOP;
END $$;
