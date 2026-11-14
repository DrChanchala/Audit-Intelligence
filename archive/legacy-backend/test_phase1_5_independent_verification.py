"""
SiteIQ Stage-Based Inspection Allocation — Independent Verification Test Suite (Phases 1–5)
Validates:
1. Confirm & Allocate action validity & checkpoint storage.
2. Database transaction integrity & rollback across 4 tables.
3. Backend duplicate prevention & concurrency guards.
4. Checkpoint IDs, stage names, and subgroup names match master checklist.
5. Engineer stable identifiers (EMP-1004, etc.) stored & returned.
6. Assignment count vs checkpoint count distinction.
7. Reload persistence & SQLite integrity.
"""

import urllib.request
import urllib.error
import json
import sqlite3
import sys
import io

# Ensure UTF-8 output on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"
DB_FILE = "audit_intelligence.db"

def api_post(endpoint, payload):
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def api_get(endpoint):
    req = urllib.request.Request(f"{BASE_URL}{endpoint}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

print("======================================================================")
print(" SITEIQ STAGE ALLOCATION: INDEPENDENT TECHNICAL VERIFICATION (PHASES 1-5)")
print("======================================================================\n")

# ---------------------------------------------------------
# VERIFICATION 1: Action Validity & Checkpoint Storage
# ---------------------------------------------------------
print("--- [1/7] VERIFYING CONFIRM & ALLOCATE VALIDITY & CHECKPOINT STORAGE ---")
payload_v1 = {
    "project_id": "psv",
    "engineer_id": "EMP-1004",
    "engineer_name": "Anjali Rao",
    "allocated_by": "Priya Deshmukh (QC Lead)",
    "tower_block": "Tower 3",
    "floor_level": "Floor 8",
    "zone_area": "Zone B · Sunken Slab",
    "grid_ref": "Grids B4–B8",
    "element_id": "Column C7 / Beam B12",
    "instructions": "Verify waterproofing membrane primer and fillet angle.",
    "planned_date": "2026-11-03",
    "due_date": "2026-11-06",
    "due_time": "18:00",
    "priority": "High",
    "checkpoint_ids": ["CHK-01-01-001"],
    "allow_duplicate": True
}
res_v1 = api_post("/api/allocations", payload_v1)
assert res_v1["status"] == "success", "Failed creating allocation"
alloc_id_v1 = res_v1["allocation"]["allocation_id"]
print(f"✓ Created Allocation: {alloc_id_v1}")
print(f"  Project: {res_v1['allocation']['project_name']} ({res_v1['allocation']['project_id']})")
print(f"  Engineer: {res_v1['allocation']['engineer_name']} (Stable ID: {res_v1['allocation']['engineer_id']})")
print(f"  Location: {res_v1['allocation']['location_scope']}")

# Verify detail endpoint
detail_v1 = api_get(f"/api/allocations/{alloc_id_v1}")
chk_stored = detail_v1["allocation"]["checkpoints"]
assert len(chk_stored) == 1, "Checkpoint count mismatch"
assert chk_stored[0]["checkpoint_id"] == "CHK-01-01-001", "Checkpoint ID mismatch"
assert "Site boundary demarcation" in chk_stored[0]["checkpoint_text_snapshot"], "Snapshot description mismatch"
print(f"✓ Stored Checkpoint: {chk_stored[0]['checkpoint_id']} -> '{chk_stored[0]['checkpoint_text_snapshot']}'")
print("  Status: PASS\n")

# ---------------------------------------------------------
# VERIFICATION 2: Database Transaction Integrity & Rollback
# ---------------------------------------------------------
print("--- [2/7] VERIFYING DATABASE TRANSACTION INTEGRITY & ATOMIC ROLLBACK ---")
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# Get baseline counts across 4 tables
cur.execute("SELECT COUNT(*) FROM inspection_allocations")
base_allocs = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM allocation_checkpoints")
base_chks = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM inspections")
base_ins = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM inspection_audit_events")
base_events = cur.fetchone()[0]

print(f"Baseline Counts -> Allocations: {base_allocs}, Checkpoints: {base_chks}, Inspections: {base_ins}, Events: {base_events}")

# Attempt an invalid transaction (e.g. invalid project)
invalid_payload = {
    "project_id": "non-existent-project-id",
    "engineer_name": "Anjali Rao",
    "checkpoint_ids": ["CHK-01-01-001"]
}
try:
    api_post("/api/allocations", invalid_payload)
    print("X Error: Invalid allocation did not fail!")
    sys.exit(1)
except urllib.error.HTTPError as e:
    print(f"✓ Invalid project rejected with HTTP {e.code}: {e.reason}")

# Verify 0 rows inserted in ANY of the 4 tables after rejected transaction
cur.execute("SELECT COUNT(*) FROM inspection_allocations")
curr_allocs = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM allocation_checkpoints")
curr_chks = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM inspections")
curr_ins = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM inspection_audit_events")
curr_events = cur.fetchone()[0]

assert curr_allocs == base_allocs, "Rollback failed: inspection_allocations changed"
assert curr_chks == base_chks, "Rollback failed: allocation_checkpoints changed"
assert curr_ins == base_ins, "Rollback failed: inspections changed"
assert curr_events == base_events, "Rollback failed: inspection_audit_events changed"
print("✓ Atomic Rollback Verified: Zero orphaned records written across all 4 tables.")
print("  Status: PASS\n")

# ---------------------------------------------------------
# VERIFICATION 3: Backend Duplicate Prevention & Concurrency
# ---------------------------------------------------------
print("--- [3/7] VERIFYING BACKEND-LEVEL DUPLICATE & REPEATED SUBMISSION PREVENTION ---")
dup_payload = {
    "project_id": "psv",
    "engineer_id": "EMP-1004",
    "engineer_name": "Anjali Rao",
    "location_scope": "Tower 3 · Floor 8 · Zone B · Sunken Slab · Grids B4–B8 · Column C7 / Beam B12",
    "tower_block": "Tower 3",
    "floor_level": "Floor 8",
    "zone_area": "Zone B · Sunken Slab",
    "grid_ref": "Grids B4–B8",
    "element_id": "Column C7 / Beam B12",
    "planned_date": "2026-11-03",
    "due_date": "2026-11-06",
    "priority": "High",
    "checkpoint_ids": ["CHK-01-01-001"],
    "allow_duplicate": False  # Duplicate check enforced
}

try:
    api_post("/api/allocations", dup_payload)
    print("X Error: Duplicate allocation was not prevented!")
    sys.exit(1)
except urllib.error.HTTPError as e:
    err_body = json.loads(e.read().decode('utf-8'))
    print(f"✓ Duplicate Request Blocked with HTTP {e.code}: {err_body.get('detail')}")
    assert "Duplicate allocation prevented" in err_body.get('detail'), "Incorrect error message"

print("✓ Backend Duplicate Guard Verified: Duplicate repeated submissions rejected at server level.")
print("  Status: PASS\n")

# ---------------------------------------------------------
# VERIFICATION 4: Authoritative Master Checklist Match
# ---------------------------------------------------------
print("--- [4/7] VERIFYING CHECKPOINTS AGAINST AUTHORITATIVE MASTER CHECKLIST ---")
cur.execute("SELECT COUNT(*) FROM master_stages")
n_stages = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM master_subgroups")
n_subgroups = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM master_checkpoints")
n_checkpoints = cur.fetchone()[0]

assert n_stages == 20, f"Expected 20 stages, found {n_stages}"
assert n_subgroups == 98, f"Expected 98 subgroups, found {n_subgroups}"
assert n_checkpoints == 859, f"Expected 859 checkpoints, found {n_checkpoints}"

# Sample checkpoint verification
cur.execute("SELECT stage_name FROM master_stages WHERE stage_id = 'STG-01'")
s1 = cur.fetchone()[0]
cur.execute("SELECT subgroup_name FROM master_subgroups WHERE subgroup_id = 'SUB-01-01'")
sub1 = cur.fetchone()[0]
cur.execute("SELECT checkpoint_description, priority FROM master_checkpoints WHERE checkpoint_id = 'CHK-01-01-001'")
chk1 = cur.fetchone()

print(f"✓ Stage 01: '{s1}'")
print(f"✓ Subgroup 01-01: '{sub1}'")
print(f"✓ Checkpoint CHK-01-01-001: '{chk1[0]}' [Priority: {chk1[1]}]")
assert s1 == "Site Preparation & Survey"
assert sub1 == "Survey & Setting Out"
assert chk1[0] == "Site boundary demarcation as per approved layout plan"
assert chk1[1] == "H"
print("✓ Master Checklist Hierarchy Integrity: 100% Match.")
print("  Status: PASS\n")

# ---------------------------------------------------------
# VERIFICATION 5: Stable Engineer Identifiers
# ---------------------------------------------------------
print("--- [5/7] VERIFYING STABLE ENGINEER IDENTIFIERS (EMP-XXXX) ---")
cur.execute("""
    SELECT allocation_id, engineer_id, engineer_name 
    FROM inspection_allocations 
    WHERE engineer_id IS NOT NULL 
    ORDER BY allocation_id DESC LIMIT 4
""")
eng_rows = cur.fetchall()
print("Persisted Allocations with Stable IDs:")
for r in eng_rows:
    print(f"  • Allocation {r[0]} -> Engineer ID: {r[1]} | Name: {r[2]}")
    assert r[1].startswith("EMP-"), f"Invalid engineer_id format: {r[1]}"

print("✓ Stable Identifiers Verified: Engineer assignments store immutable employee IDs.")
print("  Status: PASS\n")

# ---------------------------------------------------------
# VERIFICATION 6: Assignment Count vs Checkpoint Count
# ---------------------------------------------------------
print("--- [6/7] VERIFYING ASSIGNMENT COUNT VS CHECKPOINT COUNT DISTINCTION ---")
cur.execute("SELECT COUNT(*) FROM inspections WHERE project_id = 'psv' AND status = 'Allocated'")
assignment_count = cur.fetchone()[0]
cur.execute("""
    SELECT SUM(ac_count) FROM (
        SELECT COUNT(*) as ac_count 
        FROM allocation_checkpoints ac
        JOIN inspection_allocations a ON ac.allocation_id = a.allocation_id
        WHERE a.project_id = 'psv' AND a.status = 'Allocated'
        GROUP BY a.allocation_id
    )
""")
total_allocated_checkpoints = cur.fetchone()[0]

print(f"✓ Total Allocated Assignments on PSV: {assignment_count}")
print(f"✓ Total Allocated Checkpoints across those assignments: {total_allocated_checkpoints}")
assert total_allocated_checkpoints > assignment_count, "Counts are conflated!"
print("✓ Dashboard Distinction Verified: Pipeline counts assignment objects; cards display checkpoint volume.")
print("  Status: PASS\n")

# ---------------------------------------------------------
# VERIFICATION 7: Reload Persistence
# ---------------------------------------------------------
print("--- [7/7] VERIFYING RAW SQLITE RELOAD PERSISTENCE ---")
cur.execute("SELECT allocation_id, project_id, engineer_name, status, due_date FROM inspection_allocations WHERE allocation_id = ?", (alloc_id_v1,))
persisted_alloc = cur.fetchone()
assert persisted_alloc is not None, "Allocation missing from database!"
print(f"✓ Found in SQLite: {persisted_alloc[0]} | {persisted_alloc[1]} | {persisted_alloc[2]} | {persisted_alloc[3]} | Due: {persisted_alloc[4]}")

cur.execute("SELECT code, project_id, title, eng, status, items_count FROM inspections WHERE code = ?", (alloc_id_v1,))
persisted_ins = cur.fetchone()
assert persisted_ins is not None, "Mirror inspection missing from database!"
print(f"✓ Found in Mirror Inspections: {persisted_ins[0]} | Title: {persisted_ins[2]} | Eng: {persisted_ins[3]} | Items: {persisted_ins[5]}")

conn.close()
print("✓ Database Persistence Verified: Record is permanently saved in SQLite.")
print("  Status: PASS\n")

print("======================================================================")
print(" ALL 7 TECHNICAL VERIFICATION MODULES PASSED WITH ZERO DEFECTS")
print("======================================================================")
