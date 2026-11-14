# SiteIQ Code Review & Security Remediation Matrix

This document tracks the remediation of confirmed security vulnerabilities (V1–V12) and architectural defects from the legacy monolith refactor per `SiteIQ_Refactor_Prompt.md`.

---

## Vulnerabilities Remediation Matrix (V1–V12)

| # | Vulnerability Description | Legacy Location | Remediation | Verification Test | Test File |
|---|---|---|---|---|---|
| **V1** | `POST /api/auth/register` was public; caller chose arbitrary `org_id` and `role`, enabling unauthenticated admin account takeover of any tenant. | `app_audit.py` ~L409 | Public self-registration endpoint removed and replaced with HTTP 410 Gone. User accounts are strictly provisioned by authenticated organization admins or QC leads via `/api/auth/users`. | `test_v1_public_register_gone` | `tests/test_auth.py` |
| **V2** | `GET /api/auth/organizations` was public and returned every registered tenant ID in the database. | `app_audit.py` ~L198 | Tenant listing removed. Endpoint requires authenticated session and returns strictly the caller's own organization. Anonymous requests return 401. | `test_v2_org_enumeration_prevented` | `tests/test_auth.py` |
| **V3** | `GET /api/auth/users?org_id=X` allowed cross-tenant user listing by supplying a foreign tenant ID. | `app_audit.py` ~L291 | `org_id` query parameter is ignored. User lookup is strictly pinned to `principal.org_id` from the verified session token. | `test_v3_org_user_leak` | `tests/test_tenancy.py` |
| **V4** | `POST /api/projects` accepted `org_id` in request body, allowing cross-tenant writes into another organization. | `app_audit.py` ~L591 | Body `org_id` parameter is ignored. New projects are strictly created under `principal.org_id` from the authenticated session. | `test_v4_cross_tenant_project_write` | `tests/test_tenancy.py` |
| **V5** | ~30 endpoints lacked authentication (allocations, NCs, approvals, summary, engineers, inspections, reports, master checklist). | Throughout legacy routes | Applied FastAPI dependency guards (`any_user`, `admin_or_qc`, `qc_lead_only`, `engineer_only`) across all routes. Unauthenticated requests return 401. | `test_v5_unauthenticated_endpoints_blocked`<br>`test_access_matrix_roles` (100% /api routes) | `tests/test_auth.py`<br>`tests/test_access_matrix.py` |
| **V6** | JWT secret had a hard-coded default fallback in source code (`secret-jwt-key`), enabling offline token forgery. | `auth_service.py` L20 | Production refuses weak or default secrets; tokens validated using HMAC-SHA256 with constant-time verification; forged secrets rejected with 401. | `test_v6_forged_jwt_rejected` | `tests/test_auth.py` |
| **V7** | Evidence upload was unauthenticated, accepted arbitrary file extensions (e.g. `.html` stored XSS), and served files same-origin from `/static`. | `app_audit.py` ~L1143 | Upload restricted to authenticated engineer on own editable allocation; magic-byte validation allows only JPEG, PNG, or WebP; files served only through authenticated `/api/evidence` route with tenant isolation. | `test_v7_evidence_upload_hardened`<br>`test_magic_byte_sniffing` | `tests/test_evidence.py` |
| **V8** | `POST /api/seed` was unauthenticated and wiped core database tables upon request. | `app_audit.py` ~L191 | Endpoint permanently removed (returns 410 Gone). Demo data initialization is moved to standalone CLI script `scripts/seed_demo.py` which refuses execution if `APP_ENV=production`. | `test_v8_public_seed_gone` | `tests/test_auth.py` |
| **V9** | Supabase storage bucket used public URLs and service key exposed in client requests. | Upload endpoint | Storage bucket set to private; file retrieval mediated by backend using signed URLs or private local volume streaming with tenant verification. | `test_v9_evidence_storage_private` | `tests/test_evidence.py` |
| **V10** | 73 `innerHTML` sinks; unsanitized `marked.parse()` markdown output in AI dossier and inspection cards. | Frontend | Safe client template rendering via tagged template `html` (auto-escaping all interpolations) and DOMPurify for markdown parsing. Server stores literal string values and rejects raw script evaluation. | `test_v10_stored_xss_sink_prevention` | `tests/test_auth.py` |
| **V11** | Audit trail identities (`actor_name`, `by_user`, `allocated_by`, `reviewer_name`) defaulted to hardcoded strings and were taken from client request bodies. | Schemas & handlers | Audit trail identities and action records are strictly populated from `principal.actor` derived from the cryptographically verified session token. Client body fields are ignored. | `test_v11_audit_trail_actor_pinned_to_session` | `tests/test_allocation_lifecycle.py` |
| **V12** | CORS wildcard `*` allowed credentials; raw exception strings (`detail=str(e)`) exposed internal implementation details and database structures. | App initialization | Production settings reject wildcard CORS origins; centralized exception handler catches unhandled exceptions and outputs an opaque reference ID (`Internal error (ref <id>)`), logging tracebacks internally. | `test_v12_cors_and_error_sanitization` | `tests/test_auth.py` |

---

## Architectural & Reliability Fixes

1. **SQL Portability**: Replaced SQLite-specific syntax (`INSERT OR REPLACE`, `GROUP_CONCAT`) with ANSI-standard SQL (`INSERT ... ON CONFLICT (...) DO UPDATE`) compatible with PostgreSQL 16 and SQLite.
2. **SQL Parameter Translation**: Fixed parameter placeholder replacement (`to_pg_sql`) to preserve `%` and `?` inside SQL string literals while translating external parameters to `%s` and escaping standalone `%` to `%%`.
3. **Session Hardening**: Sessions use `HttpOnly`, `SameSite=Lax` cookies; state-changing requests (POST, PUT, DELETE) require the `X-SiteIQ-CSRF: 1` header.
4. **Tenant Isolation**: Cross-tenant requests return 404 (Not Found) rather than 403 (Forbidden) to prevent tenant ID enumeration or existence probing.
5. **Engineer Scoping**: Engineers can only view and update allocations assigned to their specific user or employee ID.
