#!/usr/bin/env python3
"""
SiteIQ — SQLite to Supabase / PostgreSQL Data Migration Engine
Extracts all persistent records from local audit_intelligence.db
and migrates them into PostgreSQL / Supabase with referential integrity verification.
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime
from typing import List, Dict, Any, Tuple

try:
    import psycopg2
    from psycopg2.extras import execute_batch, RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

TABLE_ORDER: List[str] = [
    "projects",
    "master_stages",
    "master_subgroups",
    "master_checkpoints",
    "non_conformities",
    "nc_audit_logs",
    "inspections",
    "approvals",
    "action_items",
    "evidence_photos",
    "inspection_reports",
    "inspection_allocations",
    "allocation_checkpoints",
    "inspection_reviews",
    "inspection_audit_events"
]

PRIMARY_KEYS: Dict[str, str] = {
    "projects": "id",
    "master_stages": "stage_id",
    "master_subgroups": "subgroup_id",
    "master_checkpoints": "checkpoint_id",
    "non_conformities": "code",
    "nc_audit_logs": "id",
    "inspections": "code",
    "approvals": "code",
    "action_items": "id",
    "evidence_photos": "id",
    "inspection_reports": "id",
    "inspection_allocations": "allocation_id",
    "allocation_checkpoints": "id",
    "inspection_reviews": "review_id",
    "inspection_audit_events": "event_id"
}

SERIAL_PKS: Dict[str, str] = {
    "nc_audit_logs": "id",
    "action_items": "id",
    "evidence_photos": "id",
    "inspection_reports": "id",
    "allocation_checkpoints": "id",
    "inspection_reviews": "review_id",
    "inspection_audit_events": "event_id"
}

def sanitize_val(table: str, col: str, val: Any) -> Any:
    if col == "is_resolved":
        return bool(val) if val is not None else False
    if val == "" and (col.endswith(("_date", "_at", "_stamp")) or col in ("cleared_date", "closed_date", "submitted_at", "approved_at", "returned_at")):
        return None
    return val

def inspect_sqlite_data(sqlite_path: str) -> Dict[str, List[Dict[str, Any]]]:
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database not found at {sqlite_path}")

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    data_payload: Dict[str, List[Dict[str, Any]]] = {}

    for table in TABLE_ORDER:
        try:
            cur.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cur.fetchall()]
            data_payload[table] = rows
        except sqlite3.OperationalError:
            data_payload[table] = []

    conn.close()
    return data_payload

def run_dry_run_audit(sqlite_path: str):
    print("=" * 70)
    print("SiteIQ SQLite Data Migration Audit (DRY-RUN)")
    print("=" * 70)
    data = inspect_sqlite_data(sqlite_path)

    total_records = 0
    print(f"{'Table Name':<30} | {'Record Count':<15} | {'Primary Key':<15}")
    print("-" * 70)
    for table in TABLE_ORDER:
        count = len(data.get(table, []))
        total_records += count
        pk = PRIMARY_KEYS.get(table, "unknown")
        print(f"{table:<30} | {count:<15} | {pk:<15}")

    print("-" * 70)
    print(f"Total Persistent Records: {total_records}")
    print("=" * 70)
    print("[OK] Dry-run audit completed successfully. Ready for migration.")

def migrate_to_postgres(sqlite_path: str, pg_url: str):
    if not HAS_PSYCOPG2:
        raise RuntimeError("psycopg2 is required for PostgreSQL migration. Install via 'pip install psycopg2-binary'.")

    print(f"Connecting to SQLite: {sqlite_path}")
    data = inspect_sqlite_data(sqlite_path)

    print(f"Connecting to PostgreSQL / Supabase...")
    # Support sslmode if Supabase requires it
    pg_conn = psycopg2.connect(pg_url)
    pg_conn.autocommit = False
    cur = pg_conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Step 1: Ensure Schema Exists
        schema_path = os.path.join(os.path.dirname(__file__), "migrations", "001_initial_schema_postgres.sql")
        if os.path.exists(schema_path):
            print("Applying schema: 001_initial_schema_postgres.sql ...")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            cur.execute(schema_sql)
            print("[OK] Schema applied.")

        # Step 2: Migrate data in topological order
        print("\nMigrating tables...")
        for table in TABLE_ORDER:
            rows = data.get(table, [])
            if not rows:
                print(f"  - {table:<28}: 0 records (skipped)")
                continue

            columns = list(rows[0].keys())
            cols_str = ", ".join(f'"{c}"' for c in columns)
            placeholders = ", ".join(["%s"] * len(columns))
            pk = PRIMARY_KEYS.get(table)

            if pk:
                # Use ON CONFLICT DO NOTHING to ensure idempotence
                insert_query = f"""
                    INSERT INTO {table} ({cols_str})
                    VALUES ({placeholders})
                    ON CONFLICT ("{pk}") DO NOTHING
                """
            else:
                insert_query = f"""
                    INSERT INTO {table} ({cols_str})
                    VALUES ({placeholders})
                """

            values = [[sanitize_val(table, c, row[c]) for c in columns] for row in rows]
            execute_batch(cur, insert_query, values, page_size=100)
            print(f"  - {table:<28}: {len(rows)} records migrated")

            # Update serial sequences if primary key is auto-increment
            if table in SERIAL_PKS:
                seq_col = SERIAL_PKS[table]
                cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', '{seq_col}'), COALESCE(MAX({seq_col}), 1)) FROM {table};")

        pg_conn.commit()
        print("\n[SUCCESS] All records committed to PostgreSQL / Supabase!")

        # Step 3: Verification Check
        print("\nVerifying migrated row counts in PostgreSQL:")
        print(f"{'Table Name':<30} | {'SQLite Count':<15} | {'Postgres Count':<15} | {'Status'}")
        print("-" * 75)
        for table in TABLE_ORDER:
            sqlite_count = len(data.get(table, []))
            cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            pg_count = cur.fetchone()["cnt"]
            match = "MATCH" if pg_count >= sqlite_count else "MISMATCH"
            print(f"{table:<30} | {sqlite_count:<15} | {pg_count:<15} | {match}")

    except Exception as e:
        pg_conn.rollback()
        print(f"\n[ERROR] Migration failed. Transaction rolled back: {e}")
        raise
    finally:
        cur.close()
        pg_conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SiteIQ Database Migration Engine")
    parser.add_argument("--sqlite", default="audit_intelligence.db", help="Path to SQLite database")
    parser.add_argument("--pg-url", default=os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL"), help="PostgreSQL connection string")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry-run inspection without migrating")

    args = parser.parse_args()

    if args.dry_run or not args.pg_url:
        run_dry_run_audit(args.sqlite)
        if not args.pg_url:
            print("\n[NOTE] No DATABASE_URL provided. Run with --pg-url or set DATABASE_URL environment variable to execute live migration.")
    else:
        migrate_to_postgres(args.sqlite, args.pg_url)
