# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an oncall AI agent built with:
- **AGNO Framework**: For building AI agents
- **Claude API**: For intelligent incident analysis
- **MCP (Model Context Protocol)**: For integrating with external tools
- **GitHub MCP Server**: For GitHub API integration via MCP
- **Python AsyncIO**: For concurrent operations
- **uv**: For package management

## Key Architecture Decisions

1. **Modular MCP Integrations**: All integrations extend `MCPIntegration` base class in `src/oncall_agent/mcp_integrations/base.py`
2. **Async-First**: All operations are async to handle concurrent MCP calls efficiently
3. **Configuration-Driven**: Uses pydantic for config validation and environment variables
4. **Type-Safe**: Extensive use of type hints throughout the codebase
5. **Retry Logic**: Built-in exponential backoff for network operations (configurable via MCP_MAX_RETRIES)
6. **Singleton Config**: Global configuration instance accessed via `get_config()`

## Working with the Codebase

### When Adding New MCP Integrations

1. **Always extend the base class**:
   ```python
   from src.oncall_agent.mcp_integrations.base import MCPIntegration
   ```

2. **Follow the established pattern**:
   - Implement all abstract methods
   - Use the retry mechanism for network operations
   - Log all operations appropriately
   - Handle errors gracefully

3. **File location**: Create new integrations in `src/oncall_agent/mcp_integrations/`

### Code Style Guidelines

- Use descriptive variable names
- Add type hints to all functions
- Include docstrings for all public methods
- Follow PEP 8 conventions
- Use `async/await` for all I/O operations

### Common Patterns in This Codebase

1. **Error Handling**:
   ```python
   try:
       result = await operation()
   except Exception as e:
       self.logger.error(f"Operation failed: {e}")
       return {"error": str(e)}
   ```

2. **Configuration Access**:
   ```python
   from src.oncall_agent.config import get_config
   config = get_config()
   ```

3. **Logging**:
   ```python
   from src.oncall_agent.utils import get_logger
   logger = get_logger(__name__)
   ```

## Important Files to Understand

1. **`src/oncall_agent/agent.py`**: Core agent logic, study this to understand the main flow
2. **`src/oncall_agent/mcp_integrations/base.py`**: Base class defining the MCP interface
3. **`src/oncall_agent/config.py`**: Configuration schema and defaults
4. **`main.py`**: Entry point showing how to use the agent

## Testing Approach

When asked to test changes:
1. Check if `.env` exists, if not copy from `.env.example`
2. Ensure `ANTHROPIC_API_KEY` is set
3. Run with: `uv run python main.py`
4. For specific integrations, create mock implementations first

## Common Tasks

### Adding a New MCP Integration
1. Create file in `src/oncall_agent/mcp_integrations/`
2. Extend `MCPIntegration` base class
3. Implement all abstract methods
4. Add configuration to `.env.example`
5. Update README.md with usage instructions

### Modifying Alert Handling
1. Look at `PagerAlert` model in `agent.py`
2. Modify `handle_pager_alert` method
3. Update the prompt sent to Claude if needed

### Adding New Configuration Options
1. Add to `Config` class in `config.py`
2. Add to `.env.example` with description
3. Document in README.md

## Commands

### Development Commands
- **Install dependencies**: `uv sync`
- **Run the agent**: `uv run python main.py`
- **Add dependency**: `uv add <package>`
- **Add dev dependency**: `uv add --dev <package>`
- **Check environment**: `uv run python test_run.py`

### Testing and Validation
- **Run demo**: `uv run python main.py` (runs a simulated alert through the agent)
- **Validate setup**: `uv run python test_run.py` (checks Python version, packages, env vars)
- **Run API server**: `uv run uvicorn src.oncall_agent.api:app --reload` (starts FastAPI server)
- **Run tests**: `uv run pytest tests/` (runs all tests)
- **Run linter**: `uv run ruff check .` (checks code style)
- **Run type checker**: `uv run mypy . --ignore-missing-imports` (checks type annotations)

### IMPORTANT: Pre-commit Checklist
**ALWAYS run these commands before finishing any task:**
```bash
# 1. Run linter and fix any issues
uv run ruff check . --fix

# 2. Run type checker
uv run mypy . --ignore-missing-imports

# 3. Run all tests
uv run pytest tests/

# 4. Verify the application still runs
uv run python main.py
```

If any of these fail, fix the issues before considering the task complete.

## Dependencies and Tools

- **uv**: Package manager (use `uv add <package>` to add dependencies)
- **AGNO**: Agent framework (check their docs for advanced features)
- **Anthropic**: Claude API client
- **Pydantic**: Data validation and settings
- **aiohttp**: HTTP client for MCP server communication
- **FastAPI**: Web framework for the REST API
- **uvicorn**: ASGI server for running FastAPI

