# MCP Integrations Guide

This guide covers the Model Context Protocol (MCP) integrations that enable DreamOps to connect with external tools and services for incident response.

## Overview

MCP (Model Context Protocol) is the foundation for DreamOps' extensible integration system. All integrations follow a consistent interface pattern and support:

- **Asynchronous Operations**: All MCP calls are async for better performance
- **Retry Logic**: Built-in exponential backoff for network operations
- **Health Monitoring**: Real-time status checking for each integration
- **Error Handling**: Graceful error recovery and logging

## Available Integrations

### Core Integrations
- **Kubernetes**: Pod management, deployment operations, resource monitoring
- **GitHub**: Repository management, issue tracking, pull request automation
- **PagerDuty**: Incident management, alerting, and resolution workflows
- **Notion**: Documentation management and knowledge base integration

### Planned Integrations
- **Slack**: Team notifications and interactive workflows
- **Grafana**: Metrics and dashboard integration
- **Datadog**: Advanced monitoring and alerting
- **AWS CloudWatch**: Native AWS monitoring integration

## MCP Integration Interface

Every MCP integration must implement the base `MCPIntegration` class with these required methods:

```python
from src.oncall_agent.mcp_integrations.base import MCPIntegration

class CustomIntegration(MCPIntegration):
    async def connect(self) -> bool:
        """Establish connection to the service"""
        pass
    
    async def disconnect(self) -> None:
        """Gracefully close connections"""
        pass
    
    async def fetch_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve information from the service"""
        pass
    
    async def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform remediation actions"""
        pass
    
    def get_capabilities(self) -> List[str]:
        """List available actions this integration supports"""
        pass
    
    async def health_check(self) -> bool:
        """Verify connection status"""
        pass
```

## Kubernetes Integration

### Overview
The Kubernetes integration provides comprehensive cluster management capabilities for automated incident resolution.

### Configuration
```env
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false
```

### Capabilities
- **Pod Management**: List, describe, restart, and monitor pods
- **Deployment Operations**: Scale, rollback, and update deployments
- **Service Monitoring**: Check service health and endpoints
- **Event Retrieval**: Get cluster events for troubleshooting
- **Resource Analysis**: Monitor CPU, memory, and disk usage

### YOLO Mode Operations
When `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`, the integration can:

```python
# Restart failed pods
await k8s.execute_action("restart_error_pods", {
    "namespace": "production",
    "selector": "app=api-gateway"
})

# Increase memory limits
await k8s.execute_action("increase_memory_limits", {
    "deployment": "api-gateway",
    "memory_limit": "2Gi"
})

# Scale deployments
await k8s.execute_action("scale_deployment", {
    "deployment": "worker",
    "replicas": 5
})
```

### Action Types
- `identify_error_pods`: Find pods in error states
- `restart_error_pods`: Delete pods to force restart
- `check_resource_constraints`: Run kubectl top commands
- `identify_oom_pods`: Find OOM killed pods
- `increase_memory_limits`: Patch deployments with higher memory
- `scale_deployment`: Scale deployments up or down
- `rollback_deployment`: Rollback to previous version
- `get_pod_logs`: Retrieve pod logs for analysis

### Example Usage
```python
from src.oncall_agent.mcp_integrations.kubernetes import KubernetesIntegration

async def diagnose_pod_issues():
    k8s = KubernetesIntegration()
    await k8s.connect()
    
    # Get pods in error state
    error_pods = await k8s.fetch_context({
        "action": "list_error_pods",
        "namespace": "production"
    })
    
    # Restart problematic pods
    if error_pods['pods']:
        result = await k8s.execute_action("restart_error_pods", {
            "pods": error_pods['pods']
        })
        
    await k8s.disconnect()
```

## GitHub Integration

### Overview
The GitHub integration enables automated issue management, pull request creation, and repository monitoring.

### Configuration
```env
GITHUB_TOKEN=your-github-token
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo
```

### Capabilities
- **Issue Management**: Create, update, and close issues automatically
- **Pull Request Automation**: Create PRs for fixes and updates
- **Repository Monitoring**: Watch for changes and events
- **Code Analysis**: Review code changes and suggest improvements

