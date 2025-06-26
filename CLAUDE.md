# AI Assistant Instructions for DreamOps Oncall Agent Codebase

This document provides comprehensive instructions for AI assistants (like Claude, GPT-4, etc.) on how to effectively work with this codebase.

## Documentation Structure

**IMPORTANT**: Before making any changes, read the relevant documentation in the `/docs` folder:

- `docs/database-setup.md` - Database configuration for all environments
- `docs/pagerduty-integration.md` - PagerDuty setup and webhook configuration  
- `docs/yolo-mode.md` - Autonomous operation mode and safety mechanisms
- `docs/deployment.md` - AWS deployment options (Terraform, Amplify)
- `docs/mcp-integrations.md` - External service integrations and API usage
- `docs/technical-details.md` - Architecture, implementation details, and fixes
- `docs/ci-cd.md` - GitHub Actions workflows and deployment automation

Always check these documentation files for the latest information before implementing changes.

## Project Overview

DreamOps is an intelligent AI-powered incident response and infrastructure management platform built with:
- **Claude API**: For intelligent incident analysis and decision making
- **MCP (Model Context Protocol)**: For integrating with external tools and services
- **FastAPI**: Web framework for the REST API and webhooks
- **Python AsyncIO**: For concurrent operations and real-time processing
- **uv**: Modern Python package manager for dependency management
- **Next.js**: Frontend SaaS interface with real-time dashboard
- **Terraform**: AWS infrastructure deployment and management
- **Neon**: PostgreSQL database with environment separation
- **Docker**: Containerization for consistent deployments

## Key Architecture Decisions

1. **Modular MCP Integrations**: All integrations extend `MCPIntegration` base class in `src/oncall_agent/mcp_integrations/base.py`
2. **Async-First**: All operations are async to handle concurrent MCP calls efficiently
3. **Configuration-Driven**: Uses pydantic for config validation and environment variables
4. **Type-Safe**: Extensive use of type hints throughout the codebase
5. **Retry Logic**: Built-in exponential backoff for network operations (configurable via MCP_MAX_RETRIES)
6. **Singleton Config**: Global configuration instance accessed via `get_config()`
7. **Environment Separation**: Complete database and configuration isolation between local/staging/production
8. **YOLO Mode**: Autonomous remediation mode that executes fixes without human approval

## Project Structure

```
backend/
├── src/oncall_agent/
│   ├── agent.py              # Core agent logic
│   ├── agent_enhanced.py     # Enhanced agent with YOLO mode
│   ├── agent_executor.py     # Command execution engine
│   ├── api.py                # FastAPI REST API
│   ├── config.py             # Configuration management
│   ├── mcp_integrations/     # MCP integration modules
│   │   ├── base.py          # Base integration class
│   │   ├── kubernetes.py    # Kubernetes integration
│   │   ├── github_mcp.py    # GitHub integration
│   │   ├── notion_direct.py # Notion integration
│   │   └── pagerduty.py     # PagerDuty integration
│   ├── strategies/          # Resolution strategies
│   │   ├── kubernetes_resolver.py
│   │   └── deterministic_k8s_resolver.py
│   └── utils/               # Utility functions
│       └── logger.py        # Logging configuration
├── tests/                    # All test files
├── examples/                 # Example scripts and demos
├── scripts/                  # Utility scripts
├── main.py                   # CLI entry point
└── Dockerfile.prod          # Production Docker image

frontend/
├── app/                     # Next.js app router
│   ├── (dashboard)/        # Dashboard pages
│   ├── (login)/            # Authentication pages
│   └── api/                # API routes
├── components/             # React components
│   ├── ui/                # UI components
│   └── incidents/         # Incident-specific components
├── lib/                   # Utilities and configurations
│   ├── db/               # Database utilities
│   ├── auth/             # Authentication
│   └── hooks/            # React hooks
└── scripts/              # Build and deployment scripts
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

4. **Required methods to implement**:
   ```python
   async def connect() -> bool
   async def disconnect() -> None
   async def fetch_context(params: Dict[str, Any]) -> Dict[str, Any]
   async def execute_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]
   def get_capabilities() -> List[str]
   async def health_check() -> bool
   ```

### Code Style Guidelines

- Use descriptive variable names
- Add type hints to all functions
- Include docstrings for all public methods
- Follow PEP 8 conventions
- Use `async/await` for all I/O operations
- Handle exceptions gracefully with proper logging
- Use dataclasses for structured data
- Implement proper JSON serialization for API responses

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
   from src.oncall_agent.utils.logger import get_logger
   logger = get_logger(__name__)
   ```

4. **JSON Serialization** (IMPORTANT):
   ```python
   # Always convert dataclasses to dict for JSON serialization
   execution_context = {
       "action": action.to_dict() if hasattr(action, 'to_dict') else action.__dict__,
       "result": result
   }
   ```

## Important Files to Understand

