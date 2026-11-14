-- ============================================================================
-- Migration 003: Tenancy Indexes, Foreign Key Scoping & RLS Hardening (PostgreSQL)
-- ============================================================================

-- 1. Ensure column typing for inspection_allocations.engineer_id
ALTER TABLE inspection_allocations
    ALTER COLUMN engineer_id TYPE VARCHAR(64);

-- 2. Performance & Tenancy Indexes
CREATE INDEX IF NOT EXISTS idx_users_org_role ON users(org_id, role);
CREATE INDEX IF NOT EXISTS idx_allocations_engineer ON inspection_allocations(engineer_id);
CREATE INDEX IF NOT EXISTS idx_allocations_org_status ON inspection_allocations(project_id, status);

-- 3. Backfill engineer_id where it holds an EMP- employee_id or display name
-- Dry-run check:
-- SELECT COUNT(*) AS rows_needing_backfill
-- FROM inspection_allocations a
-- JOIN projects p ON a.project_id = p.id
-- WHERE a.engineer_id IS NOT NULL
--   AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = a.engineer_id);

UPDATE inspection_allocations a
SET engineer_id = u.id
FROM projects p, users u
WHERE a.project_id = p.id
  AND u.org_id = p.org_id
  AND u.role = 'engineer'
  AND (a.engineer_id = u.employee_id OR LOWER(a.engineer_name) = LOWER(u.full_name))
  AND (a.engineer_id IS NULL OR NOT EXISTS (SELECT 1 FROM users u2 WHERE u2.id = a.engineer_id));

-- 4. Drop permissive "Allow all access" RLS policies
-- Backend connections use the service role / direct database connection, so permissive
-- policies allowing anon or authenticated Supabase REST client access are removed.
DO $$
BEGIN
    DROP POLICY IF EXISTS "Allow all access" ON organizations;
    DROP POLICY IF EXISTS "Allow all access" ON users;
    DROP POLICY IF EXISTS "Allow all access" ON projects;
    DROP POLICY IF EXISTS "Allow all access" ON inspection_allocations;
    DROP POLICY IF EXISTS "Allow all access" ON allocation_checkpoints;
    DROP POLICY IF EXISTS "Allow all access" ON non_conformities;
    DROP POLICY IF EXISTS "Allow all access" ON approvals;
END $$;
