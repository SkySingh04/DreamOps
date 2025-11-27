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

### 3. Test Simulation Button (Events V2 API) ✅
- [x] Add "Send Test Event" button to frontend dashboard
- [x] Implement Events V2 API call with test payload
- [x] Include "(TEST BY SKY)" in summary to prevent panic
- [x] Add visual feedback (loading, success, error states)
- [x] Auto-resolve test incidents immediately after triggering
- [x] Log test events separately for easy identification

### 4. Kubernetes MCP Server Connection ✅
- [x] Add Node.js to Docker container for MCP server
- [x] Fix kubeconfig mount path for appuser
- [x] Deploy kubeconfig to production server (`/root/.kube/config`)
- [x] Verify kubectl commands work through MCP
- [x] Test pod listing, logs retrieval, deployment status
- [x] Access to 3 EKS clusters: staging, infra-dev, infra-prod
- [ ] Test destructive operations (restart, scale) in YOLO mode
- [x] Add K8s connection health check to dashboard

### 5. PostgreSQL Persistence ✅
- [x] Replace in-memory incident storage with PostgreSQL
- [x] Migrate AI analysis results to database
- [x] Add database connection health check
- [x] Implement proper error handling for DB failures

**Current State:** PostgreSQL persistence is now working. Tables auto-created on startup.

**Files modified:**
- `backend/src/oncall_agent/api/routers/incidents.py` - Uses IncidentService/AnalysisService
- `backend/src/oncall_agent/api/webhooks.py` - Uses database for incidents/analysis
- `backend/src/oncall_agent/services/incident_service.py` - New database service
- `backend/api_server.py` - Database initialization on startup

### 6. Slack Notifications (Analysis Complete) ✅ COMPLETE
- [x] Add Slack webhook integration for analysis notifications
- [x] Send notification when AI analysis completes
- [x] Include incident summary, severity, and recommended actions
- [x] Configure Slack webhook URL in environment variables
- [x] Post as thread reply under PagerDuty incident message
- [x] Concise format with cause, fixes, and report link

**Status:** Fully deployed and working! Slack notifications post as thread replies under PagerDuty messages.

**Configuration (Production):**
```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C07A3NZAYSD
SLACK_CHANNEL=#oncall
SLACK_ENABLED=true
```

**Notification Format:**
```
🤖 AI Analysis

Cause: Out of Memory (OOM) - Pod exceeded memory limits

Recommended Fixes:
• kubectl get pods -n production --field-selector=status.phase=Failed
• kubectl rollout restart deployment api-service -n production

View Full Report (link to incident)
```

### 7. OAuth Reverse Proxy Authentication ✅
- [x] Remove built-in authentication (already done)
- [x] Verify Authentik proxy headers are being read (`dependencies.py`)
- [x] Hardcoded `user_id=1` are intentional fallbacks for demo/no-auth mode
- [x] Test protected endpoints work through proxy (webhooks use `get_user_from_request`)
- [x] Document proxy header expectations

**Status:** Authentik integration is complete. Headers parsed:
- `X-Authentik-Username`, `X-Authentik-Email`, `X-Authentik-Name`
- `X-Authentik-Uid`, `X-Authentik-Groups`

Falls back to demo user (id="1") when not configured.

### 8. UI Redesign ⏳ (INPUT NEEDED FROM SKY - DO LAST)
> **Status:** Waiting for design input from Sky. This will be done last in Phase 1.

- [ ] Complete UI redesign (all pages)
- [ ] Redesign incident list view
- [ ] Redesign incident detail page
- [ ] Redesign report download UI
- [ ] Redesign AI agent logs panel
- [ ] Redesign dashboard layout
- [ ] Mobile responsiveness
- [ ] Consistent design system
- [ ] Dark mode support (optional)

**Note:** Sky to provide design mockups/requirements before implementation.

---

## Phase 2: Enhanced Features (After Phase 1 Complete)

### 1. Incident Report Generation ✅
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

### 2. Advanced K8s Operations
- [ ] Test YOLO mode destructive operations on staging cluster
- [ ] Implement rollback safeguards
- [ ] Add K8s cluster selector for multi-cluster support
- [ ] Implement read-only vs read-write mode toggle in UI

### 3. Monitoring & Alerting Enhancements
- [ ] Add Prometheus/Grafana monitoring stack
- [ ] Create alerts for backend health
- [ ] Monitor SSE connection stability
- [ ] Track API response times

---

## Quick Reference: Production Endpoints

| Service | URL |
|---------|-----|
| Backend API | `http://oncall.frai.pro:8001/api/v1/` |
| PagerDuty Webhook | `http://oncall.frai.pro:8001/webhook/pagerduty` |
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

