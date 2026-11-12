# SiteIQ — Construction Quality Assurance & Audit Intelligence Platform

[![CI Verification](https://github.com/siteiq-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/siteiq-platform/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org/)
[![Database](https://img.shields.io/badge/Database-Supabase%20%7C%20PostgreSQL-3ECF8E?logo=supabase)](https://supabase.com/)
[![Hosting](https://img.shields.io/badge/Hosting-Railway-0B0D0E?logo=railway)](https://railway.app/)
[![AI Engine](https://img.shields.io/badge/AI-Google%20Gemini%202.0-4285F4?logo=google)](https://deepmind.google/technologies/gemini/)

SiteIQ is an enterprise construction quality assurance, field inspection management, and AI-powered audit intelligence platform engineered for real estate developers, EPC contractors, and third-party inspection agencies. It provides end-to-end ISO 9001:2015 & NBC 2016-compliant site governance.

---

## 🏗️ Architectural Overview

```
                                 ┌──────────────────────────────────────────────────────────┐
                                 │                   Client Layer (Web / Mobile)           │
                                 │  - QC Lead Governance Cockpit                            │
                                 │  - Field Inspection Engineer Workspace                  │
                                 │  - Role Login Gateway & Session Manager                  │
                                 └────────────────────────────┬─────────────────────────────┘
                                                              │ HTTPS / JSON API
                                                              ▼
                                 ┌──────────────────────────────────────────────────────────┐
                                 │                  FastAPI Backend Gateway                 │
                                 │  - 4-Step Master Inspection Allocation Engine            │
                                 │  - Defect & Non-Conformity (NC) Classification Service   │
                                 │  - Dynamic Role-Based Access Routing                     │
                                 │  - Static Asset Delivery & Evidence Processor            │
                                 └──────────────┬───────────────────────────┬───────────────┘
                                                │                           │
                   ┌────────────────────────────▼─────┐       ┌─────────────▼────────────────┐
                   │    Database & Storage Layer      │       │     AI Intelligence Layer    │
                   │  - Supabase PostgreSQL (Prod)    │       │  - Google Gemini 2.0 Flash   │
                   │  - Local SQLite (Dev / Offline)  │       │  - Audit Report Synthesis    │
                   │  - Supabase Storage Bucket       │       │  - Defect Severity Scorer    │
                   │  - Row Level Security (RLS)      │       │  - Regulatory Compliance     │
                   └──────────────────────────────────┘       └──────────────────────────────┘
```

---

## 🌟 Key Capabilities

1. **Role Login Gateway & Strict Platform Separation:**
   - **QC Lead Portal:** Complete project quality register, 4-step inspection creation & allocation wizard, engineer reassignment (`👤 Change Inspection Engineer`), approval queues, and AI executive dossier generation.
   - **Field Inspection Engineer Workspace:** Mobile-optimized checklist runner, 1-tap rapid checkpoint verification (`[✓ OK] [⚠ NC] [— NA]`), structured Non-Conformity logging (Defect Severity, Responsible Trade, Target Rectification Date), evidence camera capture, and strict hold-point submission gating.
2. **Master Quality Checklist Engine:**
   - 20 Stages, 98 Subgroups, and 859 Standard Checkpoints spanning Substructure, RCC Structure, Masonry, Finishing, MEP, Waterproofing, and Façade.
3. **AI Inspection Report Dossiers:**
   - Google Gemini multimodal LLM automatically analyzes checkpoint results, photographic evidence, and contractor observations to synthesize audit reports.
4. **Hybrid Database Architecture:**
   - Seamless zero-configuration fallback to SQLite (`audit_intelligence.db`) for local testing.
   - High-throughput transactional PostgreSQL for Supabase and Railway production environments.

---

## 🚀 Quickstart & Local Development

### Prerequisites
- Python 3.12+
- Git

### Installation

```bash
# 1. Clone repository
git clone https://github.com/siteiq-platform.git
cd siteiq-platform

# 2. Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Fill in GEMINI_API_KEY in .env

# 5. Start application
python app_audit.py
```

The application will be accessible at:
- **Role Gateway:** `http://localhost:8000/login`
- **QC Lead Cockpit:** `http://localhost:8000/qc-lead`
- **Field Engineer Workspace:** `http://localhost:8000/engineer`
- **Swagger API Docs:** `http://localhost:8000/docs`
- **Health Check:** `http://localhost:8000/api/health`

---

## 🗄️ Database Migration (SQLite to Supabase PostgreSQL)

SiteIQ includes an idempotent, transactional migration engine:

```bash
# 1. Inspect existing SQLite data (Dry-Run mode)
python migrate_sqlite_to_postgres.py --dry-run

# 2. Execute migration into Supabase / PostgreSQL
python migrate_sqlite_to_postgres.py --pg-url "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres?sslmode=require"
```

The migration engine safely applies `migrations/001_initial_schema_postgres.sql`, imports all 1,150+ records across 15 tables in foreign-key topological order, enables Supabase Row Level Security (RLS), and executes validation row-count checks.

---

## 🚢 Production Deployment to Railway

### 1. Link GitHub Repository
1. Log in to [Railway.app](https://railway.app).
2. Create **New Project** $\rightarrow$ **Deploy from GitHub repo** $\rightarrow$ select `siteiq-platform`.

### 2. Configure Environment Variables
Set the following variables in the Railway dashboard:

| Variable | Description | Example / Default |
|---|---|---|
| `PORT` | Auto-provided by Railway | `8000` |
| `DATABASE_URL` | Supabase Transactional Pooler URL | `postgresql://postgres:[PWD]@db.[REF].supabase.co:5432/postgres?sslmode=require` |
| `DIRECT_URL` | Supabase Direct Connection URL | `postgresql://postgres:[PWD]@db.[REF].supabase.co:5432/postgres?sslmode=require` |
| `SUPABASE_URL` | Supabase Project API URL | `https://[REF].supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase Public Anonymous Key | `eyJhbGciOi...` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Server-side Secret Key | `eyJhbGciOi...` |
| `SUPABASE_STORAGE_BUCKET` | Evidence Storage Bucket | `inspection-evidence` |
| `GEMINI_API_KEY` | Google Gemini API Key | `AIzaSy...` |
| `ENVIRONMENT` | Runtime mode | `production` |

### 3. Deploy
Railway will automatically detect `railway.toml` and `Dockerfile`, build the container, perform health checks on `/api/health`, and provision the production HTTPS domain.

---

## 🔒 Security & Data Integrity

- **Row Level Security (RLS):** Enforced across all 15 PostgreSQL tables in Supabase.
- **Service Isolation:** Backend credentials (`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`) are kept strictly server-side and never exposed to the frontend.
- **Hold-Point Gating:** Inspection engineers cannot mark an inspection as submitted while any checkpoint remains unevaluated (`Pending`).
- **Audit Logging:** Every state transition, engineer assignment, and review action is immutably logged to `inspection_audit_events`.

---

## 📄 License
Enterprise Proprietary — SiteIQ CQMS Platform & Purvanchal Projects.
