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
    "kubernetes_mcp": IntegrationConfig(
        enabled=True,
        config={
            "cluster": "production",
            "namespace": "default",
            "kubeconfig_path": "/etc/kubernetes/config"
        }
    ),
    "notion": IntegrationConfig(
        enabled=False,
        config={
            "token": "",
            "database_id": "",
            "version": "2022-06-28"
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
                capabilities_dict = await integration.get_capabilities()
                # Convert capabilities dict to list of strings
                capabilities = []
                if capabilities_dict:
                    if isinstance(capabilities_dict, dict):
                        # Extract all capability lists and flatten them
                        for category, items in capabilities_dict.items():
                            if isinstance(items, list):
                                capabilities.extend(items)
                        # If no capabilities found, use category names
                        if not capabilities:
                            capabilities = list(capabilities_dict.keys())
                    elif isinstance(capabilities_dict, list):
                        capabilities = capabilities_dict

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
        capabilities_dict = await integration.get_capabilities()
        # Convert capabilities dict to list of strings
        capabilities = []
        if capabilities_dict:
            if isinstance(capabilities_dict, dict):
                # Extract all capability lists and flatten them
                for category, items in capabilities_dict.items():
                    if isinstance(items, list):
                        capabilities.extend(items)
                # If no capabilities found, use category names
                if not capabilities:
                    capabilities = list(capabilities_dict.keys())
            elif isinstance(capabilities_dict, list):
                capabilities = capabilities_dict

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


# Kubernetes-specific endpoints
@router.get("/kubernetes/discover")
async def discover_kubernetes_contexts() -> JSONResponse:
    """Discover available Kubernetes contexts from kubeconfig."""
    try:
        from src.oncall_agent.mcp_integrations.kubernetes_enhanced import (
            EnhancedKubernetesMCPIntegration,
        )

        # Create temporary integration instance for discovery
        k8s_integration = EnhancedKubernetesMCPIntegration()
        contexts = await k8s_integration.discover_contexts()

        return JSONResponse(content={"contexts": contexts})
    except Exception as e:
        logger.error(f"Error discovering Kubernetes contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kubernetes/test")
async def test_kubernetes_connection(
    context_name: str = Body(..., embed=True),
    namespace: str = Body("default", embed=True)
) -> JSONResponse:
    """Test connection to a specific Kubernetes cluster."""
    try:
        from src.oncall_agent.mcp_integrations.kubernetes_enhanced import (
            EnhancedKubernetesMCPIntegration,
        )

        # Create temporary integration instance for testing
        k8s_integration = EnhancedKubernetesMCPIntegration()
        test_result = await k8s_integration.test_connection(context_name, namespace)

        return JSONResponse(content=test_result)
    except Exception as e:
        logger.error(f"Error testing Kubernetes connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kubernetes/configs")
async def list_kubernetes_configs() -> JSONResponse:
    """List saved Kubernetes configurations."""
    # In a real implementation, this would fetch from a database
    # For now, return mock data or current config
    configs = []

    if "kubernetes" in INTEGRATION_CONFIGS:
        k8s_config = INTEGRATION_CONFIGS["kubernetes"]
        configs.append({
            "id": "default",
            "name": "Default Cluster",
            "context": k8s_config.config.get("cluster", "unknown"),
            "namespace": k8s_config.config.get("namespace", "default"),
            "enabled": k8s_config.enabled,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        })

    return JSONResponse(content={"configs": configs})


@router.post("/kubernetes/configs")
async def save_kubernetes_config(
    name: str = Body(...),
    context: str = Body(...),
    namespace: str = Body("default"),
    enable_destructive: bool = Body(False),
    kubeconfig_path: str = Body(None)
) -> JSONResponse:
    """Save a new Kubernetes configuration."""
    try:
        # In a real implementation, this would save to a database
        # For now, update the in-memory config
        config_id = f"k8s-{datetime.now().timestamp()}"

        INTEGRATION_CONFIGS["kubernetes"] = IntegrationConfig(
            enabled=True,
            config={
                "id": config_id,
                "name": name,
                "context": context,
                "namespace": namespace,
                "enable_destructive": enable_destructive,
                "kubeconfig_path": kubeconfig_path or "~/.kube/config"
            }
        )

        # If agent is available, reconnect with new config
        agent = await get_agent_instance()
        if agent and "kubernetes" in agent.mcp_integrations:
            k8s = agent.mcp_integrations["kubernetes"]
            await k8s.disconnect()
            # Update with new config
            k8s.context_name = context
            k8s.namespace = namespace
            k8s.enable_destructive = enable_destructive
            await k8s.connect()

        return JSONResponse(content={
            "success": True,
            "config_id": config_id,
            "message": "Kubernetes configuration saved successfully"
        })
    except Exception as e:
        logger.error(f"Error saving Kubernetes config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/kubernetes/configs/{config_id}")
async def update_kubernetes_config(
    config_id: str = Path(...),
    name: str = Body(None),
    context: str = Body(None),
    namespace: str = Body(None),
    enable_destructive: bool = Body(None),
    enabled: bool = Body(None)
) -> JSONResponse:
    """Update an existing Kubernetes configuration."""
    try:
        # In a real implementation, this would update in database
        if "kubernetes" not in INTEGRATION_CONFIGS:
            raise HTTPException(status_code=404, detail="Kubernetes configuration not found")

        k8s_config = INTEGRATION_CONFIGS["kubernetes"]

        # Update fields if provided
        if name is not None:
            k8s_config.config["name"] = name
        if context is not None:
            k8s_config.config["context"] = context
        if namespace is not None:
            k8s_config.config["namespace"] = namespace
        if enable_destructive is not None:
            k8s_config.config["enable_destructive"] = enable_destructive
        if enabled is not None:
            k8s_config.enabled = enabled

        # Reconnect if agent is available
        agent = await get_agent_instance()
        if agent and "kubernetes" in agent.mcp_integrations:
            k8s = agent.mcp_integrations["kubernetes"]
            await k8s.disconnect()
            if k8s_config.enabled:
                k8s.context_name = k8s_config.config.get("context")
                k8s.namespace = k8s_config.config.get("namespace", "default")
                k8s.enable_destructive = k8s_config.config.get("enable_destructive", False)
                await k8s.connect()

        return JSONResponse(content={
            "success": True,
            "message": "Kubernetes configuration updated successfully"
        })
    except Exception as e:
        logger.error(f"Error updating Kubernetes config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/kubernetes/configs/{config_id}")
async def delete_kubernetes_config(config_id: str = Path(...)) -> JSONResponse:
    """Delete a Kubernetes configuration."""
    try:
        # In a real implementation, this would delete from database
        # For now, just disable it
        if "kubernetes" in INTEGRATION_CONFIGS:
            INTEGRATION_CONFIGS["kubernetes"].enabled = False

            # Disconnect if agent is available
            agent = await get_agent_instance()
            if agent and "kubernetes" in agent.mcp_integrations:
                await agent.mcp_integrations["kubernetes"].disconnect()

        return JSONResponse(content={
            "success": True,
            "message": "Kubernetes configuration deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting Kubernetes config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kubernetes/health")
async def get_kubernetes_health() -> JSONResponse:
    """Get Kubernetes integration health status."""
    try:
        agent = await get_agent_instance()

        if not agent or "kubernetes" not in agent.mcp_integrations:
            return JSONResponse(content={
                "status": "not_initialized",
                "message": "Kubernetes integration not initialized"
            })

        k8s = agent.mcp_integrations["kubernetes"]
        is_healthy = await k8s.health_check()

        # Get connection info if using enhanced integration
        connection_info = {}
        if hasattr(k8s, 'get_connection_info'):
            connection_info = k8s.get_connection_info()

        return JSONResponse(content={
            "status": "healthy" if is_healthy else "unhealthy",
            "connected": k8s.connected,
            "connection_time": k8s.connection_time.isoformat() if k8s.connection_time else None,
            "connection_info": connection_info,
            "capabilities": await k8s.get_capabilities() if is_healthy else []
        })
    except Exception as e:
        logger.error(f"Error checking Kubernetes health: {e}")
        return JSONResponse(content={
            "status": "error",
            "error": str(e)
        })


@router.post("/kubernetes/verify-permissions")
async def verify_kubernetes_permissions(
    context_name: str = Body(..., embed=True)
) -> JSONResponse:
    """Verify RBAC permissions for a Kubernetes context."""
    try:
        from src.oncall_agent.mcp_integrations.kubernetes_enhanced import (
            EnhancedKubernetesMCPIntegration,
        )

        # Create temporary integration instance
        k8s_integration = EnhancedKubernetesMCPIntegration()
        permissions = await k8s_integration.verify_permissions(context_name)

        return JSONResponse(content=permissions)
    except Exception as e:
        logger.error(f"Error verifying Kubernetes permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kubernetes/cluster-info")
async def get_kubernetes_cluster_info(
    context_name: str = Query(...)
) -> JSONResponse:
    """Get detailed information about a Kubernetes cluster."""
    try:
        from src.oncall_agent.mcp_integrations.kubernetes_enhanced import (
            EnhancedKubernetesMCPIntegration,
        )

        # Create temporary integration instance
        k8s_integration = EnhancedKubernetesMCPIntegration()
        cluster_info = await k8s_integration.get_cluster_info(context_name)

        return JSONResponse(content=cluster_info)
    except Exception as e:
        logger.error(f"Error getting Kubernetes cluster info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
