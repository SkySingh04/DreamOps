# AI Assistant Instructions for Oncall Agent Codebase

This document provides comprehensive instructions for AI assistants (like Claude, GPT-4, etc.) on how to effectively work with this codebase.

## Project Overview

This is an oncall AI agent built with:
- **AGNO Framework**: For building AI agents
- **Claude API**: For intelligent incident analysis
- **MCP (Model Context Protocol)**: For integrating with external tools
- **FastAPI**: Web framework for the REST API
- **Python AsyncIO**: For concurrent operations
- **uv**: For package management

## Key Architecture Decisions

1. **Modular MCP Integrations**: All integrations extend `MCPIntegration` base class in `src/oncall_agent/mcp_integrations/base.py`
2. **Async-First**: All operations are async to handle concurrent MCP calls efficiently
3. **Configuration-Driven**: Uses pydantic for config validation and environment variables
4. **Type-Safe**: Extensive use of type hints throughout the codebase
5. **Retry Logic**: Built-in exponential backoff for network operations (configurable via MCP_MAX_RETRIES)
6. **Singleton Config**: Global configuration instance accessed via `get_config()`

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
│   │   ├── github_mcp.py    # GitHub integration
│   │   └── notion_direct.py # Notion integration
│   └── strategies/          # Resolution strategies
│       └── kubernetes_resolver.py
├── tests/                    # All test files
├── examples/                 # Example scripts
├── scripts/                  # Utility scripts
├── main.py                   # CLI entry point
└── Dockerfile.prod          # Production Docker image
```

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
4. **`src/oncall_agent/api.py`**: FastAPI application with REST endpoints
5. **`main.py`**: Entry point showing how to use the agent

## Commands and Development Workflow

### Development Commands
- **Install dependencies**: `uv sync`
- **Run the agent**: `uv run python main.py`
- **Add dependency**: `uv add <package>`
- **Add dev dependency**: `uv add --dev <package>`

### Testing and Validation
- **Run demo**: `uv run python main.py`
- **Run API server**: `uv run uvicorn src.oncall_agent.api:app --reload`
- **Run tests**: `uv run pytest tests/`
- **Run linter**: `uv run ruff check . --fix`
- **Run type checker**: `uv run mypy . --ignore-missing-imports`

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

## API Development

The project includes a FastAPI REST API in `src/oncall_agent/api.py`:

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

### GitHub Secrets Required
1. `AWS_ACCESS_KEY_ID` - AWS access key for deployment
2. `AWS_SECRET_ACCESS_KEY` - AWS secret key
3. `ANTHROPIC_API_KEY` - Your Anthropic API key
4. `CLOUDFRONT_DISTRIBUTION_ID` - CloudFront ID (after initial deployment)
5. `REACT_APP_API_URL` - Backend API URL (after initial deployment)

## MCP Integration Interface

Every MCP integration must implement these methods from the base class:
- `async def connect()`: Establish connection to the service
- `async def disconnect()`: Gracefully close connections
- `async def fetch_context(params: Dict[str, Any])`: Retrieve information
- `async def execute_action(action: str, params: Dict[str, Any])`: Perform remediation
- `def get_capabilities() -> List[str]`: List available actions
- `async def health_check() -> bool`: Verify connection status

## Kubernetes Integration

The Kubernetes MCP integration (`src/oncall_agent/mcp_integrations/kubernetes.py`) provides:

### Features
- Pod management (list, logs, describe, restart)
- Deployment operations (status, scale, rollback)
- Service monitoring
- Event retrieval
- Automated resolution strategies

### Alert Pattern Detection
The agent detects these Kubernetes patterns:
- `pod_crash`: CrashLoopBackOff, crash, restarting
- `image_pull`: ImagePullBackOff, ErrImagePull
- `oom`: OOMKilled, memory exceeded
- `cpu_throttle`: CPU usage threshold exceeded
- `service_down`: Service unavailable
- `deployment_failed`: Deployment issues
- `node_issue`: Node problems

### Testing with EKS
For testing with AWS EKS cluster:
```bash
cd infrastructure/eks
terraform init
terraform apply
./deploy-sample-apps.sh
```

## GitHub Integration

The GitHub MCP integration (`src/oncall_agent/mcp_integrations/github_mcp.py`) provides:

### Features
- Context gathering: Fetches recent commits, issues, PRs, and GitHub Actions runs
- Issue management: Creates incident issues for high-severity alerts
- Repository mapping: Maps service names to GitHub repositories
- Workflow monitoring: Checks GitHub Actions status

### Configuration
Required environment variables:
- `GITHUB_TOKEN`: GitHub Personal Access Token
- `GITHUB_MCP_SERVER_PATH`: Path to GitHub MCP server binary
- `GITHUB_MCP_HOST`: Host for MCP server (default: localhost)
- `GITHUB_MCP_PORT`: Port for MCP server (default: 8081)

## Debugging Tips

1. Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging
2. Check agent state with `agent.mcp_integrations` dictionary
3. Use `agent.health_check()` on integrations to verify connectivity
4. For API issues, check FastAPI logs and use the `/docs` endpoint

## High-Level Flow

1. **Alert Reception**: `OncallAgent.handle_pager_alert()` receives a PagerAlert
2. **Pattern Detection**: Agent checks for Kubernetes-specific patterns
3. **Context Gathering**: Agent queries all registered MCP integrations
4. **Claude Analysis**: Sends alert + context to Claude for analysis
5. **Response Generation**: Returns structured incident analysis with:
   - Severity assessment
   - Root cause analysis
   - Impact assessment
   - Recommended actions
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

## Dependencies and Tools

- **uv**: Package manager (use `uv add <package>` to add dependencies)
- **AGNO**: Agent framework (check their docs for advanced features)
- **Anthropic**: Claude API client
- **Pydantic**: Data validation and settings
- **aiohttp**: HTTP client for MCP server communication
- **FastAPI**: Web framework for the REST API
- **uvicorn**: ASGI server for running FastAPI
- **kubernetes**: Python client for Kubernetes API
- **httpx**: Modern HTTP client
- **pytest**: Testing framework
- **ruff**: Fast Python linter
- **mypy**: Static type checker

## Important Notes

1. **Test files location**: All test files should be in the `tests/` directory
2. **Example scripts**: Demo and example scripts go in `examples/`
3. **Utility scripts**: Helper scripts go in `scripts/`
4. **Always run validation**: Use `./scripts/validate.sh` before committing
5. **Docker support**: Production Dockerfile is `Dockerfile.prod`
6. **Environment variables**: All config should be in `.env`, never hardcode
7. **Async everywhere**: All I/O operations must be async
8. **Type hints required**: All new functions need type annotations
9. **Error handling**: Always log errors with context
10. **Documentation**: Update README.md for any user-facing changes