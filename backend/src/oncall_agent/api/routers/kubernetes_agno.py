"""
API routes for Kubernetes Agno MCP integration.

Provides endpoints for:
- Testing K8s MCP connectivity
- Managing remote cluster connections
- Incident response with Agno agent
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.oncall_agent.agno_kubernetes_agent import DreamOpsK8sAgent
from src.oncall_agent.api.dependencies import get_db_pool
from src.oncall_agent.services.kubernetes_auth import AuthMethod, K8sCredentials
from src.oncall_agent.services.kubernetes_credentials import (
    KubernetesCredentialsService,
)
from src.oncall_agent.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/kubernetes/agno", tags=["kubernetes-agno"])
logger = get_logger(__name__)


class K8sCredentialsRequest(BaseModel):
    """Request model for K8s credentials."""
    auth_method: str  # "kubeconfig", "service_account", "client_certificate"
    cluster_name: str
    cluster_endpoint: str
    namespace: str = "default"

    # For kubeconfig method
    kubeconfig_data: str | None = None

    # For service account method
    service_account_token: str | None = None
    ca_certificate: str | None = None

    # For client certificate method
    client_certificate: str | None = None
    client_key: str | None = None

    # Additional options
    verify_ssl: bool = True
    proxy_url: str | None = None


class K8sIncidentRequest(BaseModel):
    """Request model for K8s incident processing."""
    alert_id: str
    title: str
    description: str
    severity: str
    metadata: dict[str, Any]


class AgnoTestRequest(BaseModel):
    """Request model for testing Agno integration."""
    use_remote_cluster: bool = False
    cluster_name: str | None = None
    test_query: str | None = "List all pods in the default namespace"


@router.post("/test-connection")
async def test_agno_connection(
    request: AgnoTestRequest,
    db_pool=Depends(get_db_pool)
) -> dict[str, Any]:
    """Test Agno K8s MCP integration connectivity."""
    try:
        agent = DreamOpsK8sAgent()

        # Initialize with MCP
        if request.use_remote_cluster and request.cluster_name:
            # Get credentials from database
            creds_service = KubernetesCredentialsService(db_pool)
            credentials = await creds_service.get_credentials(
                user_id=1,  # TODO: Get from auth
                cluster_name=request.cluster_name
            )

            if not credentials:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No credentials found for cluster: {request.cluster_name}"
                )

            initialized = await agent.initialize_with_mcp(credentials)
        else:
            # Use local MCP server
            initialized = await agent.initialize_with_mcp()

        if not initialized:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to initialize Agno agent with K8s MCP"
            )

        # Test the integration
        test_result = await agent.test_mcp_integration()

        # Run a test query if provided
        if request.test_query and agent.agent:
            try:
                query_result = await agent.agent.run(request.test_query)
                test_result["test_query_result"] = {
                    "query": request.test_query,
                    "success": True,
                    "response": str(query_result)[:500]  # Limit response size
                }
            except Exception as e:
                test_result["test_query_result"] = {
                    "query": request.test_query,
                    "success": False,
                    "error": str(e)
                }

        await agent.cleanup()

        return {
            "status": "success",
            "agno_integration": "active",
            "test_results": test_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Agno connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing Agno integration: {str(e)}"
        )


@router.post("/connect-cluster")
async def connect_remote_cluster(
    credentials: K8sCredentialsRequest,
    db_pool=Depends(get_db_pool)
) -> dict[str, Any]:
    """Connect to a remote Kubernetes cluster without local kubeconfig."""
    try:
        # Convert request to K8sCredentials
        auth_method = AuthMethod(credentials.auth_method)

        k8s_creds = K8sCredentials(
            auth_method=auth_method,
            cluster_endpoint=credentials.cluster_endpoint,
            cluster_name=credentials.cluster_name,
            kubeconfig_data=credentials.kubeconfig_data,
            service_account_token=credentials.service_account_token,
            ca_certificate=credentials.ca_certificate,
            client_certificate=credentials.client_certificate,
            client_key=credentials.client_key,
            namespace=credentials.namespace,
            verify_ssl=credentials.verify_ssl,
            proxy_url=credentials.proxy_url
        )

        # Initialize agent with credentials service
        creds_service = KubernetesCredentialsService(db_pool)
        agent = DreamOpsK8sAgent(credentials_service=creds_service)

        # Connect to remote cluster
        result = await agent.connect_remote_cluster(
            user_id=1,  # TODO: Get from auth
            credentials=k8s_creds
        )

        await agent.cleanup()

        if result.get("connected"):
            return {
                "status": "success",
                "cluster_name": credentials.cluster_name,
                "connection_result": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to cluster: {result.get('error')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting to remote cluster: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error connecting to cluster: {str(e)}"
        )


@router.get("/clusters")
async def list_clusters(db_pool=Depends(get_db_pool)) -> list[dict[str, Any]]:
    """List all available Kubernetes clusters."""
    try:
        creds_service = KubernetesCredentialsService(db_pool)
        agent = DreamOpsK8sAgent(credentials_service=creds_service)

        clusters = await agent.list_available_clusters(
            user_id=1  # TODO: Get from auth
        )

        return clusters

    except Exception as e:
        logger.error(f"Error listing clusters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing clusters: {str(e)}"
        )


@router.post("/process-incident")
async def process_k8s_incident(
    incident: K8sIncidentRequest,
    db_pool=Depends(get_db_pool)
) -> dict[str, Any]:
    """Process a Kubernetes incident using Agno agent."""
    try:
        # Create alert data from request
        alert_data = {
            "alert_id": incident.alert_id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity,
            "metadata": incident.metadata
        }

        # Initialize agent
        creds_service = KubernetesCredentialsService(db_pool)
        agent = DreamOpsK8sAgent(credentials_service=creds_service)

        # Check if we need to use a specific cluster
        cluster_name = incident.metadata.get("cluster")
        if cluster_name and cluster_name != "local":
            # Get credentials for remote cluster
            credentials = await creds_service.get_credentials(
                user_id=1,  # TODO: Get from auth
                cluster_name=cluster_name
            )
            if credentials:
                await agent.initialize_with_mcp(credentials)

        # Process the incident
        result = await agent.handle_pagerduty_alert(alert_data)

        await agent.cleanup()

        return {
            "status": "success",
            "incident_id": incident.alert_id,
            "processing_result": result
        }

    except Exception as e:
        logger.error(f"Error processing K8s incident: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing incident: {str(e)}"
        )


@router.get("/agent-status")
async def get_agent_status() -> dict[str, Any]:
    """Get current Agno agent status and configuration."""
    try:
        from src.oncall_agent.config import get_config
        config = get_config()

        return {
            "agno_version": "1.6.3",  # From pyproject.toml
            "k8s_integration": {
                "enabled": config.k8s_enabled,
                "mcp_server_url": config.k8s_mcp_server_url or "local",
                "yolo_mode": config.k8s_enable_destructive_operations,
                "namespace": config.k8s_namespace,
                "context": config.k8s_context
            },
            "supported_auth_methods": [
                "kubeconfig",
                "service_account",
                "client_certificate",
                "eks",
                "gke",
                "aks"
            ],
            "features": {
                "remote_clusters": True,
                "multi_cluster": True,
                "automated_remediation": True,
                "incident_response": True,
                "mcp_integration": True
            }
        }

    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent status: {str(e)}"
        )


@router.post("/test-remediation")
async def test_remediation_scenario(
    scenario: str,
    cluster_name: str | None = None,
    namespace: str = "default",
    db_pool=Depends(get_db_pool)
) -> dict[str, Any]:
    """Test a specific remediation scenario."""

    # Define test scenarios
    scenarios = {
        "pod_crash": {
            "title": "Pod CrashLoopBackOff Test",
            "description": "Pod test-app-123 is in CrashLoopBackOff state",
            "metadata": {"pod": "test-app-123", "namespace": namespace}
        },
        "oom_kill": {
            "title": "Pod OOMKilled Test",
            "description": "Pod test-app-456 was OOMKilled due to memory limits",
            "metadata": {"pod": "test-app-456", "namespace": namespace}
        },
        "image_pull": {
            "title": "ImagePullBackOff Test",
            "description": "Pod test-app-789 cannot pull image",
            "metadata": {"pod": "test-app-789", "namespace": namespace}
        }
    }

    if scenario not in scenarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scenario: {scenario}. Available: {list(scenarios.keys())}"
        )

    try:
        # Create test alert
        test_alert = scenarios[scenario]
        test_alert["alert_id"] = f"test-{scenario}-{datetime.utcnow().timestamp()}"
        test_alert["severity"] = "high"

        if cluster_name:
            test_alert["metadata"]["cluster"] = cluster_name

        # Process with agent
        creds_service = KubernetesCredentialsService(db_pool)
        agent = DreamOpsK8sAgent(credentials_service=creds_service)

        result = await agent.handle_pagerduty_alert(test_alert)

        await agent.cleanup()

        return {
            "status": "success",
            "scenario": scenario,
            "test_alert": test_alert,
            "remediation_result": result
        }

    except Exception as e:
        logger.error(f"Error testing remediation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing remediation: {str(e)}"
        )
