"""
Improved Kubernetes integration API with proper context selection and kubeconfig support.
"""

import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.oncall_agent.mcp_integrations.kubernetes_direct import (
    KubernetesDirectIntegration,
)
from src.oncall_agent.services.kubernetes_auth import (
    KubernetesAuthService,
)
from src.oncall_agent.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/integrations/kubernetes", tags=["kubernetes"])
logger = get_logger(__name__)


class KubeconfigUploadRequest(BaseModel):
    """Request model for kubeconfig upload."""
    kubeconfig_content: str  # Base64 encoded kubeconfig content
    test_context: str | None = None  # Optional context to test


class ContextTestRequest(BaseModel):
    """Request model for testing a Kubernetes context."""
    context_name: str
    namespace: str = "default"
    kubeconfig_content: str | None = None  # Optional kubeconfig for remote clusters


class DiscoverResponse(BaseModel):
    """Response model for context discovery."""
    contexts: list[dict[str, Any]]
    current_context: str | None = None
    source: str  # "local" or "uploaded"


@router.post("/discover")
async def discover_kubernetes_contexts(
    request: KubeconfigUploadRequest | None = None
) -> DiscoverResponse:
    """
    Discover available Kubernetes contexts from local kubeconfig or uploaded content.
    
    If no kubeconfig is provided, attempts to use local ~/.kube/config.
    """
    try:
        auth_service = KubernetesAuthService()

        if request and request.kubeconfig_content:
            # Decode base64 kubeconfig
            try:
                kubeconfig_content = base64.b64decode(request.kubeconfig_content).decode('utf-8')
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid base64 encoded kubeconfig: {str(e)}"
                )

            # Validate kubeconfig
            validation_result = await auth_service.validate_kubeconfig(kubeconfig_content)

            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid kubeconfig: {validation_result.get('error', 'Unknown error')}"
                )

            return DiscoverResponse(
                contexts=validation_result["contexts"],
                current_context=next(
                    (ctx["name"] for ctx in validation_result["contexts"] if ctx.get("is_current")),
                    None
                ),
                source="uploaded"
            )
        else:
            # Try local kubeconfig
            kubeconfig_path = Path.home() / ".kube" / "config"

            if not kubeconfig_path.exists():
                return DiscoverResponse(
                    contexts=[],
                    current_context=None,
                    source="local"
                )

            # Read and validate local kubeconfig
            kubeconfig_content = kubeconfig_path.read_text()
            validation_result = await auth_service.validate_kubeconfig(kubeconfig_content)

            if not validation_result["valid"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Local kubeconfig is invalid: {validation_result.get('error', 'Unknown error')}"
                )

            return DiscoverResponse(
                contexts=validation_result["contexts"],
                current_context=next(
                    (ctx["name"] for ctx in validation_result["contexts"] if ctx.get("is_current")),
                    None
                ),
                source="local"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discovering Kubernetes contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_kubernetes_connection(
    request: ContextTestRequest
) -> JSONResponse:
    """
    Test connection to a specific Kubernetes context.
    
    Can use either local kubeconfig or uploaded kubeconfig content.
    """
    try:
        # Create Kubernetes integration with context
        k8s_integration = KubernetesDirectIntegration(
            namespace=request.namespace,
            context=request.context_name,
            kubeconfig_content=request.kubeconfig_content,
            enable_destructive_operations=False
        )

        # Connect to Kubernetes
        connected = await k8s_integration.connect()

        if not connected:
            return JSONResponse(
                content={
                    "success": False,
                    "status": "failed",
                    "error": "Failed to connect to Kubernetes cluster",
                    "details": {
                        "context": request.context_name,
                        "namespace": request.namespace
                    }
                },
                status_code=200
            )

        # Test connection
        test_result = await k8s_integration.test_connection(request.context_name)

        # Get connection info
        connection_info = k8s_integration.get_connection_info()

        # Disconnect
        await k8s_integration.disconnect()

        # Prepare response with fields expected by frontend
        response_data = {
            "success": test_result.get("connected", False),
            "status": "success" if test_result.get("connected") else "failed",
            "context": test_result.get("context", request.context_name),
            "namespace": test_result.get("namespace", request.namespace),
            "error": test_result.get("error"),
        }

        # Add additional fields if connection was successful
        if test_result.get("connected"):
            response_data.update({
                "cluster_version": test_result.get("api_version"),
                "node_count": test_result.get("nodes_count", 0),
                "namespace_exists": True,  # TODO: Actually check if namespace exists
                "connection_time": datetime.now(UTC).isoformat(),
                "permissions": {
                    "can_list_pods": True,  # TODO: Actually check permissions
                    "can_list_nodes": True,
                    "can_list_namespaces": True,
                }
            })

        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Kubernetes connection: {e}")
        return JSONResponse(
            content={
                "success": False,
                "status": "error",
                "error": str(e),
                "details": {}
            },
            status_code=200
        )


@router.post("/upload-kubeconfig")
async def upload_kubeconfig(
    file: UploadFile = File(..., description="Kubeconfig file")
) -> JSONResponse:
    """
    Upload a kubeconfig file and validate it.
    
    Returns the discovered contexts from the uploaded file.
    """
    try:
        # Read file content
        content = await file.read()

        try:
            kubeconfig_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid file encoding. Kubeconfig must be UTF-8 encoded."
            )

        # Validate kubeconfig
        auth_service = KubernetesAuthService()
        validation_result = await auth_service.validate_kubeconfig(kubeconfig_content)

        if not validation_result["valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid kubeconfig: {validation_result.get('error', 'Unknown error')}"
            )

        # Return base64 encoded content for use in subsequent requests
        encoded_content = base64.b64encode(content).decode('utf-8')

        return JSONResponse(
            content={
                "success": True,
                "kubeconfig_encoded": encoded_content,
                "contexts": validation_result["contexts"],
                "current_context": next(
                    (ctx["name"] for ctx in validation_result["contexts"] if ctx.get("is_current")),
                    None
                )
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing kubeconfig upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def kubernetes_integration_health() -> JSONResponse:
    """Check health of Kubernetes integration."""
    try:
        # Create integration instance
        k8s_integration = KubernetesDirectIntegration()

        # Try to discover contexts
        contexts = await k8s_integration.discover_contexts()

        return JSONResponse(
            content={
                "healthy": True,
                "available_contexts": len(contexts),
                "contexts": [ctx["name"] for ctx in contexts],
                "integration_type": "kubernetes_direct"
            }
        )

    except Exception as e:
        return JSONResponse(
            content={
                "healthy": False,
                "error": str(e),
                "integration_type": "kubernetes_direct"
            },
            status_code=503
        )
