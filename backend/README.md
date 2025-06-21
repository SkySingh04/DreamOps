# Oncall AI Agent Backend

AI-powered oncall agent for automated incident response.

## Features

- FastAPI-based REST API
- PagerDuty webhook integration
- Kubernetes cluster monitoring
- MCP (Model Context Protocol) integrations
- Real-time incident analysis and response

## Setup

```bash
# Install dependencies
uv sync

# Run the API server
uv run python api_server.py
```

## API Endpoints

- `GET /health` - Health check
- `POST /webhooks/pagerduty` - PagerDuty webhook endpoint
- `GET /api/v1/incidents` - List incidents
- `GET /api/v1/dashboard` - Dashboard data

## Environment Variables

- `ANTHROPIC_API_KEY` - Claude API key
- `PAGERDUTY_ROUTING_KEY` - PagerDuty integration key
- `K8S_CONFIG_PATH` - Kubernetes config file path