1. **`src/oncall_agent/agent_enhanced.py`**: Enhanced agent with YOLO mode capabilities
2. **`src/oncall_agent/agent_executor.py`**: Command execution engine for Kubernetes operations
3. **`src/oncall_agent/mcp_integrations/base.py`**: Base class defining the MCP interface
4. **`src/oncall_agent/config.py`**: Configuration schema and defaults
5. **`src/oncall_agent/api.py`**: FastAPI application with REST endpoints
6. **`main.py`**: Entry point showing how to use the agent
7. **`src/oncall_agent/strategies/deterministic_k8s_resolver.py`**: Kubernetes resolution strategies

## Commands and Development Workflow

### Development Commands
- **Install dependencies**: `uv sync`
- **Run the agent**: `uv run python main.py`
- **Run API server**: `uv run python api_server.py`
- **Add dependency**: `uv add <package>`
- **Add dev dependency**: `uv add --dev <package>`

### Environment Setup
```bash
# Backend setup
cd backend
uv sync
cp .env.example .env
# Edit .env with your API keys

# Frontend setup
cd frontend
npm install
npm run dev
```

### Testing and Validation
- **Run demo**: `uv run python main.py`
- **Run API server**: `uv run uvicorn src.oncall_agent.api:app --reload`
- **Run tests**: `uv run pytest tests/`
- **Run linter**: `uv run ruff check . --fix`
- **Run type checker**: `uv run mypy . --ignore-missing-imports`

### Database Operations
```bash
# Frontend database operations
cd frontend
npm run db:migrate:local      # Migrate local database
npm run db:migrate:staging    # Migrate staging database
npm run db:migrate:production # Migrate production (requires confirmation)
npm run db:studio            # Open Drizzle Studio
npm run test:db             # Test all database connections
```

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

# 5. Test API server
uv run python api_server.py
```

If any of these fail, fix the issues before considering the task complete.

## Testing Approach

When asked to test changes:
1. Check if `.env` exists, if not copy from `.env.example`
2. Ensure `ANTHROPIC_API_KEY` is set
3. Run with: `uv run python main.py`
4. For specific integrations, create mock implementations first
5. Test database connections: `cd frontend && npm run test:db`
6. Test API endpoints: `curl -X GET http://localhost:8000/health`

## Common Tasks

### Adding a New MCP Integration
1. Create file in `src/oncall_agent/mcp_integrations/`
2. Extend `MCPIntegration` base class
3. Implement all abstract methods
4. Add configuration to `.env.example`
5. Update README.md with usage instructions
6. Add integration to the main config file

### Modifying Alert Handling
1. Look at `PagerAlert` model in `agent_enhanced.py`
2. Modify `handle_pager_alert` method
3. Update the prompt sent to Claude if needed
4. Test with different alert types
5. Ensure proper JSON serialization

### Adding New Configuration Options
1. Add to `Config` class in `config.py`
2. Add to `.env.example` with description
3. Document in README.md
4. Handle in frontend configuration if needed

### Implementing YOLO Mode Features
1. Understand the YOLO mode philosophy: execute ALL actions without human approval
2. Add new resolution strategies in `strategies/` directory
3. Implement corresponding action executors in `agent_executor.py`
4. Ensure proper error handling and logging
5. Test with `fuck_kubernetes.sh` scenarios

### Database Schema Changes
1. Modify schema in `frontend/lib/db/schema.ts`
2. Generate migration: `npm run db:generate`
3. Apply to local: `npm run db:migrate:local`
4. Test with Drizzle Studio: `npm run db:studio`
5. Apply to staging/production when ready

## Testing Kubernetes Alerting

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
- `GET /alerts/{alert_id}` - Get alert details
- `GET /integrations` - List available MCP integrations
- `POST /integrations/{name}/health` - Check specific integration health
- `POST /webhook/pagerduty` - PagerDuty webhook handler
- `GET /agent/config` - Get current agent configuration
- `POST /agent/config` - Update agent configuration

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
- **Frontend**: S3 + CloudFront or AWS Amplify
- **Database**: Neon PostgreSQL with environment separation
- **Monitoring**: CloudWatch dashboards and alarms
- **Security**: Secrets Manager for sensitive data

### CI/CD Pipelines
- **Backend**: `.github/workflows/backend-ci.yml`
- **Frontend**: `.github/workflows/frontend-ci.yml`
- **Security**: `.github/workflows/security-scan.yml`
- **Markdown Check**: `.github/workflows/check-markdown-files.yml`

### Environment Management
The project uses strict environment separation:
- **Local**: For development with local database
- **Staging**: For testing with staging database  
- **Production**: For production with production database

Each environment has its own:
- Database instance
- Configuration files
- Environment variables
- Deployment pipeline

### GitHub Secrets Required
1. `AWS_ACCESS_KEY_ID` - AWS access key for deployment
2. `AWS_SECRET_ACCESS_KEY` - AWS secret key
3. `ANTHROPIC_API_KEY` - Your Anthropic API key
4. `CLOUDFRONT_DISTRIBUTION_ID` - CloudFront ID (after initial deployment)
5. `AMPLIFY_APP_ID` - Amplify app ID for frontend deployment
6. `NEON_DATABASE_URL_STAGING` - Staging database connection string
7. `NEON_DATABASE_URL_PROD` - Production database connection string

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
- Memory limit adjustments
- Resource constraint analysis

