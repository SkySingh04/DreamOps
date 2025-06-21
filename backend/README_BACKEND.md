# Oncall AI Agent - Backend

This is the backend component of the Oncall AI Agent system.

## Quick Start

1. Install dependencies:
```bash
uv sync
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run the demo:
```bash
uv run python main.py
```

4. Start API server:
```bash
uv run uvicorn src.oncall_agent.api:app --reload
```

## ⚠️ Development Requirements

**ALWAYS run these commands before finishing any task:**

```bash
# 1. Fix code style issues
uv run ruff check . --fix

# 2. Check type annotations
uv run mypy . --ignore-missing-imports

# 3. Run all tests
uv run pytest tests/

# 4. Verify the application still runs
uv run python main.py
```

If any of these fail, you MUST fix the issues before considering your task complete.

## Project Structure

```
backend/
├── src/oncall_agent/
│   ├── agent.py              # Core agent logic
│   ├── api.py                # FastAPI REST API
│   ├── config.py             # Configuration management
│   ├── mcp_integrations/     # MCP integration modules
│   │   ├── base.py          # Base integration class
│   │   ├── kubernetes.py    # Kubernetes integration
│   │   └── github_mcp.py    # GitHub integration
│   └── strategies/          # Resolution strategies
│       └── kubernetes_resolver.py
├── main.py                   # CLI entry point
├── demo_k8s_debug.py        # Kubernetes demo
├── test_all_scenarios.py    # Scenario testing
└── Dockerfile.prod          # Production Docker image
```

## API Documentation

When running the API server, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### API Endpoints

- `POST /alerts` - Submit a new alert for processing
- `GET /health` - Health check endpoint
- `GET /integrations` - List available MCP integrations
- `POST /integrations/{name}/health` - Check integration health

## MCP Integrations

### Available Integrations

1. **Kubernetes** - Debugs pod crashes, OOM issues, and config problems
2. **GitHub** - Fetches context from repositories and creates incident issues

### Adding New Integrations

1. Create a new file in `src/oncall_agent/mcp_integrations/`
2. Extend the `MCPIntegration` base class
3. Implement all required methods
4. Add configuration to `.env.example`
5. Update documentation

See [CLAUDE.md](CLAUDE.md) for detailed integration guidelines.

## Testing

```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_kubernetes_integration.py

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## Docker

### Development
```bash
docker build -t oncall-agent .
docker run -it --env-file .env oncall-agent
```

### Production
```bash
docker build -t oncall-agent -f Dockerfile.prod .
docker run -p 8000:8000 --env-file .env oncall-agent
```

## Configuration

Key environment variables:

- `ANTHROPIC_API_KEY` - Required for Claude AI
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `K8S_ENABLED` - Enable Kubernetes integration
- `GITHUB_TOKEN` - GitHub personal access token

See `.env.example` for full configuration options.

## Development Guidelines

1. **Async First**: All I/O operations should be async
2. **Type Safety**: Add type hints to all functions
3. **Error Handling**: Log errors appropriately
4. **Testing**: Write tests for new features
5. **Documentation**: Update docs when adding features

## Debugging

1. Set `LOG_LEVEL=DEBUG` for verbose logging
2. Use `import pdb; pdb.set_trace()` for breakpoints
3. Check logs in CloudWatch for production issues

## Contributing

1. Create a feature branch
2. Make changes
3. **Run all tests and linters** (see Development Requirements)
4. Submit PR with clear description
5. Ensure CI/CD checks pass

## AI Assistant Instructions

See [CLAUDE.md](CLAUDE.md) for instructions when using AI assistants to work on this codebase.