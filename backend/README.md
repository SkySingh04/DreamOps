# Oncall AI Agent - Backend

This is the backend service for the Oncall AI Agent, built with Python and the AGNO framework.

## Prerequisites

- Python 3.11+
- uv package manager
- Anthropic API key

## Setup

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

## API Endpoints (Coming Soon)

The backend will expose REST API endpoints for:
- `/api/alerts` - Receive and process alerts
- `/api/incidents` - Incident history and management
- `/api/integrations` - MCP integration status
- `/api/config` - Agent configuration

## Environment Variables

See `.env.example` for all available configuration options.