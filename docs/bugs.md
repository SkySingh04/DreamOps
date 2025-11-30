# DreamOps Bug Report

**Date:** 2025-11-30
**Environment:** Production (37.27.115.235:8001)
**Tester:** Claude Code E2E Test

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 3 |
| High | 5 |
| Medium | 2 |
| Low | 1 |
| **Total** | **11** |

---

## Critical Bugs

### BUG-001: CORS/Redirect Issue on Agent API Endpoints

**Severity:** Critical
**Status:** Open
**Affected Pages:** AI Agents (`/ai-control`)

**Description:**
API calls to `/api/v1/agent/*` endpoints are being redirected (307) from port 8001 to port 80. Since port 80 is served by K3s ingress-nginx (not the backend), the CORS headers are missing, causing all requests to fail.

**Affected Endpoints:**
- `/api/v1/agent/config`
- `/api/v1/agent/action-history`
- `/api/v1/agent/approvals/pending`
- `/api/v1/agent/safety-config`
- `/api/v1/agent/confidence-history`

**Console Error:**
```
Access to fetch at 'http://37.27.115.235/api/v1/agent/config' (redirected from
'http://37.27.115.235:8001/api/v1/agent/config/') has been blocked by CORS policy
```

**Root Cause:**
FastAPI's trailing slash redirect behavior. When frontend calls `/api/v1/agent/config/` (with trailing slash), FastAPI issues a 307 redirect to `/api/v1/agent/config` but the redirect URL loses the port number, defaulting to port 80.

**Suggested Fix:**
1. Option A: Update FastAPI router to not redirect trailing slashes
   ```python
   app = FastAPI(redirect_slashes=False)
   ```
2. Option B: Ensure frontend calls endpoints without trailing slashes
3. Option C: Configure nginx/traefik to preserve port on redirects

---

### BUG-002: AI Analysis Not Displayed in UI

**Severity:** Critical
**Status:** Open
**Affected Pages:** Incidents (`/incidents`)

**Description:**
When expanding an incident, the AI Analysis section shows "Waiting for AI analysis..." even though the API endpoint returns complete analysis data.

**Evidence:**
- UI shows: "Waiting for AI analysis..."
- API returns full analysis with root cause, remediation steps, kubectl commands

**API Response (working):**
```bash
curl http://37.27.115.235:8001/api/v1/incidents/Q1DVU5S23V5JIV/analysis
# Returns complete JSON with analysis, k8s_alert_type, remediation commands
```

**Root Cause:**
Frontend component is not fetching or displaying the analysis data from the `/api/v1/incidents/{id}/analysis` endpoint.

**Suggested Fix:**
Update the incident detail component to:
1. Fetch analysis from `/api/v1/incidents/{incident_id}/analysis`
2. Display the `analysis` field content
3. Show the `k8s_alert_type` and remediation commands

**File to Fix:** `frontend/components/incidents/incident-detail.tsx` (or similar)

---

### BUG-003: Missing Database Table `incident_reports`

**Severity:** Critical
**Status:** Open
**Affected Features:** Report Downloads (JSON, Markdown, PDF)

**Description:**
Both JSON and Markdown report download endpoints return 500 Internal Server Error because the `incident_reports` database table does not exist.

**Backend Error:**
```
asyncpg.exceptions.UndefinedTableError: relation "incident_reports" does not exist
```

**Affected Endpoints:**
- `GET /api/v1/incidents/{id}/report/json` → 500
- `GET /api/v1/incidents/{id}/report/markdown` → 500

**Suggested Fix:**
1. Create migration for `incident_reports` table in `frontend/lib/db/schema.ts`
2. Run migration: `npm run db:migrate:production`

**Proposed Schema:**
```typescript
export const incidentReports = pgTable('incident_reports', {
  id: text('id').primaryKey(),
  incidentId: text('incident_id').notNull().references(() => incidents.id),
  reportType: text('report_type').notNull(), // 'json', 'markdown', 'pdf'
  content: text('content').notNull(),
  generatedAt: timestamp('generated_at').defaultNow(),
  createdAt: timestamp('created_at').defaultNow(),
});
```

---

## High Severity Bugs

### BUG-004: Integrations API 500 Error

