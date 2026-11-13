-- ============================================================================
-- SiteIQ CQMS — Enterprise Multi-Tenant & Authentication Migration (PostgreSQL)
-- Adds: organizations, users, user_sessions, and org_id partitioning
-- ============================================================================

-- 1. Create organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(32) NOT NULL UNIQUE,
    domain VARCHAR(128),
    industry VARCHAR(128) DEFAULT 'Construction & Real Estate',
    address TEXT,
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL, -- 'admin', 'qc_lead', 'engineer'
    employee_id VARCHAR(64),
    specialization VARCHAR(128),
    avatar_initials VARCHAR(8),
    phone VARCHAR(32),
    status VARCHAR(32) DEFAULT 'active',
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 3. Add org_id to projects table for Multi-Tenant Isolation
ALTER TABLE projects ADD COLUMN IF NOT EXISTS org_id VARCHAR(64) REFERENCES organizations(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_projects_org ON projects(org_id);

-- 4. Enable RLS on organizations and users
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "Allow all access" ON organizations;
    CREATE POLICY "Allow all access" ON organizations FOR ALL USING (true) WITH CHECK (true);

    DROP POLICY IF EXISTS "Allow all access" ON users;
    CREATE POLICY "Allow all access" ON users FOR ALL USING (true) WITH CHECK (true);
END $$;
