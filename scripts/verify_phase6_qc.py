"""Playwright end-to-end verification script for Phase 6 Gate (QC Lead Workspace).

Verifies:
- QC lead logs in → allocates 5 checkpoints to an engineer → sees it listed.
- Approves a seeded pending-review inspection → generates the dossier.
- 0 console errors at both viewports (Desktop 1366×900 and Mobile 390×844).
- Saves gate screenshots:
  - Wizard Step 1: Parameters & Location
  - Wizard Step 2: Checkpoint Selection
  - Wizard Step 3: Review & Confirm
  - Inspection Sheet: Drawer with checkpoints, photos, audit log, and dossier
  - Mobile QC Workspace
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

# Setup clean temporary SQLite database
temp_dir = tempfile.mkdtemp()
db_path = os.path.join(temp_dir, "phase6_qc_e2e.db")
if "DATABASE_URL" in os.environ:
    del os.environ["DATABASE_URL"]
os.environ["SQLITE_PATH"] = str(db_path)
os.environ["APP_ENV"] = "development"
os.environ["SITEIQ_JWT_SECRET"] = "phase6-qc-test-secret-key-at-least-32-chars-long!"
os.environ["UPLOAD_DIR"] = os.path.join(temp_dir, "uploads")
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.security import hash_password
from app.db.connection import get_database
from app.db.schema import init_schema, load_master_checklist
from app.main import app

# Seed database
db = get_database()
with db.session() as s:
    init_schema(s)
    load_master_checklist(s)

    # Seed Organization A
    s.execute("INSERT OR REPLACE INTO organizations (id, name, code, industry) VALUES ('ORG-A', 'Apex Infrastructure', 'APEX', 'Commercial Contracting')")
    hashed = hash_password("Password123!")

    # QC Lead & Engineer
    s.execute(
        "INSERT OR REPLACE INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, status) "
        "VALUES ('USR-QC-A', 'ORG-A', 'qc@apexinfra.com', ?, 'Priya Patel', 'qc_lead', 'EMP-101', 'Structural QC Lead', 'active')",
        (hashed,),
    )
    s.execute(
        "INSERT OR REPLACE INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, status) "
        "VALUES ('USR-ENG-A', 'ORG-A', 'engineer@apexinfra.com', ?, 'Ramesh Kumar', 'engineer', 'EMP-201', 'RCC & Concrete', 'active')",
        (hashed,),
    )

    # Project
    s.execute(
        "INSERT OR REPLACE INTO projects (id, org_id, code, name, type, loc, geo, status, progress, start_date, end_date, upd_by) "
        "VALUES ('PRJ-001', 'ORG-A', 'PRJ-HB', 'Apex Horizon Tower B', 'Commercial High-Rise', 'Bengaluru, KA', '12.9716, 77.5946', 'live', 45, '2026-01-15', '2027-06-30', 'Priya Patel')"
    )

    # Seed Pending Review Allocation
    s.execute(
        "INSERT OR REPLACE INTO inspection_allocations ("
        "allocation_id, project_id, engineer_id, engineer_name, allocated_by, "
        "location_scope, tower_block, floor_level, zone_area, grid_ref, element_id, instructions, "
        "planned_date, due_date, due_time, priority, status, linked_ins_code"
        ") VALUES ("
        "'ALC-PENDING-01', 'PRJ-001', 'USR-ENG-A', 'Ramesh Kumar', 'Priya Patel', "
        "'Tower B · Level 3 · Zone 1 · Grid A1-B3 · SLAB-301', 'Tower B', 'Level 3', 'Zone 1', 'Grid A1-B3', 'SLAB-301', 'Verify cover depth and rebar spacing', "
        "'2026-11-10', '2026-11-12', '18:00', 'High', 'Pending review', 'ALC-PENDING-01'"
        ")"
    )
    s.execute(
        "INSERT OR REPLACE INTO inspections (code, project_id, title, zone, tpl, eng, due_date, status, items_count, items_pass, items_nc, items_na) "
        "VALUES ('ALC-PENDING-01', 'PRJ-001', 'Level 3 Slab Reinforcement Pre-Pour', 'Tower B · Level 3', 'Structure', 'Ramesh Kumar', '2026-11-12', 'Pending review', 3, 2, 1, 0)"
    )

    # Seed checkpoints for ALC-PENDING-01
    sample_checkpoints = s.all("SELECT * FROM master_checkpoints LIMIT 3")
    for i, chk in enumerate(sample_checkpoints):
        result = "OK" if i < 2 else "NC"
        remarks = "Compliant with IS 456" if result == "OK" else "Spacing exceeded by 15mm at grid intersection"
        s.execute(
            "INSERT INTO allocation_checkpoints (allocation_id, checkpoint_id, stage_id, subgroup_id, stage_name, "
            "subgroup_name, checkpoint_text_snapshot, priority, result_status, observations) "
            "VALUES ('ALC-PENDING-01', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (chk["checkpoint_id"], chk["stage_id"], chk["subgroup_id"], "Structure", "Reinforcement", chk["checkpoint_description"], chk["priority"], result, remarks)
        )

# Start test server in background thread
PORT = 8766
config = uvicorn.Config(app=app, host="127.0.0.1", port=PORT, log_level="warning")
server = uvicorn.Server(config)
server_thread = threading.Thread(target=server.run, daemon=True)
server_thread.start()

time.sleep(1.5)

ARTIFACT_DIR = Path(r"C:\Users\Chanchala\.gemini\antigravity\brain\4e7bbfa4-c89c-448c-b236-a4c9ad6887cf")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

console_errors = []


def on_console(msg):
    if msg.type == "error":
        console_errors.append(f"Console Error: {msg.text}")


def on_page_error(err):
    console_errors.append(f"Page Error: {err}")


def run_gate():
    global console_errors
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. Desktop Viewport (1366 × 900)
        # -------------------------------------------------------------
        print("\n--- Verifying Desktop QC Lead Flow (1366x900) ---")
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        page = context.new_page()
        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("dialog", lambda dialog: dialog.accept())

        # 1.1 QC Lead Login
        print("Navigating to /login...", flush=True)
        page.goto(f"http://127.0.0.1:{PORT}/login")
        print("Filling credentials...", flush=True)
        page.fill("#signInEmail", "qc@apexinfra.com")
        page.fill("#signInPassword", "Password123!")
        print("Submitting login form...", flush=True)
        page.click("#signInSubmitBtn")

        # Expect redirect to /qc
        print("Waiting for /qc redirect...", flush=True)
        page.wait_for_url(f"http://127.0.0.1:{PORT}/qc", timeout=8000)
        print("Redirected to /qc successfully!", flush=True)
        page.wait_for_selector(".tabs-nav")
        time.sleep(1.0)
        assert len(console_errors) == 0, f"Console errors on QC Overview: {console_errors}"

        # 1.2 Navigate to Allocate Wizard
        print("Switching to allocate wizard tab...", flush=True)
        page.click('.qc-tab-btn[data-tab="allocate"]')
        page.wait_for_selector("#step1Container:not(.d-none)")
        time.sleep(0.5)

        # Fill Step 1 Parameters
        print("Filling Step 1 Parameters...", flush=True)
        page.select_option("#wizProject", "PRJ-001")
        page.select_option("#wizEngineer", index=1)
        page.fill("#wizTitle", "Level 5 Shear Wall Reinforcement & Conduits")
        page.fill("#wizTower", "Tower B")
        page.fill("#wizFloor", "Level 5")
        page.fill("#wizZone", "Zone 2")
        page.fill("#wizGrid", "Grid E1-F4")
        page.fill("#wizElement", "SW-501")
        page.fill("#wizInstructions", "Mandatory visual inspection before formwork closing.")

        step1_shot_path = ARTIFACT_DIR / "qc_wizard_step1.png"
        page.screenshot(path=str(step1_shot_path), full_page=True)
        print(f"Captured: {step1_shot_path.name}", flush=True)

        # Click Next → Step 2 (Checklist Browser)
        print("Clicking Next to Step 2...", flush=True)
        page.click("#btnStep1Next")
        page.wait_for_selector("#step2Container:not(.d-none)")
        page.wait_for_selector("#checklistTreeContainer")
        time.sleep(1.0)

        # Select 5 checkpoints
        print("Selecting checkpoints...", flush=True)
        checkboxes = page.locator(".chk-checkbox")
        chk_count = checkboxes.count()
        assert chk_count >= 5, f"Expected at least 5 checkpoints, found {chk_count}"
        for i in range(5):
            checkboxes.nth(i).check()

        time.sleep(0.5)
        step2_shot_path = ARTIFACT_DIR / "qc_wizard_step2.png"
        page.screenshot(path=str(step2_shot_path), full_page=True)
        print(f"Captured: {step2_shot_path.name}", flush=True)

        # Click Next → Step 3 (Review & Confirm)
        print("Clicking Next to Step 3...", flush=True)
        page.click("#btnStep2Next")
        page.wait_for_selector("#step3Container:not(.d-none)")
        page.wait_for_selector("#revCount")
        time.sleep(0.5)

        assert "5 checkpoints" in page.content()
        step3_shot_path = ARTIFACT_DIR / "qc_wizard_step3.png"
        page.screenshot(path=str(step3_shot_path), full_page=True)
        print(f"Captured: {step3_shot_path.name}", flush=True)

        # Confirm & Allocate
        print("Confirming allocation...", flush=True)
        page.click("#btnConfirmAllocate")

        # Expect transition to Inspections Directory
        page.wait_for_selector("#panel-inspections:not(.d-none)", timeout=5000)
        time.sleep(1.0)

        # Verify newly allocated inspection is listed
        content = page.content()
        assert "Level 5 Shear Wall" in content or "SW-501" in content
        print("Newly allocated inspection verified in directory!")

        # 1.3 Open Pending Review Inspection in Side Sheet
        page.click('.btn-open-drawer[data-id="ALC-PENDING-01"]')
        page.wait_for_selector("#inspectionDrawerBackdrop.active")
        page.wait_for_selector("#drawerBody")
        time.sleep(1.0)

        # Capture side sheet drawer screenshot
        sheet_shot_path = ARTIFACT_DIR / "qc_inspection_sheet.png"
        page.screenshot(path=str(sheet_shot_path), full_page=True)
        print(f"Captured: {sheet_shot_path.name}")

        # 1.4 Approve the Inspection
        print("Clicking Approve...", flush=True)
        page.click("#btnDrawerApprove")
        page.wait_for_selector("#inspectionDrawerBackdrop", state="hidden")
        time.sleep(1.0)

        # Reopen to verify Approved / Report Issued status
        print("Reopening drawer to view Report Issued status...", flush=True)
        page.click('.btn-open-drawer[data-id="ALC-PENDING-01"]')
        page.wait_for_selector("#inspectionDrawerBackdrop.active")
        time.sleep(1.0)

        # 1.5 Generate AI Dossier
        print("Clicking Generate Dossier...", flush=True)
        page.click("#btnGenerateDossier")

        # Verify dossier rendered
        page.wait_for_selector("#renderedDossierArticle", timeout=10000)
        dossier_shot_path = ARTIFACT_DIR / "qc_dossier_approved.png"
        page.screenshot(path=str(dossier_shot_path), full_page=True)
        print(f"Captured: {dossier_shot_path.name}", flush=True)

        assert len(console_errors) == 0, f"Console errors on QC Desktop: {console_errors}"
        context.close()

        # -------------------------------------------------------------
        # 2. Mobile Viewport (390 × 844)
        # -------------------------------------------------------------
        print("\n--- Verifying Mobile QC Lead Flow (390x844) ---")
        console_errors = []
        m_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            is_mobile=True,
            has_touch=True,
        )
        m_page = m_context.new_page()
        m_page.on("console", on_console)
        m_page.on("pageerror", on_page_error)
        m_page.on("dialog", lambda dialog: dialog.accept())

        m_page.goto(f"http://127.0.0.1:{PORT}/login")
        m_page.fill("#signInEmail", "qc@apexinfra.com")
        m_page.fill("#signInPassword", "Password123!")
        m_page.click("#signInSubmitBtn")

        m_page.wait_for_url(f"http://127.0.0.1:{PORT}/qc", timeout=5000)
        m_page.wait_for_selector(".tabs-nav")
        time.sleep(1.0)

        # Switch to Inspections tab on mobile
        m_page.click('.qc-tab-btn[data-tab="inspections"]')
        m_page.wait_for_selector("#inspectionsTable")
        time.sleep(0.5)

        # Check horizontal scroll
        body_scroll_w = m_page.evaluate("document.body.scrollWidth")
        body_client_w = m_page.evaluate("document.body.clientWidth")
        assert body_scroll_w <= body_client_w + 2, f"Horizontal scroll detected on mobile QC: {body_scroll_w} > {body_client_w}"

        mobile_qc_path = ARTIFACT_DIR / "qc_mobile_inspections.png"
        m_page.screenshot(path=str(mobile_qc_path), full_page=True)
        print(f"Captured: {mobile_qc_path.name}")

        # Open inspection drawer on mobile
        m_page.click('.btn-open-drawer[data-id="ALC-PENDING-01"]')
        m_page.wait_for_selector("#inspectionDrawerBackdrop.active")
        time.sleep(1.0)

        mobile_sheet_path = ARTIFACT_DIR / "qc_mobile_sheet.png"
        m_page.screenshot(path=str(mobile_sheet_path), full_page=True)
        print(f"Captured: {mobile_sheet_path.name}")

        assert len(console_errors) == 0, f"Console errors on QC Mobile: {console_errors}"
        m_context.close()
        browser.close()

    print("\n[SUCCESS] Phase 6 QC Lead Playwright verification completed with 0 errors!")


if __name__ == "__main__":
    try:
        run_gate()
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)