### Example Operations
```python
# Create incident issue
await github.execute_action("create_issue", {
    "title": "Production Incident: API Gateway Down",
    "body": "Automated incident report from DreamOps AI agent",
    "labels": ["incident", "production", "urgent"]
})

# Create fix PR
await github.execute_action("create_pull_request", {
    "title": "Fix: Increase memory limits for API gateway",
    "body": "Automated fix applied by DreamOps",
    "branch": "fix/api-gateway-memory",
    "base": "main"
})
```

## PagerDuty Integration

### Overview
Comprehensive incident management integration for PagerDuty services.

### Configuration
```env
PAGERDUTY_API_KEY=your-api-key
PAGERDUTY_USER_EMAIL=your-email@company.com
PAGERDUTY_WEBHOOK_SECRET=your-webhook-secret
```

### Capabilities
- **Incident Acknowledgment**: Automatically acknowledge incidents
- **Incident Resolution**: Mark incidents as resolved with details
- **Note Addition**: Add progress updates to incidents
- **Escalation Management**: Handle incident escalations

### Webhook Events
- `incident.trigger`: New incident created
- `incident.acknowledge`: Incident acknowledged
- `incident.resolve`: Incident resolved
- `incident.escalate`: Incident escalated

### Example Workflow
```python
async def handle_pagerduty_incident(incident_data):
    pagerduty = PagerDutyIntegration()
    
    # Acknowledge incident
    await pagerduty.execute_action("acknowledge_incident", {
        "incident_id": incident_data['id'],
        "requester_email": config.PAGERDUTY_USER_EMAIL
    })
    
    # Add investigation note
    await pagerduty.execute_action("add_note", {
        "incident_id": incident_data['id'],
        "note": "AI agent investigating issue..."
    })
    
    # Resolve after successful remediation
    await pagerduty.execute_action("resolve_incident", {
        "incident_id": incident_data['id'],
        "resolution_note": "Fixed by AI agent: Memory limits increased"
    })
```

## Notion Integration

### Overview
Knowledge base integration for documentation management and incident tracking.

### Configuration
```env
NOTION_TOKEN=your-notion-token
NOTION_DATABASE_ID=your-database-id
```

### Capabilities
- **Incident Documentation**: Create incident reports and post-mortems
- **Knowledge Base**: Search and update documentation
- **Runbook Management**: Access and update operational runbooks
- **Metrics Tracking**: Log incident metrics and trends

### Example Operations
```python
# Create incident report
await notion.execute_action("create_page", {
    "parent_id": "incident-database-id",
    "title": "Incident Report: API Gateway Outage",
    "content": {
        "summary": "Memory exhaustion caused pod restarts",
        "resolution": "Increased memory limits from 1Gi to 2Gi",
        "duration": "15 minutes"
    }
})

# Search runbooks
runbooks = await notion.fetch_context({
    "action": "search",
    "query": "kubernetes troubleshooting",
    "filter": "runbook"
})
```

## Creating New Integrations

### Step 1: Create Integration File

Create a new file in `src/oncall_agent/mcp_integrations/`:

```python
# src/oncall_agent/mcp_integrations/my_service.py
from typing import Dict, Any, List
from .base import MCPIntegration

class MyServiceIntegration(MCPIntegration):
    def __init__(self):
        super().__init__()
        self.service_name = "myservice"
        self.client = None
    
    async def connect(self) -> bool:
        try:
            # Initialize your service client
            self.client = MyServiceClient(api_key=self.config.MY_SERVICE_API_KEY)
            await self.client.authenticate()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to MyService: {e}")
            return False
    
    async def disconnect(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None
    
    async def fetch_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        action = params.get("action")
        
        if action == "get_status":
            return await self._get_service_status()
        elif action == "list_alerts":
            return await self._list_alerts()
        else:
            raise ValueError(f"Unknown fetch action: {action}")
    
    async def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "create_alert":
            return await self._create_alert(params)
        elif action == "resolve_alert":
            return await self._resolve_alert(params)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def get_capabilities(self) -> List[str]:
        return [
            "get_status",
            "list_alerts", 
            "create_alert",
            "resolve_alert"
        ]
    
    async def health_check(self) -> bool:
        try:
            if not self.client:
                return False
            status = await self.client.ping()
            return status == "ok"
        except Exception:
            return False
    
    # Private methods for implementation
    async def _get_service_status(self) -> Dict[str, Any]:
        # Implementation details
        pass
```

