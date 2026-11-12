# SiteIQ — Rollback & Disaster Recovery Procedures

## 1. Application Deployment Rollback (Railway)

If a newly deployed build introduces an unexpected bug or fails health checks:

1. **Instant Rollback via Railway Dashboard:**
   - Go to your SiteIQ service in the Railway project dashboard.
   - Click the **Deployments** tab.
   - Locate the previous successful deployment.
   - Click **...** (Options) $\rightarrow$ **Rollback to this deployment**.
   - Railway will immediately route traffic back to the previous stable container image within seconds.
2. **Git Rollback:**
   ```bash
   git revert HEAD
   git push origin main
   ```
   Railway's CI/CD trigger will automatically detect the revert commit and redeploy the previous code.

---

## 2. Database Recovery & Rollback (Supabase)

### 2.1 Point-in-Time Recovery (PITR)
- Supabase provides automated daily backups and continuous WAL (Write-Ahead Log) archiving.
- If data corruption occurs, navigate to **Database** $\rightarrow$ **Backups** in Supabase and select **Restore** to a specified timestamp before the incident.

### 2.2 Reverting Schema Migrations
- Schema migration scripts are strictly version-controlled in the `migrations/` directory.
- DDL modifications should only be performed forward using additive migrations (`ALTER TABLE ... ADD COLUMN ...`).
- If an emergency rollback of a table or constraint is required, execute a targeted rollback migration script using `DIRECT_URL`.

---

## 3. Storage Rollback
- Objects stored in the `inspection-evidence` Supabase Storage bucket are versioned.
- Accidental deletions can be recovered via the Supabase dashboard or restored from local backup artifacts.
