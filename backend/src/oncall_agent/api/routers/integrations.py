"""Integration management API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, File, Form, HTTPException, Path, Query, UploadFile
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
async def list_integrations(user_id: str = Query(None, description="User ID to check plan restrictions")) -> list[Integration]:
    """List all available integrations."""
    try:
        integrations = []
        agent = await get_agent_instance()
        
        # Import alert tracking to check user plan
        from src.oncall_agent.api.routers.alert_tracking import USER_DATA, INTEGRATION_RESTRICTIONS
        import os
        
        # Check if in development mode
        is_dev_mode = os.getenv("NEXT_PUBLIC_DEV_MODE", "false").lower() == "true" or os.getenv("NODE_ENV", "") == "development"
        
        # Get user's plan if user_id provided
        user_plan = "pro" if is_dev_mode else "free"  # Default to pro in dev mode
        if user_id and user_id in USER_DATA:
            user_plan = USER_DATA[user_id].get("account_tier", user_plan)
        
        # Get allowed integrations for the plan
        allowed_integrations = INTEGRATION_RESTRICTIONS.get(user_plan, [])

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
                    last_check=datetime.now(timezone.utc),
                    metrics={
                        "requests_per_minute": 42,
                        "error_rate": 0.02,
                        "avg_response_time_ms": 150
                    }
                )

            # Check if integration is allowed for user's plan
            is_allowed = name in allowed_integrations if user_id else True
            
            # Add plan restriction info to the integration
            integration_data = Integration(
                name=name,
                type=name,  # Could be more specific
                status=status if (config.enabled and is_allowed) else IntegrationStatus.DISCONNECTED,
                capabilities=capabilities,
                config=config,
                health=health
            )
            
            # Add custom fields for plan restrictions
            integration_dict = integration_data.model_dump()
            integration_dict["is_allowed"] = is_allowed
            integration_dict["requires_plan"] = "pro" if name not in ["kubernetes_mcp", "pagerduty"] else "free"
            integration_dict["user_plan"] = user_plan
            
            integrations.append(integration_dict)

        return integrations

    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_integration_templates() -> JSONResponse:
    """Get configuration templates for each integration type."""
    templates = {
        "pagerduty": {
            "integration_url": "https://events.pagerduty.com/integration/YOUR_INTEGRATION_KEY/enqueue",
            "webhook_secret": "optional_webhook_secret_for_verification"
        },
        "kubernetes": {
            "contexts": ["production-cluster", "staging-cluster"],
            "namespaces": {"production-cluster": "default", "staging-cluster": "default"},
            "enable_destructive_operations": False,
            "kubeconfig_path": "~/.kube/config"
        },
        "github": {
            "token": "ghp_YOUR_PERSONAL_ACCESS_TOKEN",
            "organization": "your-org",
            "repositories": ["repo1", "repo2"]
        },
        "notion": {
            "token": "secret_YOUR_NOTION_INTEGRATION_TOKEN",
            "workspace_id": "YOUR_WORKSPACE_ID"
        },
        "grafana": {
            "url": "https://your-grafana-instance.com",
            "api_key": "YOUR_GRAFANA_API_KEY"
        }
    }

    return JSONResponse(content={"templates": templates})


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
            last_check=datetime.now(timezone.utc),
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
        # Test actual Kubernetes MCP integration
        from src.oncall_agent.config import get_config
        config = get_config()

        # Always use Manusa MCP integration
        from src.oncall_agent.mcp_integrations.kubernetes_manusa_mcp import (
            KubernetesManusaMCPIntegration,
        )

        k8s = KubernetesManusaMCPIntegration(
            namespace="default",
            enable_destructive_operations=config.k8s_enable_destructive_operations
        )

        # Try to connect and discover contexts
        try:
            contexts = await k8s.discover_contexts()
            await k8s.disconnect()  # Clean up

            return {
                "success": True,
                "tests": {
                    "mcp_server_connection": "pass",
                    "context_discovery": "pass",
                    "contexts_found": len(contexts)
                },
                "message": f"Kubernetes MCP integration working. Found {len(contexts)} contexts",
                "contexts": contexts[:5]  # Return first 5 contexts
            }
        except Exception as e:
                return {
                    "success": False,
                    "tests": {
                        "mcp_server_connection": "fail",
                        "error": str(e)
                    },
                    "message": f"Kubernetes MCP integration failed: {e}"
                }
        else:
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
            "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=i*5)).isoformat(),
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
        from src.oncall_agent.services.kubernetes_auth import KubernetesAuthService

        auth_service = KubernetesAuthService()

        # Try to read local kubeconfig if available
        from pathlib import Path

        kubeconfig_path = Path.home() / ".kube" / "config"
        if not kubeconfig_path.exists():
            return JSONResponse(content={"contexts": [], "error": "No local kubeconfig found"})

        kubeconfig_content = kubeconfig_path.read_text()
        validation_result = await auth_service.validate_kubeconfig(kubeconfig_content)

        if validation_result["valid"]:
            return JSONResponse(content={"contexts": validation_result["contexts"]})
        else:
            return JSONResponse(content={"contexts": [], "error": validation_result.get("error")})
    except Exception as e:
        logger.error(f"Error discovering Kubernetes contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kubernetes/test")
async def test_kubernetes_connection(
    context_name: str = Body(None, embed=True),
    namespace: str = Body("default", embed=True),
    credential_id: str = Body(None, embed=True),
    user_id: int = Body(..., embed=True)  # In production, get from auth
) -> JSONResponse:
    """Test connection to a specific Kubernetes cluster."""
    try:
        import asyncpg

        from src.oncall_agent.services.kubernetes_auth import KubernetesAuthService
        from src.oncall_agent.services.kubernetes_credentials import (
            KubernetesCredentialsService,
        )

        # In production, get DB pool from app state
        # For now, create a simple connection
        db_url = "postgresql://user:pass@localhost/dbname"  # Get from config
        pool = await asyncpg.create_pool(db_url)

        try:
            creds_service = KubernetesCredentialsService(pool)
            auth_service = KubernetesAuthService()

            # Get credentials if credential_id provided
            if credential_id:
                credentials = await creds_service.get_credentials(user_id, context_name)
                if not credentials:
                    raise HTTPException(status_code=404, detail="Credentials not found")

                # Test connection
                test_result = await auth_service.test_connection(credentials)

                # Update connection status
                await creds_service.update_connection_status(
                    credential_id,
                    "connected" if test_result["connected"] else "failed",
                    test_result.get("error")
                )

                return JSONResponse(content=test_result)
            else:
                # Legacy local kubeconfig test
                from src.oncall_agent.config import get_config
                config = get_config()

                # Always use Manusa MCP integration
                from src.oncall_agent.mcp_integrations.kubernetes_manusa_mcp import (
                    KubernetesManusaMCPIntegration,
                )
                k8s_integration = KubernetesManusaMCPIntegration()

                try:
                    test_result = await k8s_integration.test_connection(context_name, namespace)
                    return JSONResponse(content=test_result)
                finally:
                    # Ensure proper cleanup
                    await k8s_integration.disconnect()

        finally:
            await pool.close()

    except HTTPException:
        raise
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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
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
        from src.oncall_agent.config import get_config
        config = get_config()

        # Always use Manusa MCP integration
        from src.oncall_agent.mcp_integrations.kubernetes_manusa_mcp import (
            KubernetesManusaMCPIntegration,
        )
        k8s_integration = KubernetesManusaMCPIntegration()

        # Note: verify_permissions method needs to be implemented
        # For now, return basic permissions check
        return JSONResponse(content={
            "permissions": {
                "read": True,
                "write": config.k8s_enable_destructive_operations
            }
        })
    except Exception as e:
        logger.error(f"Error verifying Kubernetes permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kubernetes/cluster-info")
async def get_kubernetes_cluster_info(
    context_name: str = Query(...)
) -> JSONResponse:
    """Get detailed information about a Kubernetes cluster."""
    try:
        from src.oncall_agent.config import get_config
        config = get_config()

        # Always use Manusa MCP integration
        from src.oncall_agent.mcp_integrations.kubernetes_manusa_mcp import (
            KubernetesManusaMCPIntegration,
        )
        k8s_integration = KubernetesManusaMCPIntegration()
        cluster_info = await k8s_integration.get_cluster_info(context_name)

        return JSONResponse(content=cluster_info)
    except Exception as e:
        logger.error(f"Error getting Kubernetes cluster info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# New endpoints for multiple authentication methods
@router.post("/kubernetes/auth/kubeconfig")
async def authenticate_with_kubeconfig(
    kubeconfig_content: str = Body(..., description="Kubeconfig file content"),
    context_name: str = Body(None, description="Specific context to use"),
    namespace: str = Body("default", description="Default namespace")
) -> JSONResponse:
    """Authenticate to Kubernetes cluster using kubeconfig file."""
    try:
        from src.oncall_agent.services.kubernetes_auth import (
            AuthMethod,
            K8sCredentials,
            KubernetesAuthService,
        )

        auth_service = KubernetesAuthService()

        # Always use MCP server for validation
        from src.oncall_agent.mcp_integrations.kubernetes_manusa_mcp import (
            KubernetesManusaMCPIntegration,
        )

        k8s_mcp = KubernetesManusaMCPIntegration()
        validation = await k8s_mcp.validate_kubeconfig(kubeconfig_content)
        if not validation.get("valid"):
            raise HTTPException(status_code=400, detail=validation.get("error", "Invalid kubeconfig"))

        # Find the context to use
        contexts = validation["contexts"]
        if not contexts:
            raise HTTPException(status_code=400, detail="No contexts found in kubeconfig")

        selected_context = None
        if context_name:
            selected_context = next((c for c in contexts if c["name"] == context_name), None)
            if not selected_context:
                raise HTTPException(status_code=400, detail=f"Context '{context_name}' not found")
        else:
            # Use current context or first available
            selected_context = next((c for c in contexts if c["is_current"]), contexts[0])

        # Create credentials
        credentials = K8sCredentials(
            auth_method=AuthMethod.KUBECONFIG,
            cluster_endpoint=selected_context["server"],
            cluster_name=selected_context["cluster"],
            kubeconfig_data=kubeconfig_content,
            namespace=namespace
        )

        # Test connection using MCP server
        test_result = await k8s_mcp.test_connection(kubeconfig_content, selected_context["name"])
        if not test_result.get("connected"):
            raise HTTPException(status_code=400, detail=test_result.get("error", "Connection failed"))

        # Save credentials to database
        import asyncpg

        from src.oncall_agent.services.kubernetes_credentials import (
            KubernetesCredentialsService,
        )

        # In production, get from app state and auth
        user_id = 1  # Get from authenticated user
        db_url = "postgresql://user:pass@localhost/dbname"  # Get from config
        pool = await asyncpg.create_pool(db_url)

        try:
            creds_service = KubernetesCredentialsService(pool)
            credential_id = await creds_service.save_credentials(user_id, credentials, test_result)

            return JSONResponse(content={
                "success": True,
                "credential_id": credential_id,
                "context": selected_context["name"],
                "cluster": selected_context["cluster"],
                "connected": test_result["connected"],
                "cluster_version": test_result.get("cluster_version")
            })
        finally:
            await pool.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating with kubeconfig: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kubernetes/auth/service-account")
async def authenticate_with_service_account(
    cluster_endpoint: str = Body(..., description="Kubernetes API server endpoint"),
    service_account_token: str = Body(..., description="Service account bearer token"),
    ca_certificate: str = Body(None, description="Cluster CA certificate (PEM format)"),
    cluster_name: str = Body(..., description="Cluster name for identification"),
    namespace: str = Body("default", description="Default namespace"),
    verify_ssl: bool = Body(True, description="Verify SSL certificates")
) -> JSONResponse:
    """Authenticate to Kubernetes cluster using service account token."""
    try:
        from src.oncall_agent.services.kubernetes_auth import (
            AuthMethod,
            K8sCredentials,
            KubernetesAuthService,
        )

        auth_service = KubernetesAuthService()

        # Create credentials
        credentials = K8sCredentials(
            auth_method=AuthMethod.SERVICE_ACCOUNT,
            cluster_endpoint=cluster_endpoint,
            cluster_name=cluster_name,
            service_account_token=service_account_token,
            ca_certificate=ca_certificate,
            namespace=namespace,
            verify_ssl=verify_ssl
        )

        # Test connection
        test_result = await auth_service.test_connection(credentials)
        if not test_result["connected"]:
            raise HTTPException(status_code=400, detail=test_result.get("error", "Connection failed"))

        # Verify permissions
        permissions = await auth_service.verify_permissions(credentials)

        # Save credentials to database
        import asyncpg

        from src.oncall_agent.services.kubernetes_credentials import (
            KubernetesCredentialsService,
        )

        # In production, get from app state and auth
        user_id = 1  # Get from authenticated user
        db_url = "postgresql://user:pass@localhost/dbname"  # Get from config
        pool = await asyncpg.create_pool(db_url)

        try:
            creds_service = KubernetesCredentialsService(pool)
            credential_id = await creds_service.save_credentials(user_id, credentials, test_result)

            return JSONResponse(content={
                "success": True,
                "credential_id": credential_id,
                "cluster": cluster_name,
                "connected": test_result["connected"],
                "cluster_version": test_result.get("cluster_version"),
                "permissions": permissions
            })
        finally:
            await pool.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating with service account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kubernetes/auth/client-cert")
async def authenticate_with_client_certificate(
    cluster_endpoint: str = Body(..., description="Kubernetes API server endpoint"),
    client_certificate: str = Body(..., description="Client certificate (PEM format)"),
    client_key: str = Body(..., description="Client private key (PEM format)"),
    ca_certificate: str = Body(None, description="Cluster CA certificate (PEM format)"),
    cluster_name: str = Body(..., description="Cluster name for identification"),
    namespace: str = Body("default", description="Default namespace"),
    verify_ssl: bool = Body(True, description="Verify SSL certificates")
) -> JSONResponse:
    """Authenticate to Kubernetes cluster using client certificate."""
    try:
        from src.oncall_agent.services.kubernetes_auth import (
            AuthMethod,
            K8sCredentials,
            KubernetesAuthService,
        )

        auth_service = KubernetesAuthService()

        # Create credentials
        credentials = K8sCredentials(
            auth_method=AuthMethod.CLIENT_CERT,
            cluster_endpoint=cluster_endpoint,
            cluster_name=cluster_name,
            client_certificate=client_certificate,
            client_key=client_key,
            ca_certificate=ca_certificate,
            namespace=namespace,
            verify_ssl=verify_ssl
        )

        # Test connection
        test_result = await auth_service.test_connection(credentials)
        if not test_result["connected"]:
            raise HTTPException(status_code=400, detail=test_result.get("error", "Connection failed"))

        # Get cluster info
        cluster_info = await auth_service.get_cluster_info(credentials)

        # Save credentials to database
        import asyncpg

        from src.oncall_agent.services.kubernetes_credentials import (
            KubernetesCredentialsService,
        )

        # In production, get from app state and auth
        user_id = 1  # Get from authenticated user
        db_url = "postgresql://user:pass@localhost/dbname"  # Get from config
        pool = await asyncpg.create_pool(db_url)

        try:
            creds_service = KubernetesCredentialsService(pool)
            credential_id = await creds_service.save_credentials(user_id, credentials, test_result)

            return JSONResponse(content={
                "success": True,
                "credential_id": credential_id,
                "cluster": cluster_name,
                "connected": test_result["connected"],
                "cluster_info": cluster_info
            })
        finally:
            await pool.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating with client certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kubernetes/upload-kubeconfig")
async def upload_kubeconfig(
    file: UploadFile = File(..., description="Kubeconfig file"),
    context_name: str = Form(None, description="Specific context to use"),
    namespace: str = Form("default", description="Default namespace")
) -> JSONResponse:
    """Upload and validate kubeconfig file."""
    try:

        # Read file content
        content = await file.read()
        kubeconfig_content = content.decode('utf-8')

        # Use the kubeconfig authentication endpoint
        return await authenticate_with_kubeconfig(
            kubeconfig_content=kubeconfig_content,
            context_name=context_name,
            namespace=namespace
        )

    except Exception as e:
        logger.error(f"Error uploading kubeconfig: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kubernetes/clusters")
async def list_saved_clusters(
    user_id: int = Query(..., description="User ID")  # In production, get from auth
) -> JSONResponse:
    """List all saved Kubernetes clusters for a user."""
    try:
        import asyncpg

        from src.oncall_agent.services.kubernetes_credentials import (
            KubernetesCredentialsService,
        )

        # In production, get from app state
        db_url = "postgresql://user:pass@localhost/dbname"  # Get from config
        pool = await asyncpg.create_pool(db_url)

        try:
            creds_service = KubernetesCredentialsService(pool)
            clusters = await creds_service.list_clusters(user_id)

            return JSONResponse(content={"clusters": clusters})

        finally:
            await pool.close()

    except Exception as e:
        logger.error(f"Error listing clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/kubernetes/clusters/{credential_id}")
async def delete_cluster_credentials(
    credential_id: str = Path(..., description="Credential ID"),
    user_id: int = Query(..., description="User ID")  # In production, get from auth
) -> JSONResponse:
    """Delete saved Kubernetes cluster credentials."""
    try:
        import asyncpg

        from src.oncall_agent.services.kubernetes_credentials import (
            KubernetesCredentialsService,
        )

        # In production, get from app state
        db_url = "postgresql://user:pass@localhost/dbname"  # Get from config
        pool = await asyncpg.create_pool(db_url)

        try:
            creds_service = KubernetesCredentialsService(pool)
            success = await creds_service.delete_credentials(user_id, credential_id)

            if not success:
                raise HTTPException(status_code=404, detail="Credentials not found")

            return JSONResponse(content={"success": True, "message": "Credentials deleted successfully"})

        finally:
            await pool.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grafana/requirements")
async def get_grafana_requirements() -> dict[str, Any]:
    """Get Grafana integration requirements."""
    import os
    
    # Get environment variables for placeholders
    grafana_url = os.getenv("GRAFANA_MCP_URL", os.getenv("GRAFANA_URL", "https://your-grafana-instance.com"))
    grafana_api_key = os.getenv("GRAFANA_MCP_API_KEY", os.getenv("GRAFANA_API_KEY", ""))
    grafana_api_key_hint = grafana_api_key[:10] + "..." if grafana_api_key else "glsa_xxxxxxxxxxxx"
    
    return {
        "fields": [
            {
                "name": "url",
                "label": "Grafana URL",
                "type": "url",
                "required": True,
                "placeholder": grafana_url,
                "description": "The base URL of your Grafana instance",
                "envVar": "GRAFANA_MCP_URL or GRAFANA_URL"
            },
            {
                "name": "apiKey",
                "label": "API Key",
                "type": "password",
                "required": True,
                "placeholder": grafana_api_key_hint,
                "description": "Grafana API key with appropriate permissions",
                "envVar": "GRAFANA_MCP_API_KEY or GRAFANA_API_KEY"
            }
        ],
        "permissions": [
            "Read access to dashboards",
            "Read access to datasources",
            "Read access to alerts (optional)",
            "Read access to organizations"
        ],
        "documentation": "https://grafana.com/docs/grafana/latest/developers/http_api/auth/"
    }


