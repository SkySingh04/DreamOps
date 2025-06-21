# AI Assistant Instructions for Oncall Agent Codebase

This document provides comprehensive instructions for AI assistants (like Claude, GPT-4, etc.) on how to effectively work with this codebase.

## Project Overview

This is an oncall AI agent built with:
- **AGNO Framework**: For building AI agents
- **Claude API**: For intelligent incident analysis
- **MCP (Model Context Protocol)**: For integrating with external tools
- **FastAPI**: Web framework for the REST API and webhooks
- **Python AsyncIO**: For concurrent operations
- **uv**: For package management
- **Next.js**: Frontend SaaS interface
- **Terraform**: AWS infrastructure deployment

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

### Testing Kubernetes Alerting
The project includes `fuck_kubernetes.sh` for simulating Kubernetes failures:

```bash
# Usage from project root
./fuck_kubernetes.sh [1-5|all|random|clean]

# Simulates:
# 1 - Pod crashes (CrashLoopBackOff)
# 2 - Image pull errors (ImagePullBackOff)  
# 3 - OOM kills
# 4 - Deployment failures
# 5 - Service unavailability

# The script:
# - Creates issues in 'fuck-kubernetes-test' namespace
# - Triggers CloudWatch alarms within 60 seconds
# - Sends alerts through SNS → PagerDuty → Slack
# - Helps verify the entire alerting pipeline
```

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

### 🚀 Automatic Server Management

**IMPORTANT**: The GitHub MCP server starts automatically - no manual setup required!

The integration features complete automatic server lifecycle management:

1. **Auto-Start**: When `GitHubMCPIntegration.connect()` is called:
   ```python
   # This happens automatically:
   await self._start_mcp_server()  # Starts subprocess
   await self._initialize_mcp_client()  # Creates HTTP client  
   await self._test_connection()  # Verifies connectivity
   ```

2. **Process Management**: 
   - Starts `github-mcp-server stdio` as subprocess
   - Passes `GITHUB_PERSONAL_ACCESS_TOKEN` via environment
   - Waits 2 seconds for server initialization
   - Performs health checks via MCP protocol

3. **Auto-Cleanup**: On shutdown:
   - Gracefully terminates server process
   - Kills process if needed
   - Cleans up all resources

### Features
- Context gathering: Fetches recent commits, issues, PRs, and GitHub Actions runs
- Issue management: Creates incident issues for high-severity alerts
- Repository mapping: Maps service names to GitHub repositories
- Workflow monitoring: Checks GitHub Actions status
- **Zero manual server management**: Fully automated startup and cleanup

### Configuration
Required environment variables:
- `GITHUB_TOKEN`: GitHub Personal Access Token
- `GITHUB_MCP_SERVER_PATH`: Path to GitHub MCP server binary (default: `../github-mcp-server/github-mcp-server`)
- `GITHUB_MCP_HOST`: Host for MCP server (default: localhost)
- `GITHUB_MCP_PORT`: Port for MCP server (default: 8081)

### Testing the Auto-Startup
```bash
# Test the automatic startup
uv run python test_mcp_integration.py

# Use in real alert simulation
uv run python simulate_pagerduty_alert.py pod_crash --github-integration

# The agent automatically:
# 1. Starts github-mcp-server subprocess
# 2. Establishes MCP connection  
# 3. Fetches GitHub context for alerts
# 4. Cleans up server on exit
```

### MCP Communication Flow
1. **Subprocess Start**: `subprocess.Popen([github-mcp-server, stdio])`
2. **MCP Handshake**: JSON-RPC 2.0 initialization via stdin/stdout
3. **Tool Calls**: `list_commits`, `get_repository`, `create_issue`, etc.
4. **Resource Access**: Repository contents, file browsing
5. **Cleanup**: Process termination and resource cleanup

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

---

# 📚 Additional Development Guidance

## Backend Project Structure

```
backend/
├── src/oncall_agent/
│   ├── agent.py              # Core agent logic
│   ├── api.py                # FastAPI REST API
│   ├── config.py             # Configuration management
│   ├── api/                  # API-specific modules
│   │   ├── webhooks.py      # PagerDuty webhook handlers
│   │   ├── alert_context_parser.py  # Alert parsing logic
│   │   ├── oncall_agent_trigger.py  # Bridge webhooks to agent
│   │   ├── models.py        # Data models
│   │   ├── schemas.py       # API schemas
│   │   └── routers/         # FastAPI routers
│   ├── mcp_integrations/     # MCP integration modules
│   │   ├── base.py          # Base integration class
│   │   ├── kubernetes.py    # Kubernetes integration
│   │   ├── github_mcp.py    # GitHub integration
│   │   ├── enhanced_github_mcp.py  # Enhanced GitHub features
│   │   └── notion_direct.py # Notion integration
│   ├── strategies/          # Resolution strategies
│   │   └── kubernetes_resolver.py
│   └── utils/              # Utilities
│       └── logger.py       # Logging utilities
├── tests/                    # All test files
├── examples/                 # Example scripts
├── scripts/                  # Utility scripts
├── main.py                   # CLI entry point
├── api_server.py            # FastAPI server entry point
└── Dockerfile.prod          # Production Docker image
```

