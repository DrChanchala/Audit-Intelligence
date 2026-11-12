"""
Audit Intelligence - Database Models & Seed Data
Engineered for hybrid execution: Supabase PostgreSQL in production, SQLite locally.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

DB_FILE = os.path.join(os.path.dirname(__file__), "audit_intelligence.db")

class HybridRow:
    """Provides dual access by column name (dict-like) and integer index (tuple-like), mirroring sqlite3.Row."""
    def __init__(self, d):
        self._d = d
        self._l = list(d.values())

    def __getitem__(self, key):
        return self._l[key] if isinstance(key, int) else self._d[key]

    def get(self, key, default=None):
        return self._d.get(key, default)

    def keys(self):
        return self._d.keys()

    def values(self):
        return self._d.values()

    def items(self):
        return self._d.items()

    def __iter__(self):
        return iter(self._d)

    def __repr__(self):
        return repr(self._d)

    def __len__(self):
        return len(self._l)

class PostgresCursorWrapper:
    """Wraps psycopg2 cursor to provide seamless compatibility with sqlite3 cursor semantics."""
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, params=None):
        if params is not None:
            # Normalize ? placeholders to %s for PostgreSQL
            sql = sql.replace('?', '%s')
            return self._cur.execute(sql, params)
        return self._cur.execute(sql)

    def executemany(self, sql, seq_of_params):
        sql = sql.replace('?', '%s')
        return self._cur.executemany(sql, seq_of_params)

    def fetchone(self):
        row = self._cur.fetchone()
        return HybridRow(row) if row is not None else None

    def fetchall(self):
        rows = self._cur.fetchall()
        return [HybridRow(r) for r in rows] if rows else []

    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()
        return [HybridRow(r) for r in rows] if rows else []

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def lastrowid(self):
        return getattr(self._cur, 'lastrowid', None)

    def close(self):
        return self._cur.close()

    def __iter__(self):
        return iter(self._cur)

class PostgresConnectionWrapper:
    """Wraps psycopg2 connection to match sqlite3.Connection semantics."""
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor(cursor_factory=RealDictCursor))

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

def get_connection():
    """
    Returns an active database connection.
    Connects to Supabase PostgreSQL when DATABASE_URL is set;
    otherwise falls back to local SQLite audit_intelligence.db.
    """
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("DIRECT_URL")
    if db_url and HAS_PSYCOPG2:
        try:
            # Handle postgres:// scheme if provided by legacy Railway URLs
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            conn = psycopg2.connect(db_url)
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            print(f"[WARN] Failed to connect to PostgreSQL via DATABASE_URL ({e}). Falling back to SQLite.")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Projects Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id VARCHAR(32) PRIMARY KEY,
        code VARCHAR(32) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        type VARCHAR(64) NOT NULL,
        loc VARCHAR(255) NOT NULL,
        geo VARCHAR(64) NOT NULL,
        status VARCHAR(20) NOT NULL,  -- live, hold, upcoming, completed
        progress INTEGER DEFAULT 0,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        cleared_date DATE,
        hold_reason TEXT,
        closed_extra INTEGER DEFAULT 0,
        upd_at DATETIME NOT NULL,
        upd_by VARCHAR(100) NOT NULL
    );
    """)

    # 2. Non-Conformities (NCs) Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS non_conformities (
        code VARCHAR(32) PRIMARY KEY,
        project_id VARCHAR(32) NOT NULL,
        title VARCHAR(255) NOT NULL,
        sev VARCHAR(16) NOT NULL,    -- critical, major, minor, ofi
        zone VARCHAR(64) NOT NULL,
        trade VARCHAR(64) NOT NULL,
        assigned VARCHAR(128) NOT NULL,
        raised_date DATE NOT NULL,
        due_date DATE NOT NULL,
        status VARCHAR(32) NOT NULL,  -- Open, Assigned, Rectification submitted, Under verification, Reopened, Closed
        raised_by VARCHAR(100) NOT NULL,
        closed_date DATE,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    """)

    # 3. NC Audit Logs Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS nc_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nc_code VARCHAR(32) NOT NULL,
        event_date DATE NOT NULL,
        what VARCHAR(128) NOT NULL,
        message TEXT NOT NULL,
        FOREIGN KEY (nc_code) REFERENCES non_conformities(code) ON DELETE CASCADE
    );
    """)

    # 4. Inspections Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inspections (
        code VARCHAR(32) PRIMARY KEY,
        project_id VARCHAR(32) NOT NULL,
        title VARCHAR(128) NOT NULL,
        zone VARCHAR(64) NOT NULL,
        tpl VARCHAR(128) NOT NULL,
        eng VARCHAR(100),
        due_date DATE NOT NULL,
        status VARCHAR(32) NOT NULL, -- Required, Allocated, In progress, Pending review, Report issued
        items_count INTEGER DEFAULT 0,
        items_pass INTEGER DEFAULT 0,
        items_nc INTEGER DEFAULT 0,
        items_na INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    """)

    # 5. Approvals Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        code VARCHAR(32) PRIMARY KEY,
        project_id VARCHAR(32) NOT NULL,
        kind VARCHAR(64) NOT NULL,
        title VARCHAR(255) NOT NULL,
        by_user VARCHAR(100) NOT NULL,
        at_time DATETIME NOT NULL,
        ref_ins VARCHAR(32),
        ref_nc VARCHAR(32),
        status VARCHAR(20) DEFAULT 'Pending',
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    """)

    # 6. Action Items Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS action_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id VARCHAR(32) NOT NULL,
        title VARCHAR(255) NOT NULL,
        detail TEXT NOT NULL,
        due_date DATE NOT NULL,
        target_type VARCHAR(16) NOT NULL, -- nc, ins, project
        target_code VARCHAR(32) NOT NULL,
        is_resolved BOOLEAN DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    """)

    # 7. Evidence Photos Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS evidence_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nc_code VARCHAR(32) NOT NULL,
        stage VARCHAR(10) NOT NULL, -- before, after
        photo_url VARCHAR(512),
        geo_stamp VARCHAR(64),
        time_stamp DATETIME,
        by_user VARCHAR(100),
        FOREIGN KEY (nc_code) REFERENCES non_conformities(code) ON DELETE CASCADE
    );
    """)

    # 8. AI Generated Inspection Reports Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inspection_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ins_code VARCHAR(32) NOT NULL,
        project_id VARCHAR(32) NOT NULL,
        title VARCHAR(255) NOT NULL,
        executive_summary TEXT,
        content_markdown TEXT NOT NULL,
        model_used VARCHAR(64) NOT NULL,
        created_at DATETIME NOT NULL,
        created_by VARCHAR(100) NOT NULL,
        FOREIGN KEY (ins_code) REFERENCES inspections(code) ON DELETE CASCADE
    );
    """)

    from seed_master_checklist import init_master_tables
    init_master_tables(conn)

    conn.commit()
    conn.close()

def seed_database():
    """Populates the database with the initial dataset from the Audit Intelligence dashboard."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # Clear existing
    cur.execute("DELETE FROM evidence_photos;")
    cur.execute("DELETE FROM action_items;")
    cur.execute("DELETE FROM approvals;")
    cur.execute("DELETE FROM inspections;")
    cur.execute("DELETE FROM nc_audit_logs;")
    cur.execute("DELETE FROM non_conformities;")
    cur.execute("DELETE FROM projects;")

    projects = [
        ('psv', 'PRJ-0012', 'Purvanchal Skyline Vista', 'Luxury Residential', 'Noida Sector 94', '28.5383° N, 77.3720° E', 'live', 18, '2026-10-20', '2029-03-31', None, None, 9, '2026-11-01 13:10:00', 'Rohit Kale'),
        ('lct', 'PRJ-0015', 'Lumos Commercial Tower', 'Commercial', 'Gurugram Sector 65', '28.4023° N, 77.0679° E', 'live', 27, '2026-06-15', '2028-06-30', None, None, 6, '2026-11-01 10:05:00', 'Meera Iyer'),
        ('nlp', 'PRJ-0017', 'Ecotech Logistics Park', 'Industrial', 'Greater Noida, Ecotech III', '28.4744° N, 77.5040° E', 'live', 74, '2025-11-03', '2026-12-31', None, None, 21, '2026-10-31 18:20:00', 'Arjun Mehta'),
        ('t117', 'PRJ-0019', 'NCR Telecom Cluster 117', 'Telecom Tower', 'Noida Sector 150 · 8 sites', '28.4290° N, 77.4870° E', 'live', 41, '2026-08-03', '2027-01-29', None, None, 4, '2026-11-01 08:45:00', 'Vikram Singh'),
        ('rvv', 'PRJ-0011', 'Riverside Villas', 'Luxury Residential', 'Greater Noida West', '28.6034° N, 77.4310° E', 'hold', 33, '2025-09-01', '2027-08-31', None, 'Client stop-work notice. Revised structural drawings awaited.', 31, '2026-10-12 11:00:00', 'Priya Deshmukh'),
        ('s62', 'PRJ-0014', 'Sector 62 Data Centre', 'Industrial', 'Noida Sector 62', '28.6270° N, 77.3720° E', 'hold', 12, '2026-05-04', '2027-12-31', None, 'Funding approval pending with the client board.', 3, '2026-10-20 16:30:00', 'Priya Deshmukh'),
        ('yem', 'PRJ-0021', 'Yamuna Expressway Mall', 'Commercial', 'Greater Noida, Sector 22D', '28.4100° N, 77.5800° E', 'upcoming', 0, '2026-11-16', '2029-06-30', None, None, 0, '2026-10-29 14:00:00', 'Priya Deshmukh'),
        ('t124', 'PRJ-0022', 'NCR Telecom Cluster 124', 'Telecom Tower', 'Ghaziabad · 6 sites', '28.6692° N, 77.4538° E', 'upcoming', 0, '2026-12-01', '2027-05-31', None, None, 0, '2026-10-27 12:10:00', 'Priya Deshmukh'),
        ('s108', 'PRJ-0008', 'Sector 108 Residences', 'Luxury Residential', 'Noida Sector 108', '28.5440° N, 77.3740° E', 'completed', 100, '2024-04-01', '2026-09-30', '2026-09-30', None, 40, '2026-09-30 18:00:00', 'Priya Deshmukh'),
        ('t109', 'PRJ-0010', 'NCR Telecom Cluster 109', 'Telecom Tower', 'Noida Sector 135 · 5 sites', '28.4980° N, 77.4120° E', 'completed', 100, '2026-02-02', '2026-07-31', '2026-08-05', None, 17, '2026-08-05 11:20:00', 'Priya Deshmukh')
    ]
    cur.executemany("INSERT INTO projects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", projects)

    ncs = [
        # psv
        ('NC-0012-0078', 'psv', 'Honeycombing at column C7 to beam junction', 'critical', 'T3 · Floor 7', 'RCC', 'Shree Ram Constructions', '2026-10-21', '2026-10-24', 'Assigned', 'Vikram Singh', None),
        ('NC-0012-0081', 'psv', 'Cover blocks missing under slab bottom rebar', 'major', 'T3 · Floor 8', 'RCC', 'Shree Ram Constructions', '2026-10-27', '2026-11-03', 'Rectification submitted', 'Rohit Kale', None),
        ('NC-0012-0084', 'psv', 'Waterproofing lap under 100 mm at sunken slab', 'major', 'T2 · Floor 4', 'Waterproofing', 'AquaSeal Systems', '2026-10-19', '2026-10-26', 'Reopened', 'Anjali Rao', None),
        ('NC-0012-0074', 'psv', 'Shear wall plumb deviation 9 mm over 3 m', 'major', 'T1 · Floor 10', 'RCC', 'Shree Ram Constructions', '2026-10-08', '2026-10-15', 'Under verification', 'Vikram Singh', None),
        ('NC-0012-0071', 'psv', 'Rebar lap length short at beam B12', 'major', 'T3 · Floor 6', 'RCC', 'Shree Ram Constructions', '2026-10-12', '2026-10-19', 'Under verification', 'Rohit Kale', None),
        ('NC-0012-0086', 'psv', 'Blockwork joints thicker than 12 mm', 'minor', 'T2 · Floor 5', 'Masonry', 'Shree Ram Constructions', '2026-10-24', '2026-11-08', 'Assigned', 'Anjali Rao', None),
        ('NC-0012-0089', 'psv', 'Conduit not clamped before plastering', 'minor', 'T1 · Floor 11', 'Electrical', 'Volt Infra Services', '2026-10-30', '2026-11-14', 'Open', 'Vikram Singh', None),
        ('NC-0012-0090', 'psv', 'Curing log not maintained on site', 'ofi', 'T3 · Floor 7', 'RCC', 'Shree Ram Constructions', '2026-10-28', '2026-11-27', 'Assigned', 'Rohit Kale', None),
        ('NC-0012-0069', 'psv', 'Debris left in column formwork before pour', 'major', 'T1 · Floor 9', 'RCC', 'Shree Ram Constructions', '2026-10-09', '2026-10-16', 'Closed', 'Vikram Singh', '2026-10-14'),
        ('NC-0012-0066', 'psv', 'Shuttering joints not sealed', 'minor', 'T3 · Floor 5', 'RCC', 'Shree Ram Constructions', '2026-10-05', '2026-10-20', 'Closed', 'Rohit Kale', '2026-10-17'),
        # lct
        ('NC-0015-0031', 'lct', 'Glazing silicone discontinuous at mullion', 'major', 'Block A · Floor 6', 'Façade', 'ClearView Facades', '2026-10-22', '2026-10-29', 'Assigned', 'Meera Iyer', None),
        ('NC-0015-0034', 'lct', 'HVAC duct hanger spacing over 2.4 m', 'minor', 'Block A · Floor 3', 'HVAC', 'CoolAir Projects', '2026-10-25', '2026-11-09', 'Rectification submitted', 'Arjun Mehta', None),
        ('NC-0015-0036', 'lct', 'Fire stop sealant missing at service shaft', 'major', 'Core · Floor 4', 'Fire', 'SafeGuard Fire Systems', '2026-10-31', '2026-11-07', 'Open', 'Meera Iyer', None),
        ('NC-0015-0028', 'lct', 'Anchor bolt edge distance below spec', 'major', 'Block A · Floor 5', 'Façade', 'ClearView Facades', '2026-10-10', '2026-10-17', 'Closed', 'Meera Iyer', '2026-10-16'),
        # nlp
        ('NC-0017-0052', 'nlp', 'Floor joint filler incomplete in Bay 4', 'minor', 'Warehouse 2 · Bay 4', 'Flooring', 'Apex Floorings', '2026-10-21', '2026-11-05', 'Assigned', 'Arjun Mehta', None),
        ('NC-0017-0055', 'nlp', 'Dock leveller safety signage missing', 'ofi', 'Warehouse 2 · Docks', 'Finishes', 'Apex Floorings', '2026-10-27', '2026-11-26', 'Assigned', 'Arjun Mehta', None),
        ('NC-0017-0049', 'nlp', 'Roof sheet overlap short at ridge', 'major', 'Warehouse 2 · Roof', 'Steel', 'Skyline Sheeting', '2026-10-06', '2026-10-13', 'Closed', 'Arjun Mehta', '2026-10-12'),
        # t117
        ('NC-0019-0012', 't117', 'Earth pit resistance 7.2 Ω, limit 5 Ω', 'critical', 'Site 117-04 · Earthing', 'Electrical', 'Volt Infra Services', '2026-10-29', '2026-11-01', 'Assigned', 'Vikram Singh', None),
        ('NC-0019-0014', 't117', 'Tower bolt torque marks missing', 'major', 'Site 117-06 · Erection', 'Steel', 'Volt Infra Services', '2026-10-15', '2026-10-22', 'Reopened', 'Vikram Singh', None),
        ('NC-0019-0015', 't117', 'Shelter door seal damaged', 'minor', 'Site 117-02 · Shelter', 'Civil', 'Volt Infra Services', '2026-10-30', '2026-11-14', 'Open', 'Vikram Singh', None),
        # rvv
        ('NC-0011-0140', 'rvv', 'Hairline cracks in plinth beam PB-14', 'major', 'Villa cluster B · Plinth', 'RCC', 'BuildRight Infra', '2026-10-05', '2026-10-12', 'Assigned', 'Rohit Kale', None),
        ('NC-0011-0142', 'rvv', 'Exposed rebar not protected during halt', 'minor', 'Villa cluster C · Columns', 'RCC', 'BuildRight Infra', '2026-10-09', '2026-10-24', 'Open', 'Rohit Kale', None),
        # s62
        ('NC-0014-0021', 's62', 'Raft waterproofing membrane torn at edge', 'minor', 'Main block · Raft', 'Waterproofing', 'AquaSeal Systems', '2026-09-28', '2026-10-13', 'Assigned', 'Anjali Rao', None),
        # s108
        ('NC-0008-0412', 's108', 'Paint shade variation in lobby', 'minor', 'Tower A · Lobby', 'Finishes', 'Colorcraft Painters', '2026-09-12', '2026-09-27', 'Closed', 'Anjali Rao', '2026-09-24'),
        ('NC-0008-0409', 's108', 'Lift pit waterproofing seepage', 'major', 'Tower B · Lift pit', 'Waterproofing', 'AquaSeal Systems', '2026-09-02', '2026-09-09', 'Closed', 'Anjali Rao', '2026-09-08'),
        # t109
        ('NC-0010-0033', 't109', 'Cable tray earthing jumper missing', 'minor', 'Site 109-03 · Shelter', 'Electrical', 'Volt Infra Services', '2026-07-20', '2026-08-04', 'Closed', 'Vikram Singh', '2026-07-29')
    ]
    cur.executemany("INSERT INTO non_conformities VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", ncs)

    inspections = [
        ('INS-0012-0345', 'psv', 'Slab pre-pour', 'T3 · Floor 9', 'RCC slab pre-pour v3', 'Rohit Kale', '2026-10-31', 'Pending review', 48, 45, 3, 0),
        ('INS-0012-0342', 'psv', 'Blockwork', 'T2 · Floor 6', 'Masonry & shell v2', 'Anjali Rao', '2026-10-30', 'Pending review', 36, 34, 1, 1),
        ('INS-0012-0347', 'psv', 'Shuttering check', 'T3 · Floor 10', 'Formwork v2', 'Rohit Kale', '2026-11-02', 'In progress', 0, 0, 0, 0),
        ('INS-0012-0338', 'psv', 'Electrical conduit', 'T1 · Floor 11', 'Electrical rough-in v1', 'Vikram Singh', '2026-10-29', 'Allocated', 0, 0, 0, 0),
        ('INS-0012-0349', 'psv', 'Masonry check', 'T2 · Floor 7', 'Masonry & shell v2', None, '2026-11-04', 'Required', 0, 0, 0, 0),
        ('INS-0012-0350', 'psv', 'MEP rough-in', 'T1 · Floor 12', 'MEP rough-in v1', None, '2026-11-06', 'Required', 0, 0, 0, 0),
        ('INS-0012-0336', 'psv', 'Column pre-pour', 'T3 · Floor 7', 'RCC column v2', 'Vikram Singh', '2026-10-21', 'Report issued', 32, 30, 2, 0),

        ('INS-0015-0118', 'lct', 'Façade bracket anchorage', 'Block A · Floor 7', 'Façade & glazing v2', 'Meera Iyer', '2026-10-31', 'Pending review', 40, 39, 1, 0),
        ('INS-0015-0119', 'lct', 'HVAC rough-in', 'Block A · Floor 4', 'HVAC v1', 'Arjun Mehta', '2026-11-03', 'Allocated', 0, 0, 0, 0),
        ('INS-0015-0121', 'lct', 'Fire stopping', 'Core · Floor 5', 'Fire protection v2', None, '2026-11-05', 'Required', 0, 0, 0, 0),
        ('INS-0015-0110', 'lct', 'Curtain wall mock-up', 'Block A · Floor 2', 'Façade & glazing v2', 'Meera Iyer', '2026-10-12', 'Report issued', 40, 38, 2, 0),

        ('INS-0017-0204', 'nlp', 'Roof sheeting final', 'Warehouse 2 · Roof', 'Pre-engineered building v1', 'Arjun Mehta', '2026-10-31', 'Pending review', 30, 30, 0, 0),
        ('INS-0017-0207', 'nlp', 'Fire hydrant pressure test', 'Yard · Ring main', 'Fire protection v2', None, '2026-11-05', 'Required', 0, 0, 0, 0),
        ('INS-0017-0201', 'nlp', 'Floor flatness survey', 'Warehouse 2 · Bays 1–6', 'Industrial flooring v1', 'Arjun Mehta', '2026-10-20', 'Report issued', 24, 22, 2, 0),

        ('INS-0019-0061', 't117', 'Foundation pre-pour', 'Site 117-07 · Foundation', 'Telecom foundation v4', 'Vikram Singh', '2026-10-30', 'Pending review', 28, 27, 1, 0),
        ('INS-0019-0062', 't117', 'Tower erection', 'Site 117-05 · Erection', 'Telecom erection v4', 'Vikram Singh', '2026-11-02', 'Allocated', 0, 0, 0, 0),
        ('INS-0019-0064', 't117', 'Earthing re-test', 'Site 117-04 · Earthing', 'Telecom earthing v4', None, '2026-11-03', 'Required', 0, 0, 0, 0),
        ('INS-0019-0058', 't117', 'Shelter installation', 'Site 117-02 · Shelter', 'Telecom shelter v4', 'Vikram Singh', '2026-10-24', 'Report issued', 22, 20, 2, 0),

        ('INS-0011-0402', 'rvv', 'Plinth beam check', 'Villa cluster B · Plinth', 'RCC beam v2', 'Rohit Kale', '2026-10-05', 'Report issued', 30, 28, 2, 0),
        ('INS-0021-0001', 'yem', 'Site survey & setting-out', 'Site · Grids A–F', 'Site preparation v1', None, '2026-11-16', 'Required', 0, 0, 0, 0)
    ]
    cur.executemany("INSERT INTO inspections VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", inspections)

    approvals = [
        ('AP-0012-031', 'psv', 'Inspection report', 'Slab pre-pour · T3 Floor 9', 'Rohit Kale', '2026-10-31 17:40:00', 'INS-0012-0345', None, 'Pending'),
        ('AP-0012-030', 'psv', 'NC closure', 'Rebar lap length short at beam B12', 'Rohit Kale', '2026-10-31 11:15:00', None, 'NC-0012-0071', 'Pending'),
        ('AP-0012-029', 'psv', 'Inspection report', 'Blockwork · T2 Floor 6', 'Anjali Rao', '2026-10-30 16:05:00', 'INS-0012-0342', None, 'Pending'),
        ('AP-0015-012', 'lct', 'Inspection report', 'Façade bracket anchorage · Floor 7', 'Meera Iyer', '2026-11-01 09:30:00', 'INS-0015-0118', None, 'Pending'),
        ('AP-0017-019', 'nlp', 'Inspection report', 'Roof sheeting final · Warehouse 2', 'Arjun Mehta', '2026-10-31 15:00:00', 'INS-0017-0204', None, 'Pending'),
        ('AP-0019-007', 't117', 'Inspection report', 'Foundation pre-pour · Site 117-07', 'Vikram Singh', '2026-10-30 12:20:00', 'INS-0019-0061', None, 'Pending'),
        ('AP-0021-001', 'yem', 'Inspection & Test Plan', 'ITP Rev 0 · 9 stages, 34 hold points', 'Meera Iyer', '2026-10-29 14:00:00', None, None, 'Pending')
    ]
    cur.executemany("INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,?)", approvals)

    actions = [
        ('psv', 'Escalate critical NC', 'NC-0012-0078 is with Shree Ram Constructions, past due', '2026-10-24', 'nc', 'NC-0012-0078', 0),
        ('psv', 'Chase overdue inspection', 'Electrical conduit · T1 Floor 11, Vikram Singh', '2026-10-29', 'ins', 'INS-0012-0338', 0),
        ('psv', 'Allocate inspection', 'Masonry check · T2 Floor 7 has no engineer', '2026-11-04', 'ins', 'INS-0012-0349', 0),
        ('psv', 'Allocate inspection', 'MEP rough-in · T1 Floor 12 has no engineer', '2026-11-06', 'ins', 'INS-0012-0350', 0),
        ('lct', 'Chase contractor', 'NC-0015-0031 is with ClearView Facades, past due', '2026-10-29', 'nc', 'NC-0015-0031', 0),
        ('lct', 'Allocate inspection', 'Fire stopping · Core Floor 5 has no engineer', '2026-11-05', 'ins', 'INS-0015-0121', 0),
        ('nlp', 'Allocate inspection', 'Fire hydrant pressure test · Yard has no engineer', '2026-11-05', 'ins', 'INS-0017-0207', 0),
        ('t117', 'Escalate reopened NC', 'NC-0019-0014 failed verification', '2026-10-22', 'nc', 'NC-0019-0014', 0),
        ('t117', 'Allocate inspection', 'Earthing re-test · Site 117-04 has no engineer', '2026-11-03', 'ins', 'INS-0019-0064', 0),
        ('rvv', 'Confirm restart date', 'Client to confirm restart after drawing revision', '2026-11-10', 'project', 'rvv', 0),
        ('yem', 'Assign inspection team', 'No engineers are tagged to this project yet', '2026-11-10', 'project', 'yem', 0),
        ('yem', 'Allocate first inspection', 'Site survey and setting-out', '2026-11-16', 'ins', 'INS-0021-0001', 0),
        ('t124', 'Approve checklist set', 'Telecom tower checklists v4 for 6 sites', '2026-11-20', 'project', 't124', 0)
    ]
    cur.executemany("INSERT INTO action_items (project_id, title, detail, due_date, target_type, target_code, is_resolved) VALUES (?,?,?,?,?,?,?)", actions)

    conn.commit()
    conn.close()
    print("Audit Intelligence database created and seeded successfully!")

if __name__ == "__main__":
    seed_database()