**Severity:** High
**Status:** Open
**Affected Pages:** Integrations (`/integrations`)

**Description:**
The integrations list endpoint returns a 500 error with message: `"object list can't be used in 'await' expression"`

**Affected Endpoint:**
- `GET /api/v1/integrations/` → 500

**Root Cause:**
Backend code is using `await` on a list object instead of an async function.

**File to Fix:** `backend/src/oncall_agent/api/routers/integrations.py`

**Suggested Fix:**
```python
# Wrong:
integrations = await [...]  # Can't await a list

# Correct:
integrations = await asyncio.gather(*[...])  # Or just remove await if not async
```

---

### BUG-005: Test Event Button Fails - Missing PagerDuty Events Key

**Severity:** High
**Status:** Open
**Affected Features:** Simulate Test Event button

**Description:**
Clicking "Send Test Event" shows error toast: "PagerDuty Events Integration Key not configured. Set PAGERDUTY_EVENTS_INTEGRATION_KEY in environment."

**Root Cause:**
Production environment is missing `PAGERDUTY_EVENTS_INTEGRATION_KEY` environment variable.

**Suggested Fix:**
1. Get the Events Integration Key from PagerDuty (different from API Key)
2. Add to production environment:
   ```bash
   ssh root@37.27.115.235
   cd /opt/dreamops
   # Add to docker-compose.yml or .env:
   PAGERDUTY_EVENTS_INTEGRATION_KEY=your-events-key
   docker compose up -d backend
   ```

---

### BUG-006: JSON Report Download 500 Error

**Severity:** High
**Status:** Open
**Affected Features:** Report Downloads

**Description:**
Clicking "JSON" download button opens new tab with 500 error.

**Related To:** BUG-003 (Missing `incident_reports` table)

---

### BUG-007: Markdown Report Download 500 Error

**Severity:** High
**Status:** Open
**Affected Features:** Report Downloads

**Description:**
Clicking "Markdown" download button returns 500 error.

**Related To:** BUG-003 (Missing `incident_reports` table)

---

### BUG-011: Missing `dashboard_incidents` Database Table

**Severity:** High
**Status:** Open
**Affected Pages:** Dashboard (`/dashboard`)

**Description:**
The dashboard page queries `dashboard_incidents` table which doesn't exist in the database. This causes all dashboard API routes to fail silently and return empty/default data.

**Root Cause:**
The table definition exists in `frontend/lib/db/dashboard-queries.ts` but was never added to the schema or migrated.

**Impact:**
- Dashboard shows "..." for Active Incidents
- Dashboard shows "..." for Resolved Today
- Recent incidents list is empty
- AI Agent status defaults to "online" regardless of actual state

**Suggested Fix:**
1. Add `dashboardIncidents` table to `frontend/lib/db/schema.ts`
2. Generate migration: `npm run db:generate`
3. Run migration: `npm run db:migrate:production`
4. Implement backend sync service to populate this table from PagerDuty incidents

---

## Medium Severity Bugs

### BUG-008: Dashboard API Endpoints Return 404

**Severity:** Medium
**Status:** Open
**Affected Pages:** Dashboard (`/dashboard`)

**Description:**
Dashboard page shows placeholder data ("...", "0") because the following API endpoints don't exist:

**Missing Endpoints:**
- `GET /api/public/dashboard/metrics` → 404
- `GET /api/public/dashboard/incidents?limit=5` → 404
- `GET /api/public/dashboard/ai-actions?limit=5` → 404

**Impact:**
- "Active Incidents" shows "..."
- "Resolved Today" shows "..."
- "AI Actions" shows "..."
- Recent incidents list empty
- Recent AI actions list empty

**Suggested Fix:**
Create these endpoints in the backend API or update frontend to use existing endpoints:
- Use `/api/v1/incidents/` for incidents
- Use `/api/v1/agent/action-history` for AI actions
- Create metrics aggregation endpoint

---

### BUG-009: Missing Avatar Image

**Severity:** Medium
**Status:** Open
**Affected Pages:** All pages (header)

**Description:**
Console shows 404 for `/avatar.png` on every page load.

**Suggested Fix:**
1. Add default avatar image to `frontend/public/avatar.png`
2. Or update component to use placeholder/initials when image missing