## Enhanced Development Workflow

### When Adding New Features

1. **Check existing patterns** - Look at similar implementations first
2. **Follow async patterns** - Use `async/await` for all I/O operations
3. **Add proper error handling** - Use try/catch with logging
4. **Update configuration** - Add new settings to `config.py` and `.env.example`
5. **Write tests** - Add tests to `tests/` directory
6. **Update documentation** - Modify README.md for user-facing changes

### PagerDuty Integration Development

1. **Webhook Handler**: `src/oncall_agent/api/webhooks.py`
   - FastAPI routes for receiving PagerDuty webhooks
   - Signature verification and payload validation
   - Error handling and logging

2. **Context Parser**: `src/oncall_agent/api/alert_context_parser.py`
   - Extracts technical details from alert payloads
   - Handles different alert types (database, server, security, network)
   - Normalizes data for agent processing

3. **Agent Trigger**: `src/oncall_agent/api/oncall_agent_trigger.py`
   - Bridges webhook handlers to agent logic
   - Manages async processing of alerts
   - Provides status tracking and response formatting

4. **Testing Framework**: 
   - `test_pagerduty_alerts.py` - Generate realistic test webhooks
   - `test_k8s_pagerduty_integration.py` - End-to-end Kubernetes testing
   - `test_all_integrations.py` - Comprehensive integration testing

### API Development Guidelines

#### FastAPI Best Practices

1. **Use dependency injection** for shared resources
2. **Implement proper error handling** with custom exception handlers
3. **Add request/response models** using Pydantic
4. **Include comprehensive docstrings** for auto-generated documentation
5. **Use background tasks** for long-running operations

#### API Structure Patterns

```python
# Router structure
from fastapi import APIRouter, Depends, HTTPException
from ..models import AlertModel, ResponseModel

router = APIRouter(prefix="/api/v1", tags=["alerts"])

@router.post("/alerts", response_model=ResponseModel)
async def create_alert(alert: AlertModel, background_tasks: BackgroundTasks):
    # Implementation
    pass
```

#### Error Response Format

```python
# Consistent error format
{
    "success": false,
    "error": "Error message",
    "details": {},
    "request_id": "req-123",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

## Enhanced Testing Strategy

### Integration Testing Approach

1. **Mock External Services** - Use pytest fixtures for MCP integrations
2. **Test Alert Flows** - End-to-end testing from webhook to response
3. **Kubernetes Scenarios** - Real cluster testing with Kind
4. **Performance Testing** - Load testing with multiple concurrent alerts
5. **Error Scenarios** - Test malformed payloads and network failures

### Testing Commands

```bash
# Full test suite
uv run pytest tests/ -v

# Specific test categories
uv run pytest tests/test_api.py -v
uv run pytest tests/test_integrations.py -v
uv run pytest tests/test_kubernetes.py -v

# Integration tests with real services
uv run python test_all_integrations.py

# Performance/stress testing
uv run python test_pagerduty_alerts.py --stress 50 --rate 5.0
```

## Kubernetes Development

### Local Development with Kind

1. **Cluster Setup**:
   ```bash
   # Create cluster with port mappings
   kind create cluster --config kind-config.yaml --name oncall-agent
   ```

2. **Demo Applications**:
   - `k8s-demo-apps.yaml` - Intentionally broken apps for testing
   - Different failure scenarios: CrashLoopBackOff, OOMKilled, ImagePullBackOff
   - `setup-k8s-demo.sh` - Automated deployment script

3. **Monitoring Integration**:
   - Real-time cluster monitoring
   - Automatic alert generation for common issues
   - Integration with PagerDuty webhook format

### EKS Production Setup

1. **Infrastructure as Code**:
   - `infrastructure/eks/` - Terraform configuration
   - CloudWatch Container Insights integration
   - Automatic alarm creation and PagerDuty integration

2. **Monitoring Stack**:
   - CloudWatch metrics and logs
   - Fluent Bit for log collection
   - Custom dashboards and alerts

## Configuration Management

### Environment Variables Strategy

```env
# Core Configuration
ANTHROPIC_API_KEY=sk-ant-...
LOG_LEVEL=INFO
ENVIRONMENT=development

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
CORS_ORIGINS=["http://localhost:3000"]

# PagerDuty Integration
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
PAGERDUTY_ROUTING_KEY=your-routing-key

# Kubernetes
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false