## ✅ LiteLLM Integration Complete (2025-11-28)

**Migration from Direct Anthropic API to LiteLLM Proxy:**

| Component | Status | Model |
|-----------|--------|-------|
| `agent.py` | ✅ Updated | Uses OpenAI SDK with LiteLLM base_url |
| `agent_enhanced.py` | ✅ Updated | AsyncOpenAI client |
| `enhanced_agent.py` | ✅ Updated | AsyncOpenAI client |
| `kubernetes_agno_mcp.py` | ✅ Updated | Agno OpenAIChat with LiteLLM |
| `github_agno_mcp.py` | ✅ Updated | Agno OpenAIChat with LiteLLM |
| `agno_github_agent.py` | ✅ Updated | Agno OpenAIChat with LiteLLM |
| Production Config | ✅ Deployed | `gpt-4o` via Azure fallback |

**Configuration:**
```env
USE_LITELLM=true
LITELLM_API_BASE=https://litellm.calmdune-a4eb8421.westus.azurecontainerapps.io
LITELLM_API_KEY=sk--_QXj0LN6knTEtPI3N2StQ
CLAUDE_MODEL=gpt-4o
```

**E2E Test Results (Playwright):**
- AI Analysis: ✅ Working (85% confidence, 15.27s response time)
- Model Used: gpt-4o via LiteLLM proxy
- Real-time Logs: ✅ Streaming via SSE

---

## ✅ K8s MCP & Settings Persistence Verification (2025-11-28)

### Proof #1: Kubernetes MCP Used for Triage

**Backend Logs Evidence:**
```
kubernetes_agno_mcp - INFO - Executing action: identify_oom_pods
kubernetes_agno_mcp - INFO - Query: Execute Kubernetes operation: identify_oom_pods with parameters: {'namespace': 'default', 'timeframe': '1h', 'dry_run': True}
kubernetes_agno_mcp - INFO - Executing action: increase_memory_limits
kubernetes_agno_mcp - INFO - Query: Execute Kubernetes operation: increase_memory_limits with parameters: {'namespace': 'default', 'increase_percentage': 50, 'target_deployments': 'auto-detect', 'dry_run': True}
```

**K8s-Specific Detection:**
- Alert Type: `oom_kill` (correctly identified)
- Resolution Actions Generated:
  - `identify_oom_pods` (95% confidence)
  - `increase_memory_limits` (90% confidence)
  - `scale_deployment` (75% confidence)

**K8s Commands in Analysis:**
- `kubectl get pods -n production --field-selector=status.phase=Failed`
- `kubectl patch deployment payment-service-deployment -n production`
- `kubectl scale deployment payment-service-deployment -n production --replicas=3`
- `kubectl top pod -n production`

**Screenshots:** `.playwright-mcp/k8s-mcp-evidence.png`

### Proof #2: AI Agent Settings Persistence

**Settings Verified in UI:**
- Mode: **Approval Mode** (Active)
- Confidence Threshold: **70%**
- Risk Matrix: Low (5 auto), Medium (5 approval), High (5 approval)

**Applied to Agent Processing:**
- `'ai_mode': 'plan'` - Confirms Approval Mode is active
- `'auto_remediation_enabled': False` - Agent respects settings
- Actions generated but NOT auto-executed (per Approval Mode)

**Recent Configuration Changes Audit Trail:**
- "Mode changed to approval" - Just now
- "Confidence threshold updated to 70%" - 2 minutes ago

**Screenshots:** `.playwright-mcp/ai-agents-settings-proof.png`

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
3. ~~**Backup files to clean**: `agent.py.bak`, `uv.lock.bak`~~ ✅ Cleaned
4. ~~**Database persistence**: PhonePe service TODOs for database storage~~ ✅ PhonePe removed
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

## Phase 3: Future Enhancements (Post-Demo)

### Priority 1: Advanced Integrations
- [ ] Runbook integration (auto-suggest runbooks based on incident type)
- [ ] Teams notifications (in addition to Slack)
- [ ] Incident correlation (group related incidents)
- [ ] SLA tracking and alerting
- [ ] Custom remediation playbooks

### Priority 2: DevOps & Infrastructure
- [ ] Set up proper CI/CD with staging environment
- [ ] Implement blue-green deployments
- [ ] Add rate limiting on webhook endpoints
- [ ] SSE disconnection recovery

### Priority 3: AI Enhancements
- [ ] Learn from resolved incidents (feedback loop)
- [ ] Custom AI prompts per team/service
- [ ] Confidence threshold tuning
- [ ] Multi-language support for notifications

---

*Last Updated: 2025-11-28*
