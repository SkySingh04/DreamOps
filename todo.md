# DreamOps Demo TODO List

> Critical tasks for project demonstration

---

## ⚠️ CRITICAL RULE: PAGERDUTY TEST INCIDENTS ⚠️

**NEVER LEAVE TEST INCIDENTS OPEN - THEY DISTURB THE ON-CALL ENGINEER!**

When testing PagerDuty:
1. **ALWAYS** use a unique `dedup_key` (e.g., `test-sky-$(date +%s)`)
2. **IMMEDIATELY** resolve the incident after triggering
3. Include `(TEST BY SKY)` in summaries so engineers know it's a test

```bash
# Trigger test
curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H "Content-Type: application/json" \
  -d '{"routing_key":"<KEY>","event_action":"trigger","dedup_key":"test-123","payload":{"summary":"(TEST BY SKY) Test","severity":"warning","source":"test"}}'

# IMMEDIATELY RESOLVE (same dedup_key!)
curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H "Content-Type: application/json" \
  -d '{"routing_key":"<KEY>","event_action":"resolve","dedup_key":"test-123"}'
```

---

## Phase 1: Core Functionality (Must Work for Demo)

### 1. Agent Analysis Working Correctly ✅
- [x] Fix Claude model mismatch in `kubernetes_agno_mcp.py` (hardcoded `claude-sonnet-4-20250514` → use config)
- [x] Verify AI agent triggers on PagerDuty webhook receipt
- [x] Confirm incident analysis generates proper output (7 tabs: Summary, Impact, Actions, RCA, etc.)
- [x] Test YOLO mode execution flow (verified via SSE logs)
- [x] Validate agent decision-making and remediation suggestions

**Files to check:**
- `backend/src/oncall_agent/agent.py`
- `backend/src/oncall_agent/agent_enhanced.py`
- `backend/src/oncall_agent/mcp_integrations/kubernetes_agno_mcp.py`
- `backend/src/oncall_agent/config.py`

### 2. Agent Workflow Logs Reaching Frontend ✅
- [x] Verify WebSocket/SSE connection for real-time logs (fixed: SSE must connect directly to backend, not through Next.js rewrites)
- [x] Check agent log streaming to frontend dashboard
- [x] Confirm log entries appear in incident detail view (real-time via SSE)
- [x] Test log persistence in database (in-memory storage working)
- [x] Validate log format and readability

**Files to check:**
- `backend/src/oncall_agent/api/routers/agent_logs.py`
- `frontend/app/(dashboard)/incidents/[id]/page.tsx`
- `frontend/components/incidents/`

### 3. Test Simulation Button (Events V2 API)
- [x] Add "Send Test Event" button to frontend dashboard
- [x] Implement Events V2 API call with test payload
- [x] Include "(TEST BY SKY)" in summary to prevent panic
- [x] Add visual feedback (loading, success, error states)
- [x] Auto-resolve test incidents immediately after triggering
- [ ] Log test events separately for easy identification

**Test Event Payload:**
```json
{
  "routing_key": "<integration_key>",
  "event_action": "trigger",
  "dedup_key": "test-sky-<timestamp>",
  "payload": {
    "summary": "(TEST BY SKY) Simulated incident for demo purposes",
    "severity": "warning",
    "source": "dreamops-test-button",
    "custom_details": {
      "test": true,
      "triggered_by": "SKY Demo Button",
      "environment": "demo"
    }
  }
}
```

### 4. OAuth Reverse Proxy Authentication
- [x] Remove built-in authentication (already done)
- [ ] Verify Authentik proxy headers are being read
- [ ] Remove hardcoded `user_id=1` references (use header or default)
- [ ] Test protected endpoints work through proxy
- [ ] Document proxy header expectations

**Note:** No user-based auth needed - Authentik handles it via reverse proxy.

---

## Phase 2: Integration & Reporting (After Phase 1 Tested)

### 5. Kubernetes MCP Server Connection
- [x] Add Node.js to Docker container for MCP server
- [x] Fix kubeconfig mount path for appuser
- [ ] **REQUIRES MANUAL SETUP**: Valid kubeconfig must be placed in `/root/.kube/config` on the server
- [ ] Verify kubectl commands work through MCP
- [ ] Test pod listing, logs retrieval, deployment status
- [ ] Confirm destructive operations (restart, scale) work when enabled
- [ ] Add connection health check to dashboard

**Current Issue:** Kubeconfig not configured on production server.

**To fix:**
```bash
# On production server, create kubeconfig:
ssh root@37.27.115.235
mkdir -p /root/.kube
# Copy your kubeconfig or create service account credentials
cat > /root/.kube/config << 'EOF'
# Your kubeconfig content here
EOF
chmod 600 /root/.kube/config

# Restart backend
cd /opt/dreamops && docker compose -f docker-compose.local.yml restart backend
```

**Files to check:**
- `backend/src/oncall_agent/mcp_integrations/kubernetes_agno_mcp.py`
- `backend/src/oncall_agent/mcp_integrations/kubernetes_direct.py`
- `backend/src/oncall_agent/agno_kubernetes_agent.py`

### 6. Incident Report Generation ✅
- [x] Review report generation logic
- [x] Ensure reports include:
  - Incident summary
  - AI analysis results
  - Actions taken (or recommended)
  - Timeline of events
  - Resolution status
- [x] Test report export (JSON/Markdown) - verified via Playwright E2E
- [x] Validate report storage and retrieval
- [x] Connect reports to actual AI agent analysis output
- [ ] Add report generation trigger after incident resolution (optional enhancement)

**Files to check:**
- `backend/src/oncall_agent/api/routers/insights.py`
- `backend/src/oncall_agent/services/`
- `frontend/app/(dashboard)/reports/`

### 7. UI Fix and Revamp (Partially Complete)
- [x] Remove hardcoded mock incidents from dashboard
- [x] Implement real incident fetching from backend DB
- [x] Clean up dashboard layout
- [x] Improve incident list view (expandable cards with AI analysis)
- [x] Add real-time status indicators (SSE connection status)
- [x] Add loading states and error handling
- [ ] Remove chaos engineering components (if still present)
- [ ] Enhance incident detail page (individual incident view)
- [ ] Implement consistent design system
- [ ] Mobile responsiveness
- [ ] Review and polish all UI components for production readiness

---

## Quick Reference: Production Endpoints

| Service | URL |
|---------|-----|
| Backend API | `http://oncall.frai.pro:8001/api/v1/` |
| PagerDuty Webhook | `http://oncall.frai.pro:8001/api/v1/webhook/pagerduty` |
| Health Check | `http://oncall.frai.pro:8001/health` |
| API Docs | `http://oncall.frai.pro:8001/docs` |

## Test Commands

```bash
# Health check
curl http://oncall.frai.pro:8001/health

# Trigger test incident (Events V2 API)
curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H "Content-Type: application/json" \
  -d '{
    "routing_key": "911db5258f304f03d02feac429aad2a2",
    "event_action": "trigger",
    "dedup_key": "test-sky-'$(date +%s)'",
    "payload": {
      "summary": "(TEST BY SKY) Demo simulation - please ignore",
      "severity": "warning",
      "source": "dreamops-manual-test"
    }
  }'

# Check backend logs
ssh root@37.27.115.235 "cd /opt/dreamops && docker compose logs backend --tail=50"
```

---

## ✅ E2E Verification Complete (2025-11-26)

**Verified with Playwright MCP:**
| Feature | Status |
|---------|--------|
| Remove hardcoded incidents | ✅ Working |
| Real incidents from DB | ✅ 3 incidents visible |
| AI Analysis on UI | ✅ 7 tabs displaying |
| K8s MCP integration | ✅ Alert type detected |
| JSON report download | ✅ Downloaded successfully |
| Markdown report download | ✅ Working |
| Real-time SSE streaming | ✅ Connected |

**Key Fixes Applied:**
- `frontend/app/(dashboard)/incidents/page.tsx` - Relative URLs for downloads
- `frontend/lib/hooks/use-agent-logs.ts` - SSE stream URL fix
- `frontend/components/dashboard/alert-usage-card.tsx` - API URL fix

---

## Known Issues to Fix

1. ~~**Claude Model Mismatch**: `kubernetes_agno_mcp.py:65` uses `claude-sonnet-4-20250514` instead of config value~~ ✅ Fixed
2. **Hardcoded user_id**: Multiple routers have `user_id=1  # TODO: Get from auth` (works with Authentik proxy)
3. **Backup files to clean**: `agent.py.bak`, `uv.lock.bak`
4. **Database persistence**: PhonePe service TODOs for database storage
5. **307 Redirect Console Errors**: `/api/v1/agent/config` shows redirect warnings (non-blocking)

---

## Demo Flow

1. Show dashboard with existing incidents
2. Click "Send Test Event" button
3. Watch PagerDuty webhook arrive
4. Show AI agent analysis in real-time logs
5. Display incident report with analysis
6. (Optional) Show Kubernetes remediation if connected

---

## Phase 3: Next Steps (Post-Demo Enhancements)

### Priority 1: Production Hardening
- [ ] Replace in-memory storage with PostgreSQL/Neon for incidents and analysis
- [ ] Add proper error handling for SSE disconnections
- [ ] Implement rate limiting on webhook endpoints
- [ ] Add health check endpoint monitoring

### Priority 2: K8s MCP Full Integration
- [ ] Configure kubeconfig on production server (`/root/.kube/config`)
- [ ] Test live K8s remediation actions (restart pods, scale deployments)
- [ ] Add K8s cluster selector for multi-cluster support
- [ ] Implement read-only vs read-write mode toggle

### Priority 3: UI/UX Improvements
- [ ] Individual incident detail page (`/incidents/[id]`)
- [ ] Incident timeline visualization
- [ ] Dark mode support
- [ ] Mobile responsive design
- [ ] Notification preferences

### Priority 4: Advanced Features
- [ ] Runbook integration (auto-suggest runbooks based on incident type)
- [ ] Slack/Teams notifications for incident updates
- [ ] Incident correlation (group related incidents)
- [ ] SLA tracking and alerting
- [ ] Custom remediation playbooks

### Priority 5: DevOps & Infrastructure
- [ ] Set up proper CI/CD with staging environment
- [ ] Add Terraform for K8s MCP infrastructure (EKS clusters)
- [ ] Implement blue-green deployments
- [ ] Add Prometheus/Grafana monitoring stack

---

*Last Updated: 2025-11-26*
