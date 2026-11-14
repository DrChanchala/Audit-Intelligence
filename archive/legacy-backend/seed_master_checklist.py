"""
Seeds Master Quality Inspection Checklist (20 stages, 98 subgroups, 859 checkpoints)
into the Audit Intelligence database.
"""

import json
import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "audit_intelligence.db")

def init_master_tables(conn):
    cur = conn.cursor()

    # 1. Master Inspection Stages
    cur.execute("""
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
    """)

    # 2. Master Inspection Subgroups
    cur.execute("""
    CREATE TABLE IF NOT EXISTS master_subgroups (
        subgroup_id VARCHAR(32) PRIMARY KEY,
        stage_id VARCHAR(16) NOT NULL,
        subgroup_name VARCHAR(255) NOT NULL,
        display_order INTEGER NOT NULL,
        FOREIGN KEY (stage_id) REFERENCES master_stages(stage_id) ON DELETE CASCADE
    );
    """)

    # 3. Master Inspection Checkpoints
    cur.execute("""
    CREATE TABLE IF NOT EXISTS master_checkpoints (
        checkpoint_id VARCHAR(64) PRIMARY KEY,
        subgroup_id VARCHAR(32) NOT NULL,
        stage_id VARCHAR(16) NOT NULL,
        checkpoint_description TEXT NOT NULL,
        priority VARCHAR(8) NOT NULL, -- H (High), M (Medium), L (Low)
        applicable_building_types VARCHAR(128) NOT NULL, -- all, luxury, commercial, hotel, etc.
        source_version VARCHAR(16) DEFAULT 'v4.0',
        display_order INTEGER NOT NULL,
        FOREIGN KEY (subgroup_id) REFERENCES master_subgroups(subgroup_id) ON DELETE CASCADE,
        FOREIGN KEY (stage_id) REFERENCES master_stages(stage_id) ON DELETE CASCADE
    );
    """)

    # 4. Inspection Allocations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inspection_allocations (
        allocation_id VARCHAR(32) PRIMARY KEY,
        project_id VARCHAR(32) NOT NULL,
        engineer_id VARCHAR(32),
        engineer_name VARCHAR(100) NOT NULL,
        allocated_by VARCHAR(100) NOT NULL,
        location_scope TEXT NOT NULL, -- JSON or string description (Tower, Floor, Grid, etc.)
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
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        submitted_at DATETIME,
        approved_at DATETIME,
        returned_at DATETIME,
        return_comments TEXT,
        linked_ins_code VARCHAR(32),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    """)

    # 5. Inspection Allocation Checkpoints (Selected checkpoints per allocation)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS allocation_checkpoints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        allocation_id VARCHAR(32) NOT NULL,
        checkpoint_id VARCHAR(64) NOT NULL,
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
        inspected_at DATETIME,
        inspected_by VARCHAR(100),
        linked_nc_code VARCHAR(32),
        FOREIGN KEY (allocation_id) REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE,
        FOREIGN KEY (checkpoint_id) REFERENCES master_checkpoints(checkpoint_id)
    );
    """)

    # 6. Inspection Reviews
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inspection_reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        allocation_id VARCHAR(32) NOT NULL,
        reviewer_name VARCHAR(100) NOT NULL,
        decision VARCHAR(32) NOT NULL, -- Approved, Returned
        comments TEXT,
        reviewed_at DATETIME NOT NULL,
        FOREIGN KEY (allocation_id) REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE
    );
    """)

    # 7. Inspection Audit Events
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inspection_audit_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        allocation_id VARCHAR(32) NOT NULL,
        actor_name VARCHAR(100) NOT NULL,
        action VARCHAR(64) NOT NULL,
        previous_status VARCHAR(32),
        new_status VARCHAR(32),
        timestamp DATETIME NOT NULL,
        remarks TEXT,
        FOREIGN KEY (allocation_id) REFERENCES inspection_allocations(allocation_id) ON DELETE CASCADE
    );
    """)

    conn.commit()

def populate_master_data():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    init_master_tables(conn)
    cur = conn.cursor()

    with open('master_checklist_parsed.json', 'r', encoding='utf-8') as f:
        stages_data = json.load(f)

    cur.execute("DELETE FROM master_checkpoints;")
    cur.execute("DELETE FROM master_subgroups;")
    cur.execute("DELETE FROM master_stages;")

    stage_order = 0
    subgroup_order = 0
    checkpoint_order = 0

    total_stages = 0
    total_subgroups = 0
    total_checkpoints = 0

    for s in stages_data:
        stage_order += 1
        raw_id = s.get('id', str(stage_order).zfill(2))
        stage_id = f"STG-{raw_id}"
        stage_name = s.get('name', f"Stage {raw_id}")
        badge = s.get('badge', '')
        bc = s.get('bc', '')
        btc = s.get('btc', '')

        cur.execute("""
            INSERT INTO master_stages (stage_id, stage_num, stage_name, badge, badge_bg, badge_color, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (stage_id, raw_id, stage_name, badge, bc, btc, stage_order))
        total_stages += 1

        sub_idx = 0
        for g in s.get('groups', []):
            sub_idx += 1
            subgroup_order += 1
            subgroup_id = f"SUB-{raw_id}-{str(sub_idx).zfill(2)}"
            subgroup_name = g.get('sub', f"Subgroup {sub_idx}")

            cur.execute("""
                INSERT INTO master_subgroups (subgroup_id, stage_id, subgroup_name, display_order)
                VALUES (?, ?, ?, ?)
            """, (subgroup_id, stage_id, subgroup_name, subgroup_order))
            total_subgroups += 1

            item_idx = 0
            for item in g.get('items', []):
                item_idx += 1
                checkpoint_order += 1
                chk_id = f"CHK-{raw_id}-{str(sub_idx).zfill(2)}-{str(item_idx).zfill(3)}"
                desc = item[0]
                pri = item[1] if len(item) > 1 else 'M'
                btype = item[2] if len(item) > 2 else 'all'

                cur.execute("""
                    INSERT INTO master_checkpoints (checkpoint_id, subgroup_id, stage_id, checkpoint_description, priority, applicable_building_types, display_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (chk_id, subgroup_id, stage_id, desc, pri, btype, checkpoint_order))
                total_checkpoints += 1

    conn.commit()
    conn.close()

    print(f"Master Checklist Seeded Successfully:")
    print(f"  • {total_stages} Stages")
    print(f"  • {total_subgroups} Subgroups")
    print(f"  • {total_checkpoints} Checkpoints")

if __name__ == '__main__':
    populate_master_data()
