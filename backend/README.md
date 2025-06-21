# Oncall AI Agent - Backend

This is the backend service for the Oncall AI Agent, built with Python and the AGNO framework.

## Prerequisites

- Python 3.11+
- uv package manager
- Anthropic API key

## Setup

### Quick Start (Without Kubernetes)
```bash
# Simple setup for testing PagerDuty integration
./quick_test_pagerduty.sh
```
See [PAGERDUTY-QUICK-START.md](PAGERDUTY-QUICK-START.md) for details.

### Full Setup
1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

3. Run the agent:
   ```bash
   uv run python main.py
   ```

## Development

### Running Tests
```bash
uv run python test_run.py  # Environment validation
```

### Adding New MCP Integrations

1. Create a new file in `src/oncall_agent/mcp_integrations/`
2. Extend the `MCPIntegration` base class
3. Implement all required methods
4. Register the integration in your agent setup

See CLAUDE.md for detailed development guidelines.

## API Server

### Running the API Server

The backend now includes a FastAPI server with PagerDuty webhook support:

```bash
# Run the API server
uv run python api_server.py

# Or run with auto-reload for development
API_RELOAD=true uv run python api_server.py
```

### API Endpoints

- `GET /` - Service info and status
- `GET /health` - Health check endpoint
- `POST /webhook/pagerduty` - PagerDuty webhook receiver
- `GET /webhook/pagerduty/status` - Webhook processing status

## PagerDuty Integration

### Configuration

1. Add PagerDuty settings to your `.env`:
   ```bash
   # Required for webhook signature verification (optional but recommended)
   PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret-here
   
   # Optional PagerDuty API key for future features
   PAGERDUTY_API_KEY=your-api-key-here
   ```

2. Configure PagerDuty webhook:
   - In PagerDuty, go to Integrations → Generic Webhooks (v3)
   - Add webhook URL: `https://your-domain.com/webhook/pagerduty`
   - Copy the signature key to `PAGERDUTY_WEBHOOK_SECRET`

### Features

- **Automatic Alert Processing**: Incident.triggered events automatically trigger the AI agent
- **Context Extraction**: Parses technical details from alerts (error codes, metrics, etc.)
- **Alert Classification**: Automatically categorizes alerts (database, server, security, network, kubernetes)
- **Concurrent Processing**: Handles multiple alerts efficiently with queuing
- **Webhook Security**: Validates PagerDuty signatures when configured

### Testing PagerDuty Integration

Use the included test generator to verify your setup:

```bash
# Test a single alert
uv run python test_pagerduty_alerts.py

# Test specific alert type
uv run python test_pagerduty_alerts.py --type database

# Test all alert types
uv run python test_pagerduty_alerts.py --all

# Send batch of alerts
uv run python test_pagerduty_alerts.py --batch 5

# Stress test
uv run python test_pagerduty_alerts.py --stress 30 --rate 2.0
```

### Kubernetes Integration Testing

For end-to-end testing with a real Kubernetes cluster:

1. **Set up Kind cluster** (see [README-KIND-SETUP.md](README-KIND-SETUP.md))
2. **Deploy demo apps**: `./setup-k8s-demo.sh`
3. **Monitor and send alerts**: `uv run python test_k8s_pagerduty_integration.py`

This creates real Kubernetes failures and tests the complete flow from K8s → PagerDuty webhook → Oncall Agent → Claude analysis.

### Alert Processing Flow

1. PagerDuty sends webhook to `/webhook/pagerduty`
2. Alert context is extracted and enriched
3. OncallAgent analyzes the incident with Claude
4. Agent returns:
   - Root cause analysis
   - Immediate mitigation steps
   - Long-term recommendations
   - Monitoring suggestions
- `/api/config` - Agent configuration

## Environment Variables

See `.env.example` for all available configuration options.