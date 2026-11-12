# SiteIQ — Verified Production Architecture Specification

## 1. Executive Summary

SiteIQ is engineered as a unified, high-performance Construction Quality Management System (CQMS). The platform delivers real-time quality assurance, field checkpoint execution, engineer allocation, and AI-driven audit report generation for enterprise civil construction projects.

## 2. Infrastructure Topology

```
+-----------------------------------------------------------------------------------+
|                                  INTERNET CLIENTS                                 |
|  - Desktop Browsers (QC Lead Console, Executive Quality Governance)               |
|  - Mobile Viewports / PWA (Site Inspection Engineers, Field Checkpoint Runner)    |
+------------------------------------------+----------------------------------------+
                                           | HTTPS / TLS 1.3
                                           v
+-----------------------------------------------------------------------------------+
|                           RAILWAY CLOUD EDGE RUNTIME                              |
|  - Ingress: Automatic SSL/TLS Termination, Global Anycast Routing                 |
|  - Container Engine: Multi-stage Debian-slim container running Python 3.12        |
|  - Process: Uvicorn ASGI Server serving FastAPI + Async Static Middleware         |
|  - Port: Dynamic $PORT routing with /api/health automated watchdog                |
+---------------------+---------------------------------------+---------------------+
                      |                                       |
                      v                                       v
+------------------------------------+  +-------------------------------------------+
|      SUPABASE MANAGED CLOUD        |  |          GOOGLE GEMINI AI ENGINE          |
|  1. PostgreSQL 15 Relational DB    |  |  - Model: Gemini 2.0 Flash                |
|     - Connection Pooler (PgBouncer)|  |  - Capabilities: Multimodal defect triage,|
|     - Direct URL for migrations    |  |    executive summary synthesis, and       |
|     - Row Level Security (RLS)     |  |    dossier generation                     |
|  2. Object Storage                 |  |  - SDK: google-genai v0.1.1               |
|     - Bucket: inspection-evidence  |  +-------------------------------------------+
|     - Signed & Public CDN URLs     |
+------------------------------------+
```

## 3. Component Details

### 3.1 Client Layer
- **Unified SPA Architecture:** Delivered through `static/audit_intelligence.html` and modular JavaScript engines (`static/js/allocation_module.js`).
- **Role Login Gateway:** Enforces strict UI and workflow separation at login between QC Lead (`Priya Deshmukh`, `EMP-1001`) and Field Inspection Engineers (`Anjali Rao`, `Rohit Kale`, etc.).
- **Responsive Theme:** Construction-grade dark mode with high-contrast accessibility tokens, smooth CSS `@keyframes spin` feedback, and mobile safe-area insets.

### 3.2 Backend API Service
- **Framework:** FastAPI with asynchronous I/O and Pydantic v2 data models.
- **Master Checklist Engine:** Dynamic stage-subgroup-checkpoint filtering across 20 stages and 859 standardized checkpoints.
- **Allocation Lifecycle Service:** State machine enforcing transition integrity:
  `Draft` $\rightarrow$ `Allocated` $\rightarrow$ `In Progress` $\rightarrow$ `Pending Review` $\rightarrow$ `Approved` / `Report Issued` (or `Returned for Reinspection`).

### 3.3 Database Layer
- **Primary Production Database:** Supabase PostgreSQL with 15 normalized relational tables.
- **Development & Offline Fallback:** Local SQLite (`audit_intelligence.db`) with automatic connection abstraction in `database_audit.py`.
- **Hybrid Cursor Wrapper:** Seamlessly translates `?` parameters to `%s` and provides dictionary and positional index access (`HybridRow`).

### 3.4 Storage & Assets
- **Object Storage:** Supabase Storage bucket (`inspection-evidence`) for high-resolution site photographs and defect evidence.
- **Local Fallback:** Writes to `static/uploads/evidence/` when cloud object storage credentials are not provided.
