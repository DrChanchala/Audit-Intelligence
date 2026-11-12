# SiteIQ — Security & Compliance Architecture

## 1. Authentication & Role-Based Access Control (RBAC)

SiteIQ enforces strict role separation at the entry point of the application:

1. **Role Login Gateway:**
   - Unauthenticated sessions are directed to the Role Login Gateway modal.
   - Users authenticate or select their assigned persona:
     - **QC Lead:** `Priya Deshmukh` (`EMP-1001`) with administrative authority over project quality registers, allocations, reassignment, and approvals.
     - **Inspection Engineers:** Active roster (`Anjali Rao`, `Rohit Kale`, `Vikram Singh`, `Meera Iyer`, `Arjun Mehta`) restricted to allocated inspections and field execution runner.
2. **Session Persistence:**
   - Roles and engineer identities are isolated in protected browser storage and verified with backend routing.
   - Switching roles is explicitly surfaced via a top-level `[ 🚪 Switch Role ]` control that clears active privileges.

---

## 2. Database Protection & Row Level Security (RLS)

- **PostgreSQL Row Level Security:** Enabled on all 15 relational tables in Supabase.
- **Service Isolation:** Public anonymous users cannot execute DDL or modify audit logs directly.
- **Data Integrity Constraints:**
  - Mandatory foreign keys with cascading deletes where appropriate.
  - Check constraints on progress ratings (`0 <= progress <= 100`).
  - Unique constraints on project codes and checkpoint IDs.
- **Hold-Point Gate:**
  - Client-side and backend validation strictly reject inspection submission if any checkpoint remains unevaluated (`Pending`).

---

## 3. Storage & Asset Protection

- Uploaded inspection photographs are scanned, assigned a collision-resistant UUID and timestamp suffix, and stored in the dedicated Supabase Storage bucket (`inspection-evidence`).
- File uploads validate MIME types (`image/jpeg`, `image/png`, `image/webp`).
- Secret keys (`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`) reside exclusively in server-side memory and are never bundled into frontend JavaScript files.

---

## 4. AI Guardrails & Prompt Injection Protection

- The AI Inspection Report Generator (`InspectionReportService`) and Central AI Agent (`ProjectAIAgent`) process structured JSON data from database queries.
- Tool execution is read-only and restricted to safe database queries; the AI model is forbidden from executing arbitrary SQL `DROP`, `UPDATE`, or `DELETE` statements.
