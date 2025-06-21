"""Integration management API endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Path, Query
from fastapi.responses import JSONResponse

from src.oncall_agent.agent import OncallAgent
from src.oncall_agent.api.schemas import (
    Integration,
    IntegrationConfig,
    IntegrationHealth,
    IntegrationStatus,
    SuccessResponse,
)
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])

# Integration configurations (mock storage)
INTEGRATION_CONFIGS: dict[str, IntegrationConfig] = {
    "kubernetes": IntegrationConfig(
        enabled=True,
        config={
            "cluster": "production",
            "namespace": "default",
            "kubeconfig_path": "/etc/kubernetes/config"
        }
    ),
    "github": IntegrationConfig(
        enabled=True,
        config={
            "org": "mycompany",
            "repos": ["backend", "frontend", "infrastructure"],
            "token": "***"
        }
    ),
    "pagerduty": IntegrationConfig(
        enabled=True,
        config={
            "api_key": "***",
            "service_ids": ["P123456", "P789012"]
        }
    ),
    "datadog": IntegrationConfig(
        enabled=True,
        config={
            "api_key": "***",
            "app_key": "***",
            "site": "datadoghq.com"
        }
    ),
    "slack": IntegrationConfig(
        enabled=False,
        config={
            "webhook_url": "",
            "channel": "#incidents"
        }
    )
}


async def get_agent_instance() -> OncallAgent | None:
    """Get agent instance if available."""
    try:
        # Import from agent router to share instance
        from src.oncall_agent.api.routers.agent import get_agent
        return await get_agent()
    except:
        return None


@router.get("/", response_model=list[Integration])
async def list_integrations() -> list[Integration]:
    """List all available integrations."""
    try:
        integrations = []
        agent = await get_agent_instance()

        for name, config in INTEGRATION_CONFIGS.items():
            # Get real status from agent if available
            status = IntegrationStatus.DISCONNECTED
            capabilities = []
            health = None

            if agent and name in agent.mcp_integrations:
                integration = agent.mcp_integrations[name]
                is_healthy = await integration.health_check()
                status = IntegrationStatus.CONNECTED if is_healthy else IntegrationStatus.ERROR
                capabilities = integration.get_capabilities()

                health = IntegrationHealth(
                    name=name,
                    status=status,
                    last_check=datetime.now(UTC),
                    metrics={
                        "requests_per_minute": 42,
                        "error_rate": 0.02,
                        "avg_response_time_ms": 150
                    }
                )

            integrations.append(Integration(
                name=name,
                type=name,  # Could be more specific
                status=status if config.enabled else IntegrationStatus.DISCONNECTED,
                capabilities=capabilities,
                config=config,
                health=health
            ))

        return integrations

    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{integration_name}", response_model=Integration)
async def get_integration(
    integration_name: str = Path(..., description="Integration name")
) -> Integration:
    """Get integration details."""
    if integration_name not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")

    config = INTEGRATION_CONFIGS[integration_name]
    agent = await get_agent_instance()

    # Get real status from agent
    status = IntegrationStatus.DISCONNECTED
    capabilities = []
    health = None

    if agent and integration_name in agent.mcp_integrations:
        integration = agent.mcp_integrations[integration_name]
        is_healthy = await integration.health_check()
        status = IntegrationStatus.CONNECTED if is_healthy else IntegrationStatus.ERROR
        capabilities = integration.get_capabilities()

        health = IntegrationHealth(
            name=integration_name,
            status=status,
            last_check=datetime.now(UTC),
            metrics={}
        )

    return Integration(
        name=integration_name,
        type=integration_name,
        status=status if config.enabled else IntegrationStatus.DISCONNECTED,
        capabilities=capabilities,
        config=config,
        health=health
    )


@router.put("/{integration_name}/config", response_model=SuccessResponse)
async def update_integration_config(
    integration_name: str = Path(..., description="Integration name"),
    config: IntegrationConfig = Body(..., description="Integration configuration")
) -> SuccessResponse:
    """Update integration configuration."""
    if integration_name not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Update config
    INTEGRATION_CONFIGS[integration_name] = config

    # If agent is available, reconnect integration
    agent = await get_agent_instance()
    if agent and integration_name in agent.mcp_integrations:
        if config.enabled:
            # Reconnect with new config
            integration = agent.mcp_integrations[integration_name]
            await integration.disconnect()
            await integration.connect()
        else:
            # Disconnect if disabled
            await agent.mcp_integrations[integration_name].disconnect()

    logger.info(f"Updated configuration for integration {integration_name}")

    return SuccessResponse(
        success=True,
        message=f"Integration {integration_name} configuration updated successfully"
    )


@router.post("/{integration_name}/test")
async def test_integration(
    integration_name: str = Path(..., description="Integration name")
) -> JSONResponse:
    """Test integration connection."""
    if integration_name not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")

    config = INTEGRATION_CONFIGS[integration_name]
    if not config.enabled:
        return JSONResponse(content={
            "success": False,
            "error": "Integration is disabled"
        })

    # Perform integration-specific tests
    test_results = await perform_integration_test(integration_name)

    return JSONResponse(content=test_results)


async def perform_integration_test(integration_name: str) -> dict[str, Any]:
    """Perform integration-specific connection tests."""
    # Mock test results based on integration type
    if integration_name == "kubernetes":
        return {
            "success": True,
            "tests": {
                "cluster_connection": "pass",
                "namespace_access": "pass",
                "pod_list": "pass",
                "deployment_list": "pass"
            },
            "message": "All Kubernetes API tests passed"
        }
    elif integration_name == "github":
        return {
            "success": True,
            "tests": {
                "api_authentication": "pass",
                "org_access": "pass",
                "repo_access": "pass",
                "webhook_delivery": "pass"
            },
            "message": "GitHub integration working correctly"
        }
    elif integration_name == "pagerduty":
        return {
            "success": True,
            "tests": {
                "api_key_valid": "pass",
                "service_access": "pass",
                "incident_creation": "pass",
                "webhook_validation": "pass"
            },
            "message": "PagerDuty integration verified"
        }
    elif integration_name == "datadog":
        return {
            "success": True,
            "tests": {
                "api_connection": "pass",
                "metrics_query": "pass",
                "logs_access": "pass",
                "monitor_list": "pass"
            },
            "message": "Datadog API connection successful"
        }
    else:
        return {
            "success": False,
            "error": f"No test suite available for {integration_name}"
        }


@router.get("/{integration_name}/metrics")
async def get_integration_metrics(
    integration_name: str = Path(..., description="Integration name"),
    period: str = Query("1h", description="Time period: 1h, 24h, 7d")
) -> JSONResponse:
    """Get integration performance metrics."""
    if integration_name not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Mock metrics data
    metrics = {
        "integration": integration_name,
        "period": period,
        "metrics": {
            "total_requests": 1523,
            "successful_requests": 1498,
            "failed_requests": 25,
            "error_rate": 0.0164,
            "avg_response_time_ms": 142.5,
            "p95_response_time_ms": 320,
            "p99_response_time_ms": 580
        },
        "errors_by_type": {
            "timeout": 12,
            "authentication": 3,
            "rate_limit": 5,
            "server_error": 5
        },
        "usage_by_feature": {
            "fetch_context": 823,
            "execute_action": 412,
            "health_check": 288
        }
    }

    return JSONResponse(content=metrics)


@router.post("/{integration_name}/sync")
async def sync_integration_data(
    integration_name: str = Path(..., description="Integration name")
) -> SuccessResponse:
    """Manually sync integration data."""
    if integration_name not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")

    config = INTEGRATION_CONFIGS[integration_name]
    if not config.enabled:
        raise HTTPException(status_code=400, detail="Integration is disabled")

    # Mock sync operation
    logger.info(f"Syncing data for integration {integration_name}")

    return SuccessResponse(
        success=True,
        message=f"Sync initiated for {integration_name}",
        data={
            "sync_id": "sync-123",
            "estimated_time_seconds": 30
        }
    )


@router.get("/{integration_name}/logs")
async def get_integration_logs(
    integration_name: str = Path(..., description="Integration name"),
    limit: int = Query(100, ge=1, le=1000),
    level: str | None = Query(None, description="Log level filter")
) -> JSONResponse:
    """Get integration-specific logs."""
    if integration_name not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Mock log entries
    logs = []
    log_levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
    log_messages = [
        "Connected to service successfully",
        "Fetching context for incident analysis",
        "Rate limit warning: 80% of quota used",
        "Connection timeout, retrying...",
        "Successfully executed remediation action"
    ]

    for i in range(min(limit, 20)):
        log_level = log_levels[i % len(log_levels)]
        if level and log_level != level.upper():
            continue

        logs.append({
            "timestamp": (datetime.now(UTC) - timedelta(minutes=i*5)).isoformat(),
            "level": log_level,
            "message": log_messages[i % len(log_messages)],
            "integration": integration_name,
            "context": {
                "request_id": f"req-{1000+i}",
                "duration_ms": 150 + (i * 10)
            }
        })

    return JSONResponse(content={
        "integration": integration_name,
        "logs": logs,
        "total": len(logs)
    })


@router.get("/available")
async def get_available_integrations() -> JSONResponse:
    """Get list of available integrations that can be added."""
    available = [
        {
            "name": "prometheus",
            "description": "Prometheus monitoring and alerting",
            "category": "monitoring",
            "status": "available"
        },
        {
            "name": "jira",
            "description": "Jira issue tracking",
            "category": "ticketing",
            "status": "available"
        },
        {
            "name": "opsgenie",
            "description": "OpsGenie incident management",
            "category": "incident_management",
            "status": "coming_soon"
        },
        {
            "name": "aws",
            "description": "AWS services integration",
            "category": "cloud",
            "status": "available"
        },
        {
            "name": "grafana",
            "description": "Grafana dashboards and alerts",
            "category": "monitoring",
            "status": "available"
        }
    ]

    return JSONResponse(content={"integrations": available})