---

## Low Severity Bugs

### BUG-010: Incidents Show "Service: Unknown" and Empty Assignee

**Severity:** Low
**Status:** Open
**Affected Pages:** Incidents (`/incidents`)

**Description:**
All incidents display:
- "Service: Unknown" instead of actual service name
- "Assignee:" with empty value

**Root Cause:**
PagerDuty webhook payload may not include service/assignee data, or the data isn't being parsed/stored correctly.

**Suggested Fix:**
1. Check PagerDuty webhook payload for service/assignee fields
2. Update incident model to store these fields
3. Display fallback text like "Unassigned" instead of empty

---

## Data Loading Architecture

### How Frontend Loads Data

The frontend uses a **hybrid architecture**:

1. **Backend API Calls** (`/api/v1/*`) - Primary pattern
   - Incidents list, AI analysis, agent config
   - Uses `apiClient` class in `frontend/lib/api-client.ts`

2. **Next.js API Routes** (`/api/public/*`) - Dashboard data
   - Direct database queries via Drizzle ORM
   - Server-side only (no client DB access)

3. **Server-Sent Events (SSE)** - Real-time logs
   - Endpoint: `/api/v1/agent-logs/stream`
   - Hook: `useAgentLogs()` in `frontend/lib/hooks/use-agent-logs.ts`

### Frontend Data Sources Audit

| Page | Data Source | API/DB | Status | Issue |
|------|-------------|--------|--------|-------|
| Dashboard | `/api/public/dashboard/metrics` | DB Query | ❌ | Missing `dashboard_incidents` table |
| Dashboard | `/api/public/dashboard/incidents` | DB Query | ❌ | Missing `dashboard_incidents` table |
| Dashboard | `/api/public/dashboard/ai-actions` | DB Query | ❌ | Missing `ai_actions` data |
| AI Agents | `/api/v1/agent/config` | Backend API | ❌ | CORS blocked (BUG-001) |
| AI Agents | `/api/v1/agent/action-history` | Backend API | ❌ | CORS blocked |
| AI Agents | `/api/v1/agent/approvals/pending` | Backend API | ❌ | CORS blocked |
| Incidents | `/api/v1/incidents/` | Backend API | ✅ | Working |
| Incident Detail | `/api/v1/incidents/{id}/analysis` | Backend API | ⚠️ | API works, UI doesn't fetch |
| Integrations | `/api/v1/integrations/` | Backend API | ❌ | 500 error (BUG-004) |
| Settings | Various `/api/v1/*` endpoints | Backend API | ⚠️ | Partial |

### Database Tables Status

#### Tables Defined in Schema (`frontend/lib/db/schema.ts`)

| Table | Exists | Used By | Status |
|-------|--------|---------|--------|
| `users` | ✅ | Auth, all pages | Working |
| `incidents` | ✅ | Incidents page (via backend) | Working |
| `incident_logs` | ✅ | Incident history | Working |
| `metrics` | ✅ | Dashboard metrics | Needs data |
| `ai_actions` | ✅ | Dashboard, AI history | Needs data |
| `alert_usage` | ✅ | Usage tracking | Working |
| `integrations` | ✅ | Integrations page | Needs fixing |
| `user_api_keys` | ✅ | Settings | Working |
| `agent_settings` | ✅ | AI Agent config | Working |
| `kubernetes_credentials` | ✅ | K8s integration | Working |

#### Tables NOT in Schema but Referenced

| Table | Referenced By | Status |
|-------|---------------|--------|
| `dashboard_incidents` | `dashboard-queries.ts` (inline definition) | **MISSING** - Causes dashboard 404s |
| `incident_reports` | Report download endpoints | **MISSING** - Causes report 500s |

### Missing Database Migrations

**BUG-011: Missing `dashboard_incidents` table**

The `dashboard-queries.ts` file defines `dashboardIncidents` table inline but it doesn't exist in the database:

```typescript
// In frontend/lib/db/dashboard-queries.ts
const dashboardIncidents = pgTable('dashboard_incidents', {
  id: serial('id').primaryKey(),
  userId: integer('user_id').notNull(),
  title: varchar('title', { length: 255 }).notNull(),
  description: text('description'),
  severity: varchar('severity', { length: 20 }).notNull(),
  status: varchar('status', { length: 20 }).notNull().default('open'),
  source: varchar('source', { length: 50 }).notNull(),
  sourceId: varchar('source_id', { length: 255 }),
  assignedTo: integer('assigned_to'),
  resolvedBy: integer('resolved_by'),
  resolvedAt: timestamp('resolved_at'),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
  metadata: text('metadata'),
});
```

**Fix Required:**
1. Add this table definition to `frontend/lib/db/schema.ts`
2. Generate migration: `npm run db:generate`
3. Run migration: `npm run db:migrate:production`
4. Backend needs to sync PagerDuty incidents to this table

**BUG-003 (Updated): Missing `incident_reports` table**

Add to schema:
```typescript
export const incidentReports = pgTable('incident_reports', {
  id: text('id').primaryKey(),
  incidentId: text('incident_id').notNull(),
  reportType: text('report_type').notNull(), // 'json', 'markdown', 'pdf'
  content: text('content').notNull(),
  generatedAt: timestamp('generated_at').defaultNow(),
  createdAt: timestamp('created_at').defaultNow(),
});
```

### Data Flow Diagrams

**Dashboard Page:**
```
Browser
  │
  └─> useQuery('/api/public/dashboard/metrics')
        │
        └─> Next.js API Route (frontend/app/api/public/dashboard/metrics/route.ts)
              │
              └─> getDashboardMetrics() (frontend/lib/db/dashboard-queries.ts)
                    │
                    └─> Drizzle ORM Query
                          │
                          └─> PostgreSQL (Neon)
                                │
                                └─> ❌ Table 'dashboard_incidents' does not exist
```

**Incidents Page:**
```
Browser
  │
  └─> useQuery('/api/v1/incidents')
        │
        └─> Backend API (FastAPI)
              │
              └─> PagerDuty API
                    │
                    └─> ✅ Returns incidents
```

**AI Analysis (Broken):**
```
Browser
  │
  └─> ❌ UI doesn't call API

(API works if called directly)
  │
  └─> GET /api/v1/incidents/{id}/analysis
        │
        └─> ✅ Returns full analysis with kubectl commands
```

---

## Screenshots Reference

All screenshots captured during testing are saved in `.playwright-mcp/`:

| File | Description |
|------|-------------|
| `01-dashboard.png` | Dashboard with missing metrics |
| `02-ai-agents.png` | AI Agents page (CORS errors) |
| `03-incidents.png` | Incidents list |
| `04-integrations.png` | Integrations (all zeros) |
| `05-settings.png` | Settings page |
| `06-simulate-test-dialog.png` | Test event dialog |
| `07-final-confirmation-dialog.png` | Confirmation step |
| `08-test-event-error.png` | PagerDuty key error |
| `09-incident-expanded-waiting.png` | AI Analysis "Waiting..." |
| `10-json-report-500-error.png` | Report 500 error |
| `11-incidents-final-state.png` | Final state |

---

## Priority Fix Order

### Phase 1: Critical Database & API Fixes
1. **BUG-003** - Create `incident_reports` table (blocks reports)
2. **BUG-011** - Create `dashboard_incidents` table (blocks dashboard)
3. **BUG-001** - Fix CORS redirect (blocks AI Agents page)
4. **BUG-002** - Display AI analysis in UI (core feature broken)

### Phase 2: High Priority Fixes
5. **BUG-004** - Fix integrations await bug (blocks integrations)
6. **BUG-005** - Add PagerDuty Events key (blocks testing)
7. **BUG-006** - JSON Report fix (depends on BUG-003)
8. **BUG-007** - Markdown Report fix (depends on BUG-003)

### Phase 3: Medium/Low Priority
9. **BUG-008** - Dashboard API error handling
10. **BUG-009** - Add avatar image
11. **BUG-010** - Fix service/assignee display

---

## Environment Info

- **Server:** 37.27.115.235
- **Frontend Port:** 8001 (via Docker)
- **Backend Port:** 8001 (same container or proxied)
- **K3s Ingress:** Port 80/443
- **Database:** Neon PostgreSQL
