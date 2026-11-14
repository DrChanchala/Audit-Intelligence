# SiteIQ Production Deployment Checklist (Phase 4)

This checklist guides the secure release of the refactored modular backend and multi-tenant security hardening.

---

## 1. Environment Variables Configuration (Railway & Hosting)

Ensure the following variables are configured in the Railway dashboard (or production environment):

| Variable | Recommended / Required Value | Purpose |
|---|---|---|
| `APP_ENV` | `production` | Enables production security guards (rejects default secrets & wildcard CORS). |
| `SITEIQ_JWT_SECRET` | Random string of ≥ 48 URL-safe chars | Secret for signing HS256 JWT tokens. Must be rotated from the legacy default! |
| `DATABASE_URL` | `postgresql://...` (Supabase connection string) | Production PostgreSQL connection string with connection pooling. |
| `UPLOAD_DIR` | `/data/uploads` | Local upload directory if using Railway persistent volume. |
| `SUPABASE_URL` | `https://<ref>.supabase.co` | Supabase project URL (if using Supabase storage). |
| `SUPABASE_SERVICE_ROLE_KEY` | `ey...` (Supabase Service Role Key) | Backend-only service key for Supabase private bucket storage. |
| `SUPABASE_STORAGE_BUCKET` | `inspection-evidence` | Name of private storage bucket. Must be set to **Private** in Supabase! |
| `ALLOW_PUBLIC_ORG_SIGNUP` | `true` (or `false` for invite-only) | Controls self-service organization admin onboarding. |
| `GEMINI_API_KEY` | API Key string | Google Gemini API key for AI audit dossier generation. |
| `GEMINI_MODELS` | `gemini-1.5-flash,gemini-1.5-pro` | Model priority fallback list for report generation. |
| `PORT` | Set automatically by Railway (`8000`) | Listening port for FastAPI uvicorn server. |

> To generate a secure `SITEIQ_JWT_SECRET`:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

---

## 2. Supabase Database Backup

Prior to executing any migrations:
1. Navigate to **Supabase Dashboard → Database → Backups**.
2. Trigger an immediate manual backup snapshot.
3. Alternatively, export via `pg_dump`:
   ```bash
   pg_dump -d "$DATABASE_URL" -F c -b -v -f "siteiq_backup_pre_phase4_$(date +%Y%m%d%H%M%S).dump"
   ```

---

## 3. Migration 003 Execution & Dry-Run Validation

File: `migrations/003_tenancy_indexes.sql`

### Step 3.1: Dry-Run Assessment Query
Run the following SQL in Supabase SQL Editor to count the number of allocations requiring backfill:
```sql
SELECT
    COUNT(*) AS total_allocations,
    COUNT(CASE WHEN a.engineer_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.engineer_id) THEN 1 END) AS rows_needing_backfill,
    COUNT(CASE WHEN a.engineer_id IS NULL THEN 1 END) AS rows_with_null_engineer
FROM inspection_allocations a;
```

### Step 3.2: Inspect Specific Rows
```sql
SELECT
    a.allocation_id,
    a.project_id,
    p.org_id,
    a.engineer_id,
    a.engineer_name,
    u.id AS matched_user_id
FROM inspection_allocations a
JOIN projects p ON a.project_id = p.id
LEFT JOIN users u ON u.org_id = p.org_id AND u.role = 'engineer'
    AND (a.engineer_id = u.employee_id OR LOWER(a.engineer_name) = LOWER(u.full_name))
WHERE a.engineer_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM users u2 WHERE u2.id = a.engineer_id);
```

### Step 3.3: Apply Migration 003
Execute `migrations/003_tenancy_indexes.sql` in the Supabase SQL editor.
Verify that:
1. `idx_users_org_role` and `idx_allocations_engineer` indexes exist.
2. Permissive `"Allow all access"` RLS policies on tables have been dropped.

---

## 4. Railway Preview Environment Smoke Tests

Once the preview environment deploys with the PR branch:

- [ ] **Admin Sign-In & KPIs:**
  - Log in as an Organization Admin.
  - Verify `/api/admin/overview` returns project and user KPIs for the admin's organization only.
- [ ] **QC Lead Workflow:**
  - Log in as QC Lead.
  - View allocations list (`/api/allocations`).
  - Create an inspection allocation (`POST /api/allocations`).
  - Attempt to allocate to an engineer belonging to a foreign organization: verify it returns **404**.
- [ ] **Cross-Tenant Isolation (404 Verification):**
  - Use Org B credentials to request `/api/projects/<org-a-project-id>` or `/api/allocations/<org-a-alloc-id>`.
  - Assert response is **HTTP 404 Not Found** (not 403, preventing resource enumeration).
- [ ] **Evidence Upload & Retrieval:**
  - Log in as assigned Engineer.
  - Upload valid JPEG evidence photo: verify upload succeeds.
  - Upload an `.html` file: verify upload is rejected with **400** (magic-byte validation).
  - Access photo URL without authentication: verify request returns **401**.
- [ ] **QC Review & Approval:**
  - Engineer submits completed allocation (`POST /api/allocations/{id}/submit`).
  - QC Lead approves inspection (`POST /api/allocations/{id}/review` with `decision: "approve"`).
  - Verify inspection status transitions to `Report issued` and approval record is marked `Approved`.
- [ ] **Security Endpoints Gone:**
  - `POST /api/auth/register` returns **410 Gone**.
  - `POST /api/seed` returns **410 Gone**.
  - `POST /api/auth/organizations` returns **410 Gone**.

---

## 5. Post-Deploy Hardening & Audit

1. **Token Invalidation:** Secret rotation (`SITEIQ_JWT_SECRET`) immediately invalidates all legacy sessions.
2. **Account Audit:** Audit `users` table for rogue accounts created through the legacy public registration:
   ```sql
   SELECT id, email, role, org_id, created_at
   FROM users
   WHERE role = 'admin'
   ORDER BY created_at DESC;
   ```
   Disable any unrecognized admin account:
   ```sql
   UPDATE users SET status = 'disabled' WHERE id = '<suspicious_user_id>';
   ```
3. **Storage Security Check:** Verify `inspection-evidence` bucket is marked **Private** in Supabase Storage settings.

---

## 6. Rollback Plan

If critical defects or regressions are discovered in the preview environment:

1. **Application Rollback:**
   - In Railway dashboard, click **Deployments** → locate previous stable deployment commit → click **Redeploy**.
   - If rolling back via Git: revert the PR merge commit on `main`.
2. **Database Rollback:**
   - If Migration 003 caused issues, restore the snapshot backup taken in Step 2 from Supabase Dashboard.
   - If only RLS policies need temporary restoration while troubleshooting backend service connections:
     ```sql
     CREATE POLICY "Allow all access" ON organizations FOR ALL USING (true) WITH CHECK (true);
     CREATE POLICY "Allow all access" ON users FOR ALL USING (true) WITH CHECK (true);
     ```
3. **Session Secret:**
   - If needed, restore the previous `SITEIQ_JWT_SECRET` in Railway environment variables to allow older active sessions to resume.
