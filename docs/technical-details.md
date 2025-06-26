# Technical Details

This document covers important technical implementation details, fixes, and architectural decisions for DreamOps.

## JSON Serialization Fix

### Issue Description
The API was returning `TypeError: Object of type ResolutionAction is not JSON serializable` when returning execution results containing `ResolutionAction` dataclass objects.

### Root Cause
In `agent_executor.py`, the execution context was storing entire `ResolutionAction` dataclass objects:

```python
# Problematic code
execution_context = {
    "action": action,  # This is a ResolutionAction dataclass!
    "incident_id": incident_id,
    "result": result
}
```

### Solution Implemented

**1. Convert Dataclass to Dictionary**
Modified the execution context to convert the `ResolutionAction` to a dictionary:

```python
# Fixed code
execution_context = {
    "action": {
        "action_type": action.action_type,
        "description": action.description,
        "params": action.params,
        "confidence": action.confidence,
        "risk_level": action.risk_level,
        "estimated_time": action.estimated_time,
        "rollback_possible": action.rollback_possible
    },
    "incident_id": incident_id,
    "result": result
}
```

**2. Added to_dict() Method**
Enhanced the `ResolutionAction` dataclass with a `to_dict()` method for consistent serialization:

```python
@dataclass
class ResolutionAction:
    action_type: str
    description: str
    params: Dict[str, Any]
    confidence: float
    risk_level: str
    estimated_time: Optional[str] = None
    rollback_possible: bool = True
    prerequisites: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "action_type": self.action_type,
            "description": self.description,
            "params": self.params,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "estimated_time": self.estimated_time,
            "rollback_possible": self.rollback_possible,
            "prerequisites": self.prerequisites or []
        }
```

**3. Usage Pattern**
Now use the `to_dict()` method consistently throughout the codebase:

```python
# In API responses
return {
    "success": True,
    "actions": [action.to_dict() for action in actions],
    "execution_context": execution_context
}

# In logging
logger.info(f"Executing action: {action.to_dict()}")
```

### Result
The API can now properly return JSON responses containing execution details without serialization errors.

## Architecture Overview

### Core Components

1. **AI Agent**: Claude-powered incident analysis and resolution
2. **MCP Integrations**: Pluggable external service connections
3. **Execution Engine**: Secure command execution with rollback capabilities
4. **Database Layer**: PostgreSQL with Drizzle ORM for persistence
5. **API Layer**: FastAPI backend with real-time WebSocket support
6. **Frontend**: Next.js dashboard with real-time incident monitoring

### Data Flow

```
PagerDuty Alert → Webhook → AI Analysis → MCP Integration → K8s Execution → Verification → Resolution
```

## Error Handling Patterns

### Graceful Error Recovery
All operations include comprehensive error handling:

```python
async def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = await self._perform_action(action, params)
        return {"success": True, "result": result}
    except Exception as e:
        self.logger.error(f"Action {action} failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### Retry Logic
Network operations include exponential backoff:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def make_api_call(self, url: str, data: Dict[str, Any]):
    # API call implementation
    pass
```

## Security Implementation

### API Key Management
- Environment variables for sensitive data
- AWS Secrets Manager in production
- Regular key rotation procedures
- Least-privilege access controls

### Request Validation
All API inputs are validated using Pydantic models:

```python
class AlertRequest(BaseModel):
    title: str
    description: str
    severity: str
    timestamp: datetime
    
    @validator('severity')
    def validate_severity(cls, v):
        allowed = ['low', 'medium', 'high', 'critical']
        if v.lower() not in allowed:
            raise ValueError(f'Severity must be one of: {allowed}')
        return v.lower()
```

## Performance Optimizations

### Async Architecture
- All I/O operations use async/await
- Concurrent execution of multiple operations
- Connection pooling for HTTP clients
- Database connection pooling

### Caching Strategy
- In-memory caching for frequently accessed data
- TTL-based cache invalidation
- Redis for distributed caching (planned)

## Testing Framework

### Test Categories
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Cross-component interactions
3. **E2E Tests**: Complete workflow validation
4. **Load Tests**: Performance and scalability testing

### Mock Framework
Comprehensive mocking for external dependencies:

```python
@pytest.fixture
def mock_k8s_integration():
    mock = AsyncMock()
    mock.connect.return_value = True
    mock.execute_action.return_value = {"success": True}
    return mock
``` 