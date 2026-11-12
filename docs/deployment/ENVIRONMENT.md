# SiteIQ — Environment Configuration Specification

This document details all environment variables supported by the SiteIQ platform.

---

## 1. Variable Reference

| Variable Name | Required | Default | Target Service | Description |
|---|---|---|---|---|
| `PORT` | Yes (in Cloud) | `8000` | Railway / Docker | Network port on which the Uvicorn ASGI server listens. Automatically supplied by Railway. |
| `ENVIRONMENT` | No | `production` | Backend API | Runtime operational profile (`development`, `staging`, `production`). |
| `DATABASE_URL` | Recommended | None (SQLite fallback) | Backend API | PostgreSQL connection string with connection pooling (e.g., Supabase PgBouncer port 6543 or 5432). |
| `DIRECT_URL` | Recommended | None | Migration Engine | Direct PostgreSQL connection string bypassing connection poolers (required for DDL migrations). |
| `SUPABASE_URL` | Recommended | None | Storage & Auth | Public REST / Storage endpoint for Supabase project (`https://[PROJECT-REF].supabase.co`). |
| `SUPABASE_ANON_KEY` | Recommended | None | Frontend / Client | Public anonymous key used for client-side queries where applicable. |
| `SUPABASE_SERVICE_ROLE_KEY` | Recommended | None | Backend API | Elevated service-role key for backend operations and evidence photo uploads. **Never expose to client.** |
| `SUPABASE_STORAGE_BUCKET` | No | `inspection-evidence` | Storage Service | Supabase Storage bucket name used for storing checkpoint photographic evidence. |
| `GEMINI_API_KEY` | Yes (for AI) | None | AI Agent Service | Google Gemini API key used for generating AI Inspection Reports and executive audit dossiers. |
| `LOG_LEVEL` | No | `info` | Backend API | Logging verbosity (`debug`, `info`, `warning`, `error`). |
| `FRONTEND_URL` | No | `*` | CORS Middleware | Authorized frontend origin domain. |
| `BACKEND_URL` | No | `*` | Backend API | Fully-qualified public domain of the backend service. |

---

## 2. Secrets Management Guidelines

1. **Local Development:** Store secrets in `.env` in the root workspace. `.env` is permanently excluded from Git version control via `.gitignore`.
2. **Production on Railway:** Input secrets directly into the Railway Project Dashboard under the **Variables** tab. Do not commit `.env` or plaintext credentials to GitHub.
3. **Supabase Secrets:** Store API keys and database credentials securely within Supabase Vault or Railway Environment Variables.