### YOLO Mode Kubernetes Operations
When YOLO mode is enabled (`K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`), the agent can:
- Automatically restart failed pods
- Increase memory limits for OOM issues
- Scale deployments up/down
- Apply configuration patches
- Delete problematic resources

### Kubernetes Action Types
- `identify_error_pods`: Find pods in error states
- `restart_error_pods`: Delete pods to force restart
- `check_resource_constraints`: Run kubectl top commands
- `identify_oom_pods`: Find OOM killed pods
- `increase_memory_limits`: Patch deployments with higher memory
- `scale_deployment`: Scale deployments up or down

## PagerDuty Integration

### Configuration
```env
PAGERDUTY_API_KEY=your-api-key-here
PAGERDUTY_USER_EMAIL=your-email@company.com
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
```

### Webhook Handling
The PagerDuty webhook handler (`/webhook/pagerduty`) processes:
- Incident creation
- Incident updates
- Alert acknowledgments
- Incident resolutions

### YOLO Mode Behavior
In YOLO mode, the PagerDuty integration:
- Always attempts to acknowledge incidents
- Automatically resolves incidents after successful remediation
- Ignores API errors and continues execution
- Logs warnings but doesn't fail the remediation process

## Database Management

### Schema Design
The database schema is defined in `frontend/lib/db/schema.ts` using Drizzle ORM:
- **Users**: Authentication and authorization
- **Teams**: Multi-tenancy support
- **Incidents**: Incident tracking and history
- **Metrics**: Performance and analytics data
- **Logs**: Agent execution logs

### Migration Strategy
1. **Local Development**: Auto-migrate with `npm run db:migrate:local`
2. **Staging**: Manual migration with `npm run db:migrate:staging`
3. **Production**: Confirmation required with `npm run db:migrate:production`

### Database Testing
Use the included database testing utilities:
```bash
cd frontend
node test-db-connections.mjs  # Test all connections
npm run db:studio            # Visual database exploration
```

## Troubleshooting Common Issues

### JSON Serialization Errors
**Problem**: `TypeError: Object of type ResolutionAction is not JSON serializable`

**Solution**: Always convert dataclasses to dictionaries:
```python
# Add to_dict() method to dataclasses
def to_dict(self) -> dict[str, Any]:
    return asdict(self)

# Use in execution context
execution_context = {
    "action": action.to_dict(),
    "result": result
}
```

### PagerDuty API Errors
**Problem**: "Requester User Not Found"

**Solution**: Ensure `PAGERDUTY_USER_EMAIL` is a valid user in your PagerDuty account.

### Database Connection Issues
**Problem**: Connection timeouts or SSL errors

**Solution**: 
1. Verify connection strings include `?sslmode=require`
2. Check Neon project is active (not suspended)
3. Ensure no `&channel_binding=require` in connection string

### YOLO Mode Not Executing
**Problem**: Agent not executing remediation actions

**Solution**:
1. Verify `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`
2. Check `K8S_ENABLED=true`
3. Ensure kubectl is configured and working
4. Verify API server is running with correct configuration

### Frontend Build Issues
**Problem**: Next.js build failures

**Solution**:
1. Check all environment variables are set
2. Verify database connection strings
3. Ensure API URL is accessible
4. Check for TypeScript errors

## Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use different secrets for each environment
- Rotate API keys regularly
- Use least-privilege access for service accounts

### Database Security
- Each environment uses completely separate databases
- Connection strings include SSL requirements
- Database users have minimal required permissions
- Regular security updates for database instances

### Kubernetes Security
- RBAC permissions are minimally scoped
- Destructive operations require explicit enablement
- All kubectl commands are logged
- Namespace isolation for testing

### API Security
- Authentication required for sensitive endpoints
- Request validation using Pydantic models
- Rate limiting implemented
- Comprehensive audit logging

## Performance Optimization

### Async Operations
- All I/O operations use async/await
- Concurrent processing of multiple alerts
- Connection pooling for database operations
- Efficient resource cleanup

### Caching Strategy
- Configuration cached in memory
- Database query results cached where appropriate
- Static assets served from CDN
- Browser caching for frontend resources

### Monitoring and Alerting
- CloudWatch integration for metrics
- Custom dashboards for system health
- Alerting on error rates and performance
- Real-time log streaming

## Best Practices for AI Assistants

### When Working with This Codebase

1. **Always check the latest README.md and this CLAUDE.md** for current instructions
2. **Test all changes locally** before suggesting them
3. **Consider environment separation** when making database changes
4. **Respect YOLO mode safety mechanisms** when adding new features
5. **Follow the established patterns** for error handling and logging
6. **Document any new integrations or features** thoroughly
7. **Test with multiple scenarios** including edge cases
8. **Ensure JSON serialization compatibility** for all API responses

### Code Review Checklist

Before submitting any changes:
- [ ] All tests pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Application runs successfully
- [ ] API endpoints respond correctly
- [ ] Database migrations work
- [ ] Documentation is updated
- [ ] Environment variables are documented
- [ ] Security considerations are addressed

This document should be your primary reference when working with the DreamOps codebase. Always refer back to it when implementing new features or making modifications.