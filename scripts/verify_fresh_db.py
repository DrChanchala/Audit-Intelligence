"""Quick verification script for Phase 1 gate: fresh SQLite DB initialization and master checklist load."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.connection import Session
from app.db.schema import init_schema, load_master_checklist


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "fresh_test.db"
        conn = sqlite3.connect(db_path)
        s = Session(conn, "sqlite")

        print(f"1. Initializing schema on fresh database at {db_path}...")
        init_schema(s)
        print("   Schema initialized successfully.")

        print("2. Loading master checklist from app/data/master_checklist_parsed.json...")
        count = load_master_checklist(s)
        print(f"   Loaded {count} checkpoints.")

        stages = s.scalar("SELECT COUNT(*) FROM master_stages")
        subgroups = s.scalar("SELECT COUNT(*) FROM master_subgroups")
        checkpoints = s.scalar("SELECT COUNT(*) FROM master_checkpoints")

        conn.close()

        print(f"3. Verifying counts: {stages} stages / {subgroups} subgroups / {checkpoints} checkpoints")
        assert stages == 20, f"Expected 20 stages, got {stages}"
        assert subgroups == 98, f"Expected 98 subgroups, got {subgroups}"
        assert checkpoints == 859, f"Expected 859 checkpoints, got {checkpoints}"
        print(" GATE VERIFICATION PASSED: exactly 20 stages / 98 subgroups / 859 checkpoints!")


if __name__ == "__main__":
    main()