### Step 2: Add Configuration

Add required configuration to `src/oncall_agent/config.py`:

```python
@dataclass
class Config:
    # ... existing config ...
    
    # MyService integration
    MY_SERVICE_API_KEY: str = ""
    MY_SERVICE_ENABLED: bool = False
```

### Step 3: Register Integration

Add to the integration registry in `src/oncall_agent/agent.py`:

```python
from src.oncall_agent.mcp_integrations.my_service import MyServiceIntegration

class OncallAgent:
    def __init__(self):
        self.integrations = {
            "kubernetes": KubernetesIntegration(),
            "github": GitHubIntegration(),
            "pagerduty": PagerDutyIntegration(),
            "myservice": MyServiceIntegration(),  # Add here
        }
```

### Step 4: Add Environment Variables

Update `.env.example`:

```env
# MyService Integration
MY_SERVICE_API_KEY=your-api-key-here
MY_SERVICE_ENABLED=true
```

### Step 5: Test Integration

Create tests in `tests/test_my_service_integration.py`:

```python
import pytest
from src.oncall_agent.mcp_integrations.my_service import MyServiceIntegration

@pytest.mark.asyncio
async def test_my_service_connection():
    integration = MyServiceIntegration()
    
    # Mock the service client
    with patch('my_service.Client') as mock_client:
        mock_client.return_value.authenticate.return_value = True
        
        result = await integration.connect()
        assert result is True
        
        await integration.disconnect()
```

## Integration Best Practices

### Error Handling
```python
async def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = await self._perform_action(action, params)
        return {"success": True, "result": result}
    except Exception as e:
        self.logger.error(f"Action {action} failed: {e}")
        return {"success": False, "error": str(e)}
```

### Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def _make_api_call(self, endpoint: str, data: Dict[str, Any]):
    # API call implementation
    pass
```

### Rate Limiting
```python
import asyncio
from asyncio import Semaphore

class MyServiceIntegration(MCPIntegration):
    def __init__(self):
        super().__init__()
        self._rate_limit = Semaphore(5)  # Max 5 concurrent requests
    
    async def _make_request(self, *args, **kwargs):
        async with self._rate_limit:
            return await self.client.request(*args, **kwargs)
```

### Logging
```python
def __init__(self):
    super().__init__()
    self.logger = logging.getLogger(f"mcp.{self.service_name}")

async def execute_action(self, action: str, params: Dict[str, Any]):
    self.logger.info(f"Executing action: {action} with params: {params}")
    # ... implementation
    self.logger.info(f"Action {action} completed successfully")
```

## Integration Testing

### Unit Tests
```bash
cd backend
uv run pytest tests/test_mcp_integrations.py -v
```

### Integration Tests
```bash
# Test with real services (requires valid credentials)
uv run pytest tests/test_mcp_integration_real.py -v --integration
```

### Health Check Testing
```bash
# Test all integration health checks
uv run python -c "
from src.oncall_agent.agent import OncallAgent
agent = OncallAgent()
asyncio.run(agent.test_all_integrations())
"
```

## Monitoring and Observability

### Metrics
Each integration automatically tracks:
- Request count and latency
- Success/failure rates
- Health check status
- Error types and frequencies

### Logging
Integration logs include:
- Connection status changes
- Action execution details
- Error messages and stack traces
- Performance metrics

### Alerting
Set up alerts for:
- Integration health check failures
- High error rates
- Unusual latency patterns
- Authentication failures

## Security Considerations

### API Key Management
- Store API keys in environment variables
- Use AWS Secrets Manager in production
- Rotate keys regularly
- Use least-privilege access

### Network Security
- Use HTTPS for all API calls
- Validate SSL certificates
- Implement request signing where available
- Use VPN or private networks when possible

### Data Handling
- Don't log sensitive data
- Encrypt data in transit and at rest
- Follow data retention policies
- Implement proper access controls 