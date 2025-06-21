# OnCall Agent API Quick Start Guide

## Starting the API Server

1. **Start the backend API server:**
   ```bash
   cd backend
   uv run python api_server.py
   ```

2. **The API will be available at:** `http://localhost:8000`

3. **API Documentation:**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## Testing the API

1. **Run the test script:**
   ```bash
   cd backend
   uv run python scripts/test_api_endpoints.py
   ```

2. **Manual testing with curl:**

   ```bash
   # Get dashboard stats
   curl http://localhost:8000/api/v1/dashboard/stats

   # Create an incident
   curl -X POST http://localhost:8000/api/v1/incidents \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Database Connection Error",
       "description": "Unable to connect to primary database",
       "severity": "high",
       "service_name": "user-service",
       "alert_source": "manual"
     }'

   # Get AI agent status
   curl http://localhost:8000/api/v1/agent/status

   # List integrations
   curl http://localhost:8000/api/v1/integrations
   ```

## Frontend Integration

The frontend can now use these endpoints:

```javascript
// Example: Fetch dashboard stats
const response = await fetch('http://localhost:8000/api/v1/dashboard/stats');
const stats = await response.json();

// Example: Create incident
const incident = await fetch('http://localhost:8000/api/v1/incidents', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    title: 'API Error',
    description: 'High error rate detected',
    severity: 'high',
    service_name: 'api-gateway',
    alert_source: 'prometheus'
  })
});

// Example: WebSocket for real-time metrics
const ws = new WebSocket('ws://localhost:8000/api/v1/monitoring/ws/metrics');
ws.onmessage = (event) => {
  const metrics = JSON.parse(event.data);
  updateDashboard(metrics);
};
```

## Key Endpoints for Frontend

### Dashboard Page
- `GET /api/v1/dashboard/stats` - Main statistics
- `GET /api/v1/dashboard/metrics/incidents?period=24h` - Incident trends
- `GET /api/v1/dashboard/activity-feed` - Recent activities
- `WebSocket /api/v1/monitoring/ws/metrics` - Real-time metrics

### Incidents Page
- `GET /api/v1/incidents` - List all incidents
- `POST /api/v1/incidents` - Create new incident
- `PATCH /api/v1/incidents/{id}` - Update incident
- `POST /api/v1/incidents/{id}/acknowledge` - Acknowledge
- `POST /api/v1/incidents/{id}/resolve` - Resolve

### AI Agent Page
- `GET /api/v1/agent/status` - Agent health
- `POST /api/v1/agent/analyze` - Trigger analysis
- `GET /api/v1/agent/capabilities` - Available actions

### Integrations Page
- `GET /api/v1/integrations` - List all integrations
- `PUT /api/v1/integrations/{name}/config` - Update config
- `POST /api/v1/integrations/{name}/test` - Test connection

### Analytics Page
- `POST /api/v1/analytics/incidents` - Incident analytics
- `GET /api/v1/analytics/services/health` - Service health
- `GET /api/v1/analytics/patterns` - Incident patterns

### Settings Page
- `GET /api/v1/settings` - All settings
- `PUT /api/v1/settings/notifications` - Update notifications
- `GET /api/v1/settings/oncall-schedules` - On-call schedules

## Mock Data

The API includes comprehensive mock data for development:
- Pre-populated incidents with various severities
- Mock AI analysis responses
- Simulated real-time metrics
- Example integration configurations
- Sample audit logs and security events

## Environment Variables

Make sure these are set in your `.env` file:

```env
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]
```

## Next Steps

1. Update the frontend to use these new endpoints
2. Add authentication middleware (API keys or JWT)
3. Implement rate limiting
4. Add request/response validation
5. Set up proper error handling
6. Configure CORS for production