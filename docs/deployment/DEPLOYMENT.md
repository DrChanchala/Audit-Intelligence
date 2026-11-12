# SiteIQ — Production Deployment Guide (GitHub, Railway & Supabase)

This guide provides end-to-end instructions for deploying SiteIQ to GitHub, Railway, and Supabase.

---

## 1. Prerequisites

1. **GitHub Account:** Permissions to create or push to a private repository (`siteiq-platform`).
2. **Supabase Account:** An active Supabase organization and project.
3. **Railway Account:** An active Railway account with permissions to deploy GitHub-connected projects.
4. **Google AI Studio / Gemini API Key:** Access to Google Gemini 2.0 Flash API.

---

## 2. Supabase Setup

### 2.1 Create Supabase Project
1. Log in to [Supabase](https://supabase.com).
2. Click **New Project**, name it `siteiq-prod`, choose a database password and region (e.g., `ap-south-1` for India / South Asia).
3. Wait for the database to provision.

### 2.2 Retrieve Connection Settings
In your Supabase project dashboard:
- Navigate to **Project Settings** $\rightarrow$ **Database**:
  - **Connection string (URI) - Transaction mode (port 6543 or 5432):** Copy as `DATABASE_URL`.
  - **Connection string (URI) - Session / Direct mode (port 5432):** Copy as `DIRECT_URL`.
- Navigate to **Project Settings** $\rightarrow$ **API**:
  - **Project URL:** Copy as `SUPABASE_URL`.
  - **Project API Keys (`anon`, `public`):** Copy as `SUPABASE_ANON_KEY`.
  - **Project API Keys (`service_role`, `secret`):** Copy as `SUPABASE_SERVICE_ROLE_KEY`.

### 2.3 Configure Storage Bucket
1. Navigate to **Storage** $\rightarrow$ **New Bucket**.
2. Name the bucket: `inspection-evidence`.
3. Set bucket to **Public** (or configure signed URL policies).
4. Click **Save**.

### 2.4 Apply Database Schema and Initial Data
Run the repeatable migration engine from your local terminal:

```bash
# Set connection string in terminal
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?sslmode=require"

# Execute migration
python migrate_sqlite_to_postgres.py --pg-url "$DATABASE_URL"
```

The script will:
- Apply `migrations/001_initial_schema_postgres.sql`.
- Enable Row Level Security (RLS) on all 15 tables.
- Migrate all 1,150+ records from `audit_intelligence.db`.
- Print a verification audit table comparing source vs destination counts.

---

## 3. GitHub Repository Setup

### 3.1 Initialize and Commit
From the project root:

```bash
git init
git checkout -b main
git add .
git commit -m "feat(core): initial production release of SiteIQ CQMS platform"
```

*(Note: Verify that `.env`, `*.db`, and media files are excluded before pushing).*

### 3.2 Add Remote and Push
```bash
# Create private repository on GitHub named 'siteiq-platform'
git remote add origin https://github.com/[YOUR-ORG-OR-USER]/siteiq-platform.git
git push -u origin main
```

---

## 4. Railway Deployment

### 4.1 Create Railway Project
1. Log in to [Railway](https://railway.app).
2. Click **+ New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Select `siteiq-platform` and choose branch `main`.

### 4.2 Configure Environment Variables
In Railway project $\rightarrow$ **Variables**, add:

| Key | Value |
|---|---|
| `PORT` | `8000` (Railway automatically manages this) |
| `DATABASE_URL` | `postgresql://postgres:[PWD]@db.[REF].supabase.co:5432/postgres?sslmode=require` |
| `DIRECT_URL` | `postgresql://postgres:[PWD]@db.[REF].supabase.co:5432/postgres?sslmode=require` |
| `SUPABASE_URL` | `https://[REF].supabase.co` |
| `SUPABASE_ANON_KEY` | `eyJhbGciOi...` |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJhbGciOi...` |
| `SUPABASE_STORAGE_BUCKET` | `inspection-evidence` |
| `GEMINI_API_KEY` | `AIzaSy...` |
| `ENVIRONMENT` | `production` |

### 4.3 Trigger Deployment
Railway will automatically build the `Dockerfile`, run health checks on `/api/health`, and allocate an active public domain (e.g., `https://siteiq-platform.up.railway.app`).