## GitHub MCP Integration

The GitHub MCP integration (`src/oncall_agent/mcp_integrations/github_mcp.py`) provides:

### Features
- **Context Gathering**: Fetches recent commits, open issues, PR status, and GitHub Actions runs
- **Issue Management**: Automatically creates incident issues for high-severity alerts
- **Repository Mapping**: Maps service names to GitHub repositories
- **GitHub Actions Integration**: Monitors workflow status and can trigger deployments

### Configuration
Required environment variables:
- `GITHUB_TOKEN`: GitHub Personal Access Token with appropriate permissions
- `GITHUB_MCP_SERVER_PATH`: Path to the GitHub MCP server binary (default: ../github-mcp-server/github-mcp-server)
- `GITHUB_MCP_HOST`: Host for MCP server (default: localhost)  
- `GITHUB_MCP_PORT`: Port for MCP server (default: 8080)

### Usage
The integration is automatically registered when `GITHUB_TOKEN` is configured. It:
1. Starts the GitHub MCP server process
2. Connects via HTTP client
3. Fetches context for alerts based on service-to-repository mapping
4. Creates incident issues for high-severity alerts
5. Provides GitHub context to Claude for analysis

### Testing
Run `python test_github_integration.py` to test the integration.

## API Development

The project now includes a FastAPI REST API in `src/oncall_agent/api.py`:

### API Endpoints
- `GET /health` - Health check endpoint
- `POST /alerts` - Submit new alerts for processing
- `GET /alerts/{alert_id}` - Get alert details (placeholder)
- `GET /integrations` - List available MCP integrations
- `POST /integrations/{name}/health` - Check specific integration health

### Running the API
```bash
# Development with auto-reload
uv run uvicorn src.oncall_agent.api:app --reload

# Production
uv run uvicorn src.oncall_agent.api:app --host 0.0.0.0 --port 8000
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Deployment

The project includes comprehensive AWS deployment configuration:

### Infrastructure
- **Backend**: ECS Fargate with ALB
- **Frontend**: S3 + CloudFront
- **Monitoring**: CloudWatch dashboards and alarms
- **Security**: Secrets Manager for sensitive data

### CI/CD Pipelines
- **Backend**: `.github/workflows/backend-ci.yml`
- **Frontend**: `.github/workflows/frontend-ci.yml`
- **Security**: `.github/workflows/security-scan.yml`

See [DEPLOYMENT.md](../DEPLOYMENT.md) for detailed instructions.

## Debugging Tips

1. Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging
2. Check agent state with `agent.mcp_integrations` dictionary
3. Use `agent.health_check()` on integrations to verify connectivity
4. For API issues, check FastAPI logs and use the `/docs` endpoint

## MCP Integration Interface

Every MCP integration must implement these methods from the base class:
- `async def connect()`: Establish connection to the service
- `async def disconnect()`: Gracefully close connections
- `async def fetch_context(params: Dict[str, Any])`: Retrieve information
- `async def execute_action(action: str, params: Dict[str, Any])`: Perform remediation
- `def get_capabilities() -> List[str]`: List available actions
- `async def health_check() -> bool`: Verify connection status

## High-Level Flow

1. **Alert Reception**: `OncallAgent.handle_pager_alert()` receives a PagerAlert
2. **Context Gathering**: Agent queries all registered MCP integrations for context
3. **Claude Analysis**: Sends alert + context to Claude for intelligent analysis
4. **Response Generation**: Returns structured incident analysis with:
   - Severity assessment
   - Root cause analysis
   - Impact assessment
   - Recommended actions (both immediate and follow-up)
   - Monitoring suggestions

## Future Architecture Considerations

The codebase is designed to support:
- Multiple alert sources (not just pagers)
- Different LLM backends (not just Claude)
- Plugin-based remediation actions
- Distributed agent deployment

When making changes, keep these future directions in mind.

## Questions to Ask When Working on This Codebase

1. Is this operation async? (It probably should be)
2. Does this need retry logic? (Network operations do)
3. Is this configuration that should be in `.env`?
4. Have I added appropriate logging?
5. Have I updated the README for user-facing changes?

## Common Pitfalls to Avoid

1. Don't make synchronous network calls
2. Don't hardcode configuration values
3. Don't forget to validate connection state before operations
4. Don't catch exceptions without logging them
5. Don't forget to update type hints when changing function signatures
6. Don't skip running tests and linters before committing
7. Don't commit without checking `uv run ruff check .` passes
8. Don't deploy without running the full test suite
9. Don't expose API keys or secrets in code or logs
10. Don't forget to update API documentation when adding endpoints