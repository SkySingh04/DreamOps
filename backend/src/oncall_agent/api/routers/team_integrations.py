"""Team-scoped integration management API endpoints."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger
from src.oncall_agent.security.firebase_auth import get_current_firebase_user, FirebaseUser
from .auth_setup import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["team-integrations"])

# Get encryption key from config
config = get_config()
# In production, this should come from a secure key management service
ENCRYPTION_KEY = config.encryption_key if hasattr(config, 'encryption_key') else Fernet.generate_key()
fernet = Fernet(ENCRYPTION_KEY)


# Mock database storage (replace with actual database in production)
TEAM_INTEGRATIONS_DB: dict[int, list[dict[str, Any]]] = {}
INTEGRATION_AUDIT_LOGS_DB: list[dict[str, Any]] = []


def encrypt_config(config: dict[str, Any]) -> str:
    """Encrypt sensitive configuration data."""
    encrypted: str = fernet.encrypt(json.dumps(config).encode()).decode()
    return encrypted


def decrypt_config(encrypted_config: str) -> dict[str, Any]:
    """Decrypt sensitive configuration data."""
    decrypted: dict[str, Any] = json.loads(fernet.decrypt(encrypted_config.encode()).decode())
    return decrypted


async def get_current_user_id(user: dict = Depends(get_current_user)) -> int:
    """Get current user ID from authenticated user."""
    return user["id"]


async def get_current_team_id(user: dict = Depends(get_current_user)) -> int:
    """Get current team ID from authenticated user."""
    return user["team_id"]


class TeamIntegrationCreate(BaseModel):
    """Model for creating a team integration."""
    integration_type: str
    config: dict[str, Any]
    is_required: bool = False


class TeamIntegrationUpdate(BaseModel):
    """Model for updating a team integration."""
    config: dict[str, Any] | None = None
    is_enabled: bool | None = None


class IntegrationTestRequest(BaseModel):
    """Model for integration test request."""
    integration_type: str
    config: dict[str, Any]


@router.get("/teams/{team_id}/integrations")
async def list_team_integrations(
    team_id: int = Path(..., description="Team ID"),
    current_user_id: int = Depends(get_current_user_id)
) -> JSONResponse:
    """List all integrations for a team."""
    try:
        # Get team integrations from mock database
        integrations = TEAM_INTEGRATIONS_DB.get(team_id, [])

        # Decrypt configs for response
        for integration in integrations:
            if 'config_encrypted' in integration:
                integration['config'] = decrypt_config(integration['config_encrypted'])
                # Mask sensitive fields
                integration['config'] = mask_sensitive_fields(integration['config'])
                del integration['config_encrypted']

        return JSONResponse(content={
            "integrations": integrations,
            "total": len(integrations)
        })
    except Exception as e:
        logger.error(f"Error listing team integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teams/{team_id}/integrations")
async def create_team_integration(
    team_id: int = Path(..., description="Team ID"),
    integration: TeamIntegrationCreate = Body(...),
    current_user_id: int = Depends(get_current_user_id)
) -> JSONResponse:
    """Create a new integration for a team."""
    try:
        # Validate integration type
        valid_types = ['pagerduty', 'kubernetes', 'github', 'notion', 'grafana']
        if integration.integration_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid integration type: {integration.integration_type}")

        # Check if integration already exists
        team_integrations = TEAM_INTEGRATIONS_DB.get(team_id, [])
        existing = next((i for i in team_integrations if i['integration_type'] == integration.integration_type), None)
        if existing:
            raise HTTPException(status_code=409, detail="Integration already exists for this team")

        # Create new integration
        integration_id = str(uuid4())
        new_integration = {
            "id": integration_id,
            "team_id": team_id,
            "integration_type": integration.integration_type,
            "config_encrypted": encrypt_config(integration.config),
            "is_enabled": True,
            "is_required": integration.is_required,
            "created_by": current_user_id,
            "updated_by": current_user_id,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat()
        }

        # Save to mock database
        if team_id not in TEAM_INTEGRATIONS_DB:
            TEAM_INTEGRATIONS_DB[team_id] = []
        TEAM_INTEGRATIONS_DB[team_id].append(new_integration)

        # Create audit log
        audit_log = {
            "id": len(INTEGRATION_AUDIT_LOGS_DB) + 1,
            "team_id": team_id,
            "integration_id": integration_id,
            "action": "created",
            "performed_by": current_user_id,
            "new_config": encrypt_config(integration.config),
            "result": "success",
            "created_at": datetime.now(UTC).isoformat()
        }
        INTEGRATION_AUDIT_LOGS_DB.append(audit_log)

        # Return created integration (without encrypted config)
        response_integration = new_integration.copy()
        response_integration['config'] = mask_sensitive_fields(integration.config)
        del response_integration['config_encrypted']

        return JSONResponse(
            content={
                "success": True,
                "integration": response_integration,
                "message": f"{integration.integration_type} integration created successfully"
            },
            status_code=201
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating team integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/teams/{team_id}/integrations/{integration_id}")
async def update_team_integration(
    team_id: int = Path(..., description="Team ID"),
    integration_id: str = Path(..., description="Integration ID"),
    update: TeamIntegrationUpdate = Body(...),
    current_user_id: int = Depends(get_current_user_id)
) -> JSONResponse:
    """Update a team integration."""
    try:
        # Find integration
        team_integrations = TEAM_INTEGRATIONS_DB.get(team_id, [])
        integration = next((i for i in team_integrations if i['id'] == integration_id), None)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Store previous config for audit
        previous_config = decrypt_config(integration['config_encrypted'])

        # Update fields
        if update.config is not None:
            integration['config_encrypted'] = encrypt_config(update.config)
        if update.is_enabled is not None:
            integration['is_enabled'] = update.is_enabled

        integration['updated_by'] = current_user_id
        integration['updated_at'] = datetime.now(UTC).isoformat()

        # Update last test status if disabling
        if update.is_enabled is False:
            integration['last_test_status'] = None
            integration['last_test_at'] = None

        # Create audit log
        audit_log = {
            "id": len(INTEGRATION_AUDIT_LOGS_DB) + 1,
            "team_id": team_id,
            "integration_id": integration_id,
            "action": "disabled" if update.is_enabled is False else "updated",
            "performed_by": current_user_id,
            "previous_config": encrypt_config(previous_config),
            "new_config": integration['config_encrypted'] if update.config else None,
            "result": "success",
            "created_at": datetime.now(UTC).isoformat()
        }
        INTEGRATION_AUDIT_LOGS_DB.append(audit_log)

        # Return updated integration
        response_integration = integration.copy()
        response_integration['config'] = mask_sensitive_fields(decrypt_config(integration['config_encrypted']))
        del response_integration['config_encrypted']

        return JSONResponse(content={
            "success": True,
            "integration": response_integration,
            "message": "Integration updated successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/teams/{team_id}/integrations/{integration_id}")
async def delete_team_integration(
    team_id: int = Path(..., description="Team ID"),
    integration_id: str = Path(..., description="Integration ID"),
    current_user_id: int = Depends(get_current_user_id)
) -> JSONResponse:
    """Delete a team integration."""
    try:
        # Find integration
        team_integrations = TEAM_INTEGRATIONS_DB.get(team_id, [])
        integration = next((i for i in team_integrations if i['id'] == integration_id), None)
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Check if it's a required integration
        if integration.get('is_required', False):
            raise HTTPException(status_code=400, detail="Cannot delete required integration")

        # Remove from database
        TEAM_INTEGRATIONS_DB[team_id] = [i for i in team_integrations if i['id'] != integration_id]

        # Create audit log
        audit_log = {
            "id": len(INTEGRATION_AUDIT_LOGS_DB) + 1,
            "team_id": team_id,
            "integration_id": integration_id,
            "action": "deleted",
            "performed_by": current_user_id,
            "result": "success",
            "created_at": datetime.now(UTC).isoformat()
        }
        INTEGRATION_AUDIT_LOGS_DB.append(audit_log)

        return JSONResponse(content={
            "success": True,
            "message": "Integration deleted successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Integration Testing Endpoints

@router.post("/integrations/test/{integration_type}")
async def test_integration(
    integration_type: str = Path(..., description="Integration type"),
    test_request: IntegrationTestRequest = Body(...),
    current_user_id: int = Depends(get_current_user_id)
) -> JSONResponse:
    """Test an integration configuration."""
    try:
        # Perform integration-specific tests
        test_result = await perform_integration_test(integration_type, test_request.config)

        return JSONResponse(content=test_result)
    except Exception as e:
        logger.error(f"Error testing {integration_type} integration: {e}")
        return JSONResponse(
            content={
                "success": False,
                "status": "failed",
                "error": str(e),
                "details": {}
            },
            status_code=200  # Return 200 even on test failure
        )


async def perform_integration_test(integration_type: str, config: dict[str, Any]) -> dict[str, Any]:
    """Perform integration-specific connection tests."""
    if integration_type == "pagerduty":
        return await test_pagerduty_integration(config)
    elif integration_type == "kubernetes":
        return await test_kubernetes_integration(config)
    elif integration_type == "github":
        return await test_github_integration(config)
    elif integration_type == "notion":
        return await test_notion_integration(config)
    elif integration_type == "grafana":
        return await test_grafana_integration(config)
    else:
        raise ValueError(f"Unknown integration type: {integration_type}")


async def test_pagerduty_integration(config: dict[str, Any]) -> dict[str, Any]:
    """Test PagerDuty integration."""
    # In production, this would make actual API calls
    # For now, return mock success
    return {
        "success": True,
        "status": "success",
        "details": {
            "api_key_valid": True,
            "services_accessible": True,
            "webhook_configured": True,
            "permissions": ["incidents.read", "incidents.write", "services.read"]
        },
        "latency_ms": 142
    }


async def test_kubernetes_integration(config: dict[str, Any]) -> dict[str, Any]:
    """Test Kubernetes integration."""
    try:
        from src.oncall_agent.mcp_integrations.kubernetes_enhanced import (
            EnhancedKubernetesMCPIntegration,
        )

        # Create temporary integration instance
        k8s = EnhancedKubernetesMCPIntegration()

        # Discover contexts first if testing multiple contexts
        contexts = config.get('contexts', [])
        if contexts:
            # Discover available contexts
            await k8s.discover_contexts()

            # Test first context
            context = contexts[0] if contexts else 'default'
            namespace = config.get('namespaces', {}).get(context, 'default')
        else:
            # Single context mode
            context = config.get('context', 'default')
            namespace = config.get('namespace', 'default')

        test_result = await k8s.test_connection(context, namespace)

        return {
            "success": test_result.get('success', False),
            "status": "success" if test_result.get('success') else "failed",
            "details": test_result,
            "latency_ms": test_result.get('latency_ms', 0)
        }
    except Exception as e:
        return {
            "success": False,
            "status": "failed",
            "error": str(e),
            "details": {}
        }


async def test_github_integration(config: dict[str, Any]) -> dict[str, Any]:
    """Test GitHub integration."""
    # Mock test for GitHub
    return {
        "success": True,
        "status": "success",
        "details": {
            "token_valid": True,
            "org_access": True,
            "repo_count": 12,
            "permissions": ["repo", "read:org", "write:issue"]
        },
        "latency_ms": 89
    }


async def test_notion_integration(config: dict[str, Any]) -> dict[str, Any]:
    """Test Notion integration."""
    # Mock test for Notion
    return {
        "success": True,
        "status": "success",
        "details": {
            "token_valid": True,
            "workspace_access": True,
            "database_count": 5,
            "page_count": 42
        },
        "latency_ms": 234
    }


async def test_grafana_integration(config: dict[str, Any]) -> dict[str, Any]:
    """Test Grafana integration."""
    # Mock test for Grafana
    return {
        "success": True,
        "status": "success",
        "details": {
            "api_key_valid": True,
            "dashboards_accessible": True,
            "datasources_count": 3,
            "alerts_enabled": True
        },
        "latency_ms": 167
    }


@router.post("/teams/{team_id}/integrations/test-all")
async def test_all_team_integrations(
    team_id: int = Path(..., description="Team ID"),
    current_user_id: int = Depends(get_current_user_id)
) -> JSONResponse:
    """Test all integrations for a team."""
    try:
        # Get team integrations
        team_integrations = TEAM_INTEGRATIONS_DB.get(team_id, [])

        results = []
        for integration in team_integrations:
            if not integration.get('is_enabled', True):
                results.append({
                    "integration_id": integration['id'],
                    "integration_type": integration['integration_type'],
                    "status": "skipped",
                    "reason": "Integration is disabled"
                })
                continue

            # Decrypt config and test
            config = decrypt_config(integration['config_encrypted'])
            test_result = await perform_integration_test(integration['integration_type'], config)

            # Update integration test status
            integration['last_test_at'] = datetime.now(UTC).isoformat()
            integration['last_test_status'] = "success" if test_result['success'] else "failed"
            integration['last_test_error'] = test_result.get('error')

            results.append({
                "integration_id": integration['id'],
                "integration_type": integration['integration_type'],
                "status": test_result['status'],
                "success": test_result['success'],
                "details": test_result.get('details', {}),
                "latency_ms": test_result.get('latency_ms')
            })

        # Summary
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        failed = sum(1 for r in results if r.get('status') == 'failed')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')

        return JSONResponse(content={
            "results": results,
            "summary": {
                "total": total,
                "successful": successful,
                "failed": failed,
                "skipped": skipped
            }
        })
    except Exception as e:
        logger.error(f"Error testing all team integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

def mask_sensitive_fields(config: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive fields in configuration."""
    masked_config = config.copy()
    sensitive_fields = ['api_key', 'token', 'secret', 'password', 'webhook_secret']

    for field in sensitive_fields:
        if field in masked_config:
            value = masked_config[field]
            if value and len(value) > 8:
                masked_config[field] = value[:4] + '***' + value[-4:]
            else:
                masked_config[field] = '***'

    return masked_config


# Discovery and Template Endpoints

@router.get("/integrations/available")
async def get_available_integrations() -> JSONResponse:
    """Get list of available integrations."""
    integrations = [
        {
            "type": "pagerduty",
            "name": "PagerDuty",
            "description": "Receives alerts and triggers AI incident response",
            "category": "incident_management",
            "required": True,
            "setup_difficulty": "easy",
            "documentation_url": "/docs/integrations/pagerduty"
        },
        {
            "type": "kubernetes",
            "name": "Kubernetes",
            "description": "Monitors pods, deployments, and enables automated fixes",
            "category": "infrastructure",
            "required": True,
            "setup_difficulty": "medium",
            "documentation_url": "/docs/integrations/kubernetes"
        },
        {
            "type": "github",
            "name": "GitHub",
            "description": "Provides codebase context for incident analysis",
            "category": "source_control",
            "required": False,
            "setup_difficulty": "easy",
            "documentation_url": "/docs/integrations/github"
        },
        {
            "type": "notion",
            "name": "Notion",
            "description": "Accesses internal runbooks and documentation",
            "category": "documentation",
            "required": False,
            "setup_difficulty": "easy",
            "documentation_url": "/docs/integrations/notion"
        },
        {
            "type": "grafana",
            "name": "Grafana",
            "description": "Fetches metrics and dashboard data during incidents",
            "category": "monitoring",
            "required": False,
            "setup_difficulty": "medium",
            "documentation_url": "/docs/integrations/grafana"
        },
        {
            "type": "datadog",
            "name": "Datadog",
            "description": "Alternative monitoring and APM integration",
            "category": "monitoring",
            "required": False,
            "status": "coming_soon",
            "setup_difficulty": "medium",
            "documentation_url": "/docs/integrations/datadog"
        }
    ]

    return JSONResponse(content={"integrations": integrations})


@router.get("/integrations/templates")
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


@router.get("/integrations/{integration_type}/requirements")
async def get_integration_requirements(
    integration_type: str = Path(..., description="Integration type")
) -> JSONResponse:
    """Get requirements and setup instructions for an integration."""
    requirements = {
        "pagerduty": {
            "permissions": ["events.write", "services.read", "incidents.read"],
            "setup_steps": [
                "Go to PagerDuty → Services",
                "Select your service → Integrations tab",
                "Add Integration → Amazon CloudWatch",
                "Copy the integration URL"
            ],
            "required_fields": ["integration_url"],
            "optional_fields": ["webhook_secret"]
        },
        "kubernetes": {
            "permissions": ["pods.list", "pods.delete", "deployments.get", "deployments.update"],
            "setup_steps": [
                "Ensure kubectl is configured",
                "Verify access to target clusters",
                "Select contexts and namespaces",
                "Test connection"
            ],
            "required_fields": ["contexts"],
            "optional_fields": ["namespaces", "enable_destructive_operations", "kubeconfig_path"]
        },
        "github": {
            "permissions": ["repo", "read:org"],
            "setup_steps": [
                "Create a personal access token",
                "Grant necessary repository permissions",
                "Configure organization access",
                "Add token to integration"
            ],
            "required_fields": ["token"],
            "optional_fields": ["organization", "repositories"]
        },
        "notion": {
            "permissions": ["read_content", "read_comments"],
            "setup_steps": [
                "Create an integration in Notion settings",
                "Share relevant pages with the integration",
                "Copy the integration token",
                "Configure workspace access"
            ],
            "required_fields": ["token"],
            "optional_fields": ["workspace_id"]
        },
        "grafana": {
            "permissions": ["dashboards:read", "datasources:read"],
            "setup_steps": [
                "Create an API key in Grafana",
                "Grant viewer permissions",
                "Configure dashboard access",
                "Test API connection"
            ],
            "required_fields": ["url", "api_key"],
            "optional_fields": []
        }
    }

    if integration_type not in requirements:
        raise HTTPException(status_code=404, detail="Integration type not found")

    return JSONResponse(content=requirements[integration_type])