# GitHub Integration
GITHUB_TOKEN=ghp_...
GITHUB_ORGANIZATION=your-org

# MCP Settings
MCP_MAX_RETRIES=3
MCP_TIMEOUT_SECONDS=30
```

### Configuration Validation

The codebase uses Pydantic for configuration validation:

```python
# Example configuration class
class Config(BaseSettings):
    anthropic_api_key: str
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Kubernetes settings
    k8s_enabled: bool = True
    k8s_config_path: Optional[str] = None
    k8s_enable_destructive_operations: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

## Deployment Considerations

### Production Checklist

1. **Security**:
   - Use AWS Secrets Manager for sensitive values
   - Enable webhook signature verification
   - Set `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false`
   - Use IAM roles instead of access keys

2. **Monitoring**:
   - Enable CloudWatch logging
   - Set up CloudWatch alarms
   - Configure PagerDuty integration for system alerts
   - Monitor API response times and error rates

3. **Scalability**:
   - Use ECS Fargate for auto-scaling
   - Configure appropriate resource limits
   - Implement connection pooling for external services
   - Use async processing for webhook handling

4. **Reliability**:
   - Implement circuit breakers for external calls
   - Add retry logic with exponential backoff
   - Set up health checks and readiness probes
   - Configure graceful shutdown handling

## Debugging and Troubleshooting

### Common Development Issues

1. **Import Errors**:
   ```bash
   # Check Python path and virtual environment
   uv run python -c "import sys; print(sys.path)"
   uv run python -c "from src.oncall_agent.config import get_config"
   ```

2. **Configuration Issues**:
   ```bash
   # Validate configuration
   uv run python -c "from src.oncall_agent.config import get_config; print(get_config())"
   ```

3. **MCP Integration Failures**:
   ```bash
   # Test individual integrations
   uv run python examples/test_kubernetes_integration.py
   uv run python examples/test_github_integration.py
   ```

4. **API Server Issues**:
   ```bash
   # Check port availability
   lsof -i :8000
   
   # Test health endpoint
   curl http://localhost:8000/health
   ```

### Logging Strategy

The codebase uses structured logging:

```python
# Logger setup
from src.oncall_agent.utils.logger import get_logger

logger = get_logger(__name__)

# Usage patterns
logger.info("Processing alert", extra={
    "alert_id": alert.id,
    "alert_type": alert.type,
    "processing_time": time.time() - start_time
})

logger.error("Integration failed", extra={
    "integration": "kubernetes",
    "error": str(e),
    "retry_count": retry_count
})
```

## Advanced Features

### Real-time Features

1. **WebSocket Support**:
   - Real-time metrics streaming
   - Live alert processing updates
   - Dashboard real-time updates

2. **Background Processing**:
   - Async alert processing
   - Scheduled maintenance tasks
   - Automatic integration health checks

3. **Caching Strategy**:
   - Alert context caching
   - Integration response caching
   - Configuration caching

### Extensibility Points

1. **Custom MCP Integrations**:
   - Extend `MCPIntegration` base class
   - Implement required interface methods
   - Add to integration registry

2. **Alert Processing Strategies**:
   - Custom alert parsers
   - Domain-specific resolution strategies
   - Custom notification channels

3. **Monitoring Extensions**:
   - Custom metrics collection
   - Extended logging formats
   - Integration with external monitoring systems

## Performance Optimization

### Key Metrics to Monitor

1. **API Performance**:
   - Request/response times
   - Concurrent request handling
   - Error rates and types

2. **Integration Performance**:
   - MCP call latencies
   - Success/failure rates
   - Retry patterns and backoff effectiveness

3. **Agent Performance**:
   - Alert processing times
   - Claude API response times
   - Context gathering efficiency

### Optimization Strategies

1. **Async Processing**:
   - All I/O operations use async/await
   - Concurrent MCP integration calls
   - Background task processing

2. **Caching**:
   - Configuration caching
   - Integration response caching
   - Alert context caching

3. **Resource Management**:
   - Connection pooling for external services
   - Proper cleanup of resources
   - Memory usage monitoring

## Security Best Practices

### API Security

1. **Authentication**:
   - API key authentication for external access
   - Webhook signature verification
   - Rate limiting per client

2. **Data Protection**:
   - No sensitive data in logs
   - Encrypted storage for secrets
   - Secure transmission (HTTPS only)

3. **Access Control**:
   - Principle of least privilege
   - Role-based access control
   - Audit logging for all actions

### Infrastructure Security

1. **Network Security**:
   - VPC with private subnets
   - Security groups with minimal access
   - WAF for public endpoints

2. **Secrets Management**:
   - AWS Secrets Manager integration
   - No hardcoded credentials
   - Regular secret rotation

3. **Monitoring and Alerting**:
   - CloudTrail for audit logging
   - GuardDuty for threat detection
   - Real-time security alerts

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