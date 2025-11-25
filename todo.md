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

### 1. Agent Analysis Working Correctly
- [x] Fix Claude model mismatch in `kubernetes_agno_mcp.py` (hardcoded `claude-sonnet-4-20250514` → use config)
- [ ] Verify AI agent triggers on PagerDuty webhook receipt
- [ ] Confirm incident analysis generates proper output
- [ ] Test YOLO mode execution flow
- [ ] Validate agent decision-making and remediation suggestions

**Files to check:**
- `backend/src/oncall_agent/agent.py`
- `backend/src/oncall_agent/agent_enhanced.py`
- `backend/src/oncall_agent/mcp_integrations/kubernetes_agno_mcp.py`
- `backend/src/oncall_agent/config.py`

### 2. Agent Workflow Logs Reaching Frontend
- [x] Verify WebSocket/SSE connection for real-time logs (fixed: SSE must connect directly to backend, not through Next.js rewrites)
- [x] Check agent log streaming to frontend dashboard
- [ ] Confirm log entries appear in incident detail view
- [ ] Test log persistence in database
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

### 6. Incident Report Generation ⚠️ NEEDS PROPER IMPLEMENTATION
- [ ] Review report generation logic
- [ ] Ensure reports include:
  - Incident summary
  - AI analysis results
  - Actions taken (or recommended)
  - Timeline of events
  - Resolution status
- [ ] Test report export (PDF/JSON)
- [ ] Validate report storage and retrieval
- [ ] Connect reports to actual AI agent analysis output
- [ ] Add report generation trigger after incident resolution

**Files to check:**
- `backend/src/oncall_agent/api/routers/insights.py`
- `backend/src/oncall_agent/services/`
- `frontend/app/(dashboard)/reports/`

### 7. UI Fix and Revamp ⚠️ NEEDS PROPER IMPLEMENTATION
- [ ] Remove chaos engineering components
- [ ] Clean up dashboard layout
- [ ] Improve incident list view
- [ ] Enhance incident detail page
- [ ] Add real-time status indicators
- [ ] Implement consistent design system
- [ ] Mobile responsiveness
- [ ] Add loading states and error handling
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

## Known Issues to Fix

1. **Claude Model Mismatch**: `kubernetes_agno_mcp.py:65` uses `claude-sonnet-4-20250514` instead of config value
2. **Hardcoded user_id**: Multiple routers have `user_id=1  # TODO: Get from auth`
3. **Backup files to clean**: `agent.py.bak`, `uv.lock.bak`
4. **Database persistence**: PhonePe service TODOs for database storage

---

## Demo Flow

1. Show dashboard with existing incidents
2. Click "Send Test Event" button
3. Watch PagerDuty webhook arrive
4. Show AI agent analysis in real-time logs
5. Display incident report with analysis
6. (Optional) Show Kubernetes remediation if connected

---

*Last Updated: 2025-11-26*
