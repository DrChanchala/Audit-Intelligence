import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "buildtrack.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # ── Projects ──────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        location TEXT,
        planned_start DATE,
        planned_finish DATE,
        contract_value REAL,
        status TEXT DEFAULT 'In Progress'
    )
    ''')

    # ── Buildings / Towers ────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS towers (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        total_floors INTEGER,
        weightage REAL DEFAULT 50.0,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # ── WBS Stages ───────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stages (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        stage_number INTEGER NOT NULL,
        name TEXT NOT NULL,
        weightage REAL NOT NULL,
        code TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # ── Sub-stages ───────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS substages (
        id TEXT PRIMARY KEY,
        stage_id TEXT,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        weightage REAL DEFAULT 0.0,
        FOREIGN KEY (stage_id) REFERENCES stages(id)
    )
    ''')

    # ── L4 Activities (Core WBS — enhanced for dual-mode) ─────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activities (
        id TEXT PRIMARY KEY,
        activity_code TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        project_id TEXT,
        tower_id TEXT,
        floor_level INTEGER,
        zone TEXT,
        unit TEXT,
        room TEXT,
        discipline TEXT,
        trade TEXT,
        boq_item TEXT,
        boq_description TEXT,
        stage_id TEXT,
        substage_id TEXT,
        responsible_role TEXT,
        responsible_engineer TEXT,
        contractor TEXT,
        planned_qty REAL NOT NULL,
        reported_qty REAL DEFAULT 0.0,
        inspected_qty REAL DEFAULT 0.0,
        accepted_qty REAL DEFAULT 0.0,
        uom TEXT NOT NULL,
        unit_cost REAL DEFAULT 0.0,
        weightage REAL NOT NULL,
        planned_start DATE,
        planned_finish DATE,
        planned_duration INTEGER,
        predecessor TEXT,
        dependency_type TEXT DEFAULT 'FS',
        actual_start DATE,
        actual_finish DATE,
        status TEXT DEFAULT 'Not Started',
        inspection_status TEXT DEFAULT 'Not Requested',
        rfi_status TEXT DEFAULT 'None',
        ncr_status TEXT DEFAULT 'None',
        camera_ref TEXT,
        remarks TEXT,
        -- ── FOUR PROGRESS STREAMS ─────────────────────────────────────────
        planned_progress_pct REAL DEFAULT 0.0,
        ai_automated_progress_pct REAL DEFAULT 0.0,
        ai_automated_confidence REAL DEFAULT 0.0,
        ai_last_observed_at TIMESTAMP,
        field_observed_progress_pct REAL DEFAULT 0.0,
        pm_approved_progress_pct REAL DEFAULT 0.0,
        pm_approved_at TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (tower_id) REFERENCES towers(id),
        FOREIGN KEY (stage_id) REFERENCES stages(id),
        FOREIGN KEY (substage_id) REFERENCES substages(id)
    )
    ''')

    # ── Schedule Baselines (L4 Upload Versions) ───────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS schedule_baselines (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        version INTEGER NOT NULL DEFAULT 1,
        filename TEXT NOT NULL,
        uploaded_by TEXT,
        status TEXT DEFAULT 'DRAFT',
        total_activities INTEGER DEFAULT 0,
        total_weight REAL DEFAULT 0.0,
        validation_errors INTEGER DEFAULT 0,
        validation_warnings INTEGER DEFAULT 0,
        validation_report TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        confirmed_at TIMESTAMP,
        confirmed_by TEXT,
        notes TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # ── Camera Coverage Mapping ───────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS camera_coverage (
        id TEXT PRIMARY KEY,
        camera_id TEXT NOT NULL,
        activity_id TEXT,
        stage_id TEXT,
        tower_id TEXT,
        floor_from INTEGER,
        floor_to INTEGER,
        visible_elements TEXT,
        coverage_quality TEXT DEFAULT 'GOOD',
        notes TEXT,
        FOREIGN KEY (camera_id) REFERENCES cameras(id)
    )
    ''')

    # ── Field Visits (Mode B) ─────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS field_visits (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        operator_name TEXT NOT NULL,
        operator_role TEXT DEFAULT 'Field Operator',
        visit_date DATE,
        purpose TEXT,
        status TEXT DEFAULT 'IN_PROGRESS',
        photos_count INTEGER DEFAULT 0,
        submitted_at TIMESTAMP,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )
    ''')

    # ── Field Photos (Mode B) ─────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS field_photos (
        id TEXT PRIMARY KEY,
        visit_id TEXT,
        activity_id TEXT,
        tower_id TEXT,
        floor_level INTEGER,
        zone TEXT,
        unit TEXT,
        file_path TEXT NOT NULL,
        file_name TEXT,
        captured_by TEXT,
        operator_quantity REAL,
        operator_uom TEXT,
        operator_remarks TEXT,
        validation_status TEXT DEFAULT 'PENDING',
        ai_progress_percent REAL,
        ai_confidence REAL,
        pm_review_status TEXT DEFAULT 'PENDING_PM_REVIEW',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (visit_id) REFERENCES field_visits(id),
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── Image Validations (AI output for every photo) ─────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS image_validations (
        id TEXT PRIMARY KEY,
        photo_id TEXT NOT NULL,
        source_type TEXT NOT NULL,
        image_valid INTEGER DEFAULT 0,
        construction_site_detected INTEGER DEFAULT 0,
        wrong_object_detected INTEGER DEFAULT 0,
        image_quality TEXT DEFAULT 'UNKNOWN',
        context_relevant INTEGER DEFAULT 0,
        activity_visible INTEGER DEFAULT 0,
        duplicate_detected INTEGER DEFAULT 0,
        validation_confidence REAL DEFAULT 0.0,
        validation_status TEXT DEFAULT 'PENDING',
        recommended_action TEXT,
        rejection_reason TEXT,
        raw_output TEXT,
        validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (photo_id) REFERENCES field_photos(id)
    )
    ''')

    # ── AI Observations (full assessment — both modes) ────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ai_observations (
        id TEXT PRIMARY KEY,
        source_type TEXT NOT NULL,
        camera_id TEXT,
        photo_id TEXT,
        activity_id TEXT,
        location TEXT,
        scheduled_status TEXT,
        ai_observed_status TEXT,
        ai_progress_percent REAL DEFAULT 0.0,
        confidence REAL DEFAULT 0.0,
        evidence_quality TEXT DEFAULT 'UNKNOWN',
        quantity_measurable INTEGER DEFAULT 0,
        schedule_variance TEXT DEFAULT 'UNKNOWN',
        requires_human_intervention INTEGER DEFAULT 0,
        requires_field_verification INTEGER DEFAULT 0,
        not_determinable INTEGER DEFAULT 0,
        safety_flags TEXT,
        ai_model TEXT DEFAULT 'PyCray_SiteIQ_V1',
        ai_model_version TEXT DEFAULT '1.0.0',
        prompt_version TEXT DEFAULT '1.0',
        input_context TEXT,
        output_json TEXT,
        human_override INTEGER DEFAULT 0,
        override_reason TEXT,
        override_by TEXT,
        observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── PM Review Queue (Mode B approval workflow) ────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pm_reviews (
        id TEXT PRIMARY KEY,
        photo_id TEXT NOT NULL,
        activity_id TEXT,
        visit_id TEXT,
        field_operator TEXT,
        ai_progress_percent REAL,
        ai_confidence REAL,
        operator_quantity REAL,
        operator_uom TEXT,
        pm_status TEXT DEFAULT 'PENDING',
        pm_approved_quantity REAL,
        pm_approved_progress_percent REAL,
        pm_reviewer TEXT,
        pm_remarks TEXT,
        pm_action TEXT,
        reviewed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (photo_id) REFERENCES field_photos(id),
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── Progress History / Quantity Submissions ───────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS progress_updates (
        id TEXT PRIMARY KEY,
        activity_id TEXT,
        submitted_by TEXT,
        role TEXT,
        reported_qty REAL,
        evidence_photo TEXT,
        remarks TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        inspection_id TEXT,
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── QA/QC Inspections ────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS inspections (
        id TEXT PRIMARY KEY,
        activity_id TEXT,
        requested_by TEXT,
        inspector TEXT,
        inspected_qty REAL,
        accepted_qty REAL,
        status TEXT DEFAULT 'Pending',
        comments TEXT,
        test_results TEXT,
        evidence_photo TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        inspected_at TIMESTAMP,
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── Daily Progress Snapshots (4-stream) ───────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS progress_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id TEXT,
        snapshot_date DATE,
        planned_pct REAL DEFAULT 0.0,
        ai_automated_pct REAL DEFAULT 0.0,
        field_observed_pct REAL DEFAULT 0.0,
        pm_approved_pct REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── RFIs ─────────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS rfis (
        id TEXT PRIMARY KEY,
        rfi_number TEXT NOT NULL,
        subject TEXT NOT NULL,
        description TEXT,
        activity_id TEXT,
        drawing_ref TEXT,
        raised_by TEXT,
        assigned_to TEXT,
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Open',
        response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP,
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── NCRs ─────────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ncrs (
        id TEXT PRIMARY KEY,
        ncr_number TEXT NOT NULL,
        activity_id TEXT,
        location TEXT,
        description TEXT,
        severity TEXT DEFAULT 'Moderate',
        contractor TEXT,
        corrective_action TEXT,
        due_date DATE,
        status TEXT DEFAULT 'Open',
        evidence_photo TEXT,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP,
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── Safety Records ────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS safety_records (
        id TEXT PRIMARY KEY,
        record_type TEXT DEFAULT 'Observation',
        tower_id TEXT,
        floor_level INTEGER,
        zone TEXT,
        description TEXT,
        severity TEXT DEFAULT 'Low',
        is_ai_flagged INTEGER DEFAULT 0,
        ai_confidence REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Open',
        corrective_action TEXT,
        assigned_to TEXT,
        created_by TEXT,
        photo_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ── Materials ─────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS materials (
        id TEXT PRIMARY KEY,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT,
        uom TEXT NOT NULL,
        current_stock REAL DEFAULT 0.0,
        reorder_level REAL DEFAULT 0.0,
        unit_price REAL DEFAULT 0.0,
        supplier TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS material_requisitions (
        id TEXT PRIMARY KEY,
        material_id TEXT,
        activity_id TEXT,
        required_qty REAL,
        status TEXT DEFAULT 'Requested',
        due_date DATE,
        requested_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (material_id) REFERENCES materials(id),
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── Fixed Site Cameras ────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cameras (
        id TEXT PRIMARY KEY,
        camera_code TEXT NOT NULL,
        location TEXT NOT NULL,
        tower_id TEXT,
        floor_level INTEGER,
        zone TEXT,
        viewing_direction TEXT,
        gps_coordinates TEXT,
        coverage_floors TEXT,
        status TEXT DEFAULT 'Active',
        last_image_url TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ── AI Camera Observations (legacy / delta tracking) ──────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ai_camera_observations (
        id TEXT PRIMARY KEY,
        camera_id TEXT,
        activity_id TEXT,
        previous_image_url TEXT,
        current_image_url TEXT,
        detected_element TEXT,
        ai_estimated_progress REAL,
        previous_estimated_progress REAL,
        delta_change REAL,
        safety_flags TEXT,
        confidence REAL,
        human_verification_status TEXT DEFAULT 'Pending Review',
        reviewed_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (camera_id) REFERENCES cameras(id),
        FOREIGN KEY (activity_id) REFERENCES activities(id)
    )
    ''')

    # ── Audit Trail ───────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        action TEXT NOT NULL,
        user_role TEXT NOT NULL,
        user_name TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # ── Weightage Revision History ────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weightage_revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modified_by TEXT NOT NULL,
        reason TEXT,
        weightage_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

def reset_db():
    """Drop and recreate the database for fresh seeding."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    print("Database reset and reinitialized.")

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
