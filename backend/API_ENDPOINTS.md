# OnCall Agent API Endpoints Documentation

This document provides a comprehensive overview of all available API endpoints in the OnCall Agent backend.

## Base URL
- Development: `http://localhost:8000`
- Production: `https://api.oncall-agent.example.com`

## API Version
All endpoints (except webhooks) are prefixed with `/api/v1`

## Authentication
Currently using API key authentication (to be implemented). Include the API key in the `X-API-Key` header.

## Endpoints Overview

### 1. Dashboard (`/api/v1/dashboard`)
Real-time metrics and statistics for the dashboard view.

- `GET /api/v1/dashboard/stats` - Get dashboard statistics overview
- `GET /api/v1/dashboard/metrics/incidents?period=24h` - Get incident trend metrics
- `GET /api/v1/dashboard/metrics/resolution-time?period=24h` - Get MTTR metrics
- `GET /api/v1/dashboard/metrics/automation` - Get automation success rate
- `GET /api/v1/dashboard/activity-feed?limit=20` - Get recent activity feed
- `GET /api/v1/dashboard/top-services?limit=5` - Get top affected services
- `GET /api/v1/dashboard/severity-distribution` - Get incident severity distribution

### 2. Incidents (`/api/v1/incidents`)
Complete incident management functionality.

- `POST /api/v1/incidents` - Create a new incident
- `GET /api/v1/incidents?page=1&page_size=20&status=triggered&severity=high` - List incidents with filtering
- `GET /api/v1/incidents/{incident_id}` - Get incident details
- `PATCH /api/v1/incidents/{incident_id}` - Update incident
- `POST /api/v1/incidents/{incident_id}/actions` - Execute action on incident
- `GET /api/v1/incidents/{incident_id}/timeline` - Get incident timeline
- `GET /api/v1/incidents/{incident_id}/related?limit=5` - Get related incidents
- `POST /api/v1/incidents/{incident_id}/acknowledge?user=email` - Acknowledge incident
- `POST /api/v1/incidents/{incident_id}/resolve?resolution=...&user=email` - Resolve incident

### 3. AI Agent (`/api/v1/agent`)
AI agent control and monitoring.

- `GET /api/v1/agent/status` - Get AI agent system status
- `POST /api/v1/agent/analyze` - Manually trigger AI analysis
- `GET /api/v1/agent/capabilities` - Get agent capabilities
- `GET /api/v1/agent/knowledge-base?query=...&limit=10` - Search knowledge base
- `GET /api/v1/agent/learning-metrics` - Get learning/improvement metrics
- `POST /api/v1/agent/feedback?incident_id=...&helpful=true&accuracy=5` - Submit feedback
- `GET /api/v1/agent/prompts` - Get agent prompt templates

### 4. Integrations (`/api/v1/integrations`)
Manage external service integrations.

- `GET /api/v1/integrations` - List all integrations
- `GET /api/v1/integrations/{name}` - Get integration details
- `PUT /api/v1/integrations/{name}/config` - Update integration config
- `POST /api/v1/integrations/{name}/test` - Test integration connection
- `GET /api/v1/integrations/{name}/metrics?period=1h` - Get integration metrics
- `POST /api/v1/integrations/{name}/sync` - Manually sync integration
- `GET /api/v1/integrations/{name}/logs?limit=100&level=error` - Get integration logs
- `GET /api/v1/integrations/available` - Get available integrations to add

### 5. Analytics (`/api/v1/analytics`)
Reporting and analytics endpoints.

- `POST /api/v1/analytics/incidents` - Get incident analytics (with time range)
- `GET /api/v1/analytics/services/health?days=7` - Get service health metrics
- `GET /api/v1/analytics/patterns?days=30&min_occurrences=3` - Identify incident patterns
- `GET /api/v1/analytics/slo-compliance?service=api-gateway` - Get SLO compliance
- `GET /api/v1/analytics/cost-impact?days=30` - Estimate incident cost impact
- `GET /api/v1/analytics/team-performance?days=30` - Get team performance metrics
- `GET /api/v1/analytics/predictions` - Get AI-based predictions
- `POST /api/v1/analytics/reports/generate?report_type=executive` - Generate report

### 6. Security & Audit (`/api/v1/security`)
Security, compliance, and audit trail.

- `GET /api/v1/security/audit-logs?page=1&action=...&user=...` - Get audit logs
- `GET /api/v1/security/audit-logs/export?format=csv` - Export audit logs
- `GET /api/v1/security/permissions?user_email=...` - Get user permissions
- `GET /api/v1/security/access-logs?limit=100` - Get API access logs
- `GET /api/v1/security/security-events?severity=high&days=7` - Get security events
- `POST /api/v1/security/rotate-api-key?service=github` - Rotate API keys
- `GET /api/v1/security/compliance-report` - Get compliance report
- `GET /api/v1/security/threat-detection` - Get threat detection status

### 7. Monitoring (`/api/v1/monitoring`)
Live monitoring, logs, and metrics.

- `GET /api/v1/monitoring/logs?level=error&source=api&limit=100` - Get system logs
- `GET /api/v1/monitoring/logs/stream` - Stream logs (Server-Sent Events)
- `WS /api/v1/monitoring/ws/metrics` - WebSocket for real-time metrics
- `GET /api/v1/monitoring/metrics` - Get current system metrics
- `GET /api/v1/monitoring/status` - Get overall system status
- `GET /api/v1/monitoring/traces?service=...&duration_min=100` - Get distributed traces
- `GET /api/v1/monitoring/alerts/active` - Get active monitoring alerts
- `GET /api/v1/monitoring/profiling?service=...&type=cpu` - Get profiling data

### 8. Settings (`/api/v1/settings`)
System configuration and settings.

- `GET /api/v1/settings` - Get all settings
- `PUT /api/v1/settings` - Update all settings
- `GET /api/v1/settings/notifications` - Get notification settings
- `PUT /api/v1/settings/notifications` - Update notification settings
- `GET /api/v1/settings/automation` - Get automation settings
- `PUT /api/v1/settings/automation` - Update automation settings
- `GET /api/v1/settings/escalation-policies` - Get escalation policies
- `GET /api/v1/settings/oncall-schedules` - Get on-call schedules
- `GET /api/v1/settings/templates` - Get incident response templates
- `GET /api/v1/settings/knowledge-base` - Get knowledge base config
- `POST /api/v1/settings/backup` - Create settings backup
- `POST /api/v1/settings/restore/{backup_id}` - Restore from backup

### 9. Webhooks (`/webhook`)
External webhook endpoints (no API version prefix).

- `POST /webhook/pagerduty` - PagerDuty webhook receiver
- `GET /webhook/pagerduty/status` - Get webhook processing status
- `POST /webhook/pagerduty/test` - Test webhook configuration

## Common Response Formats

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {}
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "details": {},
  "request_id": "req-123"
}
```

### Paginated Response
```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_next": true
}
```

## WebSocket Connection

For real-time metrics monitoring:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/monitoring/ws/metrics');
ws.onmessage = (event) => {
  const metrics = JSON.parse(event.data);
  console.log('Received metrics:', metrics);
};
```

## Server-Sent Events

For log streaming:

```javascript
const eventSource = new EventSource('/api/v1/monitoring/logs/stream?level=error');
eventSource.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log('New log entry:', log);
};
```

## Rate Limiting

- Default: 1000 requests per hour per API key
- Webhooks: 10000 requests per hour
- WebSocket connections: 10 concurrent connections per API key

## Error Codes

- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing or invalid API key)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error
- `503` - Service Unavailable

## Notes

1. All timestamps are in ISO 8601 format with UTC timezone
2. All endpoints support CORS for browser-based access
3. Large responses support pagination via `page` and `page_size` parameters
4. Filtering is supported via query parameters on list endpoints
5. The API supports both JSON request/response bodies
6. File exports (audit logs, reports) return download URLs valid for 24 hours