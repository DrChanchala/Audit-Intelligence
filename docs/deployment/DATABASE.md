# SiteIQ — Database Architecture & Migration Specification

## 1. Schema Overview

SiteIQ utilizes a normalized relational schema with 15 core entities designed to satisfy ISO 9001:2015 traceability and NBC 2016 compliance.

### Entity Catalog

| # | Entity Name | Primary Key | Description | Record Count |
|---|---|---|---|---|
| 1 | `projects` | `id` (VARCHAR 32) | Real estate and civil infrastructure projects | 10 |
| 2 | `master_stages` | `stage_id` (VARCHAR 16) | Standard construction stages (Substructure, RCC, MEP, etc.) | 20 |
| 3 | `master_subgroups` | `subgroup_id` (VARCHAR 32) | Trade groupings under each construction stage | 98 |
| 4 | `master_checkpoints` | `checkpoint_id` (VARCHAR 64) | Normalized QA/QC technical verification checkpoints | 859 |
| 5 | `non_conformities` | `code` (VARCHAR 32) | Logged non-conformance defects with severity ratings | 26 |
| 6 | `nc_audit_logs` | `id` (BIGSERIAL) | Immutable change tracking for non-conformity records | 1 |
| 7 | `inspections` | `code` (VARCHAR 32) | High-level inspection work orders and status aggregates | 37 |
| 8 | `approvals` | `code` (VARCHAR 32) | Sign-off queue for QC Lead approval gates | 7 |
| 9 | `action_items` | `id` (BIGSERIAL) | Corrective action tasks assigned to project teams | 13 |
| 10 | `evidence_photos` | `id` (BIGSERIAL) | High-resolution before/after photographic audit logs | 0 |
| 11 | `inspection_reports` | `id` (BIGSERIAL) | AI-generated executive dossiers and regulatory summaries | 4 |
| 12 | `inspection_allocations` | `allocation_id` (VARCHAR 32) | Granular inspection assignments dispatched to engineers | 17 |
| 13 | `allocation_checkpoints` | `id` (BIGSERIAL) | Snapshot execution state of checkpoints per allocation | 36 |
| 14 | `inspection_reviews` | `review_id` (BIGSERIAL) | Formal QC Lead approval decisions and return comments | 0 |
| 15 | `inspection_audit_events` | `event_id` (BIGSERIAL) | Complete lifecycle audit log of state transitions | 22 |

---

## 2. Foreign Key Topology & Dependency Order

```
projects
  ├── non_conformities
  │     ├── nc_audit_logs
  │     └── evidence_photos
  ├── inspections
  │     └── inspection_reports
  ├── approvals
  ├── action_items
  └── inspection_allocations
        ├── allocation_checkpoints
        ├── inspection_reviews
        └── inspection_audit_events

master_stages
  └── master_subgroups
        └── master_checkpoints
              └── allocation_checkpoints
```

---

## 3. Migration Procedure

### Safe Production Migration Command
```bash
python migrate_sqlite_to_postgres.py --sqlite audit_intelligence.db --pg-url "$DATABASE_URL"
```

### Safety Guarantees
1. **Idempotence:** Uses `ON CONFLICT (primary_key) DO NOTHING` to guarantee that rerunning the migration will never duplicate records or overwrite live data.
2. **Transaction Rollback:** All operations run within an explicit PostgreSQL transaction block (`BEGIN` ... `COMMIT`). If any constraint is violated, the transaction rolls back cleanly.
3. **Sequence Synchronization:** Automatically calls `setval(pg_get_serial_sequence(...))` to align auto-increment sequences with imported IDs.
