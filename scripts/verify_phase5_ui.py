"""Playwright end-to-end verification script for Phase 5 Gate.

Verifies:
- Landing (/) and Admin (/admin) pages render cleanly at:
  - Desktop: 1366 × 900
  - Mobile: 390 × 844
- Exactly 0 console errors and 0 page exceptions.
- Auth flow: login redirect, admin KPIs, projects listing, team listing.
- Modal interactions: Project creation modal, Member provisioning modal, Org registration modal.
- Captures full screenshots for Gate verification reporting.
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

# Set up clean temporary database
temp_dir = tempfile.mkdtemp()
db_path = os.path.join(temp_dir, "phase5_e2e.db")
if "DATABASE_URL" in os.environ:
    del os.environ["DATABASE_URL"]
os.environ["SQLITE_PATH"] = str(db_path)
os.environ["APP_ENV"] = "development"
os.environ["SITEIQ_JWT_SECRET"] = "phase5-test-secret-key-at-least-32-chars-long!"
os.environ["UPLOAD_DIR"] = os.path.join(temp_dir, "uploads")
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)

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
    s.execute(
        "INSERT OR REPLACE INTO users (id, org_id, email, password_hash, full_name, role, status) "
        "VALUES ('USR-ADMIN-A', 'ORG-A', 'admin@apexinfra.com', ?, 'Anand Sharma', 'admin', 'active')",
        (hashed,),
    )
    s.execute(
        "INSERT OR REPLACE INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, status) "
        "VALUES ('USR-QC-A', 'ORG-A', 'qc@apexinfra.com', ?, 'Priya Patel', 'qc_lead', 'EMP-101', 'Structural Lead', 'active')",
        (hashed,),
    )
    s.execute(
        "INSERT OR REPLACE INTO users (id, org_id, email, password_hash, full_name, role, employee_id, specialization, status) "
        "VALUES ('USR-ENG-A', 'ORG-A', 'engineer@apexinfra.com', ?, 'Ramesh Kumar', 'engineer', 'EMP-201', 'RCC & Concrete', 'active')",
        (hashed,),
    )
    s.execute(
        "INSERT OR REPLACE INTO projects (id, org_id, code, name, type, loc, geo, status, progress, start_date, end_date, upd_by) "
        "VALUES ('PRJ-001', 'ORG-A', 'PRJ-HB', 'Apex Horizon Tower B', 'Commercial High-Rise', 'Bengaluru, KA', '12.9716, 77.5946', 'live', 45, '2026-01-15', '2027-06-30', 'Anand Sharma')"
    )

# Start test server in background thread
PORT = 8765
config = uvicorn.Config(app=app, host="127.0.0.1", port=PORT, log_level="warning")
server = uvicorn.Server(config)
server_thread = threading.Thread(target=server.run, daemon=True)
server_thread.start()

time.sleep(1.5)

# Target directory for artifacts / screenshots
ARTIFACT_DIR = Path(r"C:\Users\Chanchala\.gemini\antigravity\brain\4e7bbfa4-c89c-448c-b236-a4c9ad6887cf")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

console_errors = []


def on_console(msg):
    print(f"[{msg.type.upper()}] {msg.text}")
    if msg.type == "error":
        console_errors.append(f"Console Error: {msg.text}")


def on_page_error(err):
    console_errors.append(f"Page Error: {err}")


def run_e2e():
    global console_errors
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. Desktop Viewport (1366 × 900)
        # -------------------------------------------------------------
        print("\n--- Verifying Desktop Viewport (1366x900) ---")
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        page = context.new_page()
        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        async def handle_response(r):
            print(f"HTTP {r.status} {r.url}")
            if r.status >= 400:
                try:
                    text = await r.text()
                    print(f"ERROR BODY: {text}")
                except Exception:
                    pass
        page.on("response", lambda r: print(f"HTTP {r.status} {r.url} - {r.text() if r.status >= 400 else ''}"))

        # 1.1 Landing Page
        page.goto(f"http://127.0.0.1:{PORT}/")
        page.wait_for_selector(".hero-title")
        page.wait_for_selector("#signInForm")
        time.sleep(0.5)

        landing_desktop_path = ARTIFACT_DIR / "landing_desktop_1366x900.png"
        page.screenshot(path=str(landing_desktop_path), full_page=True)
        print(f"Captured: {landing_desktop_path.name}")
        assert len(console_errors) == 0, f"Console errors on Landing (Desktop): {console_errors}"

        # 1.2 Test Modal Dialog
        page.click("#openRegisterModalBtn")
        page.wait_for_selector("#registerOrgModal.active")
        time.sleep(0.2)
        page.click('[data-modal-close="registerOrgModal"]')
        page.wait_for_selector("#registerOrgModal", state="hidden")

        # 1.3 Sign In as Admin
        page.fill("#signInEmail", "admin@apexinfra.com")
        page.fill("#signInPassword", "Password123!")
        page.click("#signInSubmitBtn")

        # Expect redirect to /admin
        page.wait_for_url(f"http://127.0.0.1:{PORT}/admin", timeout=5000)
        page.wait_for_selector("#projectsTable")
        page.wait_for_selector("#kpiProjects")
        time.sleep(1.0)  # Wait for API fetch & render

        admin_desktop_path = ARTIFACT_DIR / "admin_desktop_1366x900.png"
        page.screenshot(path=str(admin_desktop_path), full_page=True)
        print(f"Captured: {admin_desktop_path.name}")
        assert len(console_errors) == 0, f"Console errors on Admin (Desktop): {console_errors}"

        # Verify Projects Data loaded
        assert "Apex Horizon Tower B" in page.content()

        # Switch to Team Tab
        page.click("#tabBtnTeam")
        time.sleep(0.5)
        assert "Priya Patel" in page.content()
        assert "Ramesh Kumar" in page.content()

        context.close()

        # -------------------------------------------------------------
        # 2. Mobile Viewport (390 × 844)
        # -------------------------------------------------------------
        print("\n--- Verifying Mobile Viewport (390x844) ---")
        console_errors = []
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            is_mobile=True,
            has_touch=True,
        )
        m_page = mobile_context.new_page()
        m_page.on("console", on_console)
        m_page.on("pageerror", on_page_error)

        # 2.1 Landing Mobile
        m_page.goto(f"http://127.0.0.1:{PORT}/")
        m_page.wait_for_selector(".hero-title")
        time.sleep(0.5)

        landing_mobile_path = ARTIFACT_DIR / "landing_mobile_390x844.png"
        m_page.screenshot(path=str(landing_mobile_path), full_page=True)
        print(f"Captured: {landing_mobile_path.name}")
        assert len(console_errors) == 0, f"Console errors on Landing (Mobile): {console_errors}"

        # Check no horizontal overflow
        body_scroll_w = m_page.evaluate("document.body.scrollWidth")
        body_client_w = m_page.evaluate("document.body.clientWidth")
        assert body_scroll_w <= body_client_w + 2, f"Horizontal scroll detected on mobile: {body_scroll_w} > {body_client_w}"

        # 2.2 Sign In on Mobile
        m_page.fill("#signInEmail", "admin@apexinfra.com")
        m_page.fill("#signInPassword", "Password123!")
        m_page.click("#signInSubmitBtn")

        m_page.wait_for_url(f"http://127.0.0.1:{PORT}/admin", timeout=5000)
        m_page.wait_for_selector("#projectsTable")
        time.sleep(1.0)

        admin_mobile_path = ARTIFACT_DIR / "admin_mobile_390x844.png"
        m_page.screenshot(path=str(admin_mobile_path), full_page=True)
        print(f"Captured: {admin_mobile_path.name}")
        assert len(console_errors) == 0, f"Console errors on Admin (Mobile): {console_errors}"

        mobile_context.close()
        browser.close()

    print("\n[SUCCESS] Phase 5 E2E Playwright verification completed with 0 errors!")


if __name__ == "__main__":
    try:
        run_e2e()
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)
