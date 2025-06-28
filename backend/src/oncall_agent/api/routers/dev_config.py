"""Dev mode configuration endpoint for auto-fill functionality."""

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/dev", tags=["dev"])


class DevConfigResponse(BaseModel):
    """Response model for dev configuration."""
    llm_config: dict[str, Any]
    integrations: dict[str, dict[str, Any]]
    is_dev_mode: bool


def mask_sensitive_value(key: str, value: str) -> str:
    """Mask sensitive values while keeping enough for dev identification."""
    if not value:
        return ""

    # For API keys and tokens, show first 10 and last 4 characters
    if any(sensitive in key.lower() for sensitive in ['key', 'token', 'secret', 'password']):
        if len(value) > 20:
            return f"{value[:10]}...{value[-4:]}"
        elif len(value) > 10:
            return f"{value[:5]}...{value[-2:]}"

    return value


@router.get("/config", response_model=DevConfigResponse)
async def get_dev_config():
    """
    Get development configuration for auto-fill.
    
    This endpoint is only available in development mode and returns
    configuration values from environment variables for the frontend
    to use in auto-fill functionality.
    
    In dev mode, we send full unmasked values so they can be validated.
    """
    # Check if we're in dev mode
    node_env = os.getenv("NODE_ENV", "production")
    if node_env != "development":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available in development mode"
        )

    # Get LLM configuration - full values for dev mode
    llm_config = {
        "provider": "anthropic",  # Default provider
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "model": os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
        "key_name": "Development API Key"
    }

    # Get integration configurations - full values for dev mode
    integrations = {
        "pagerduty": {
            "enabled": os.getenv("PAGERDUTY_ENABLED", "false").lower() == "true",
            "api_key": os.getenv("PAGERDUTY_API_KEY", ""),
            "user_email": os.getenv("PAGERDUTY_USER_EMAIL", ""),
            "webhook_secret": os.getenv("PAGERDUTY_WEBHOOK_SECRET", ""),
        },
        "kubernetes": {
            "enabled": os.getenv("K8S_ENABLED", "false").lower() == "true",
            "config_path": os.getenv("K8S_CONFIG_PATH", ""),
            "context": os.getenv("K8S_CONTEXT", ""),
            "namespace": os.getenv("K8S_NAMESPACE", "default"),
            "enable_destructive": os.getenv("K8S_ENABLE_DESTRUCTIVE_OPERATIONS", "false").lower() == "true",
        },
        "github": {
            "enabled": bool(os.getenv("GITHUB_TOKEN")),
            "token": os.getenv("GITHUB_TOKEN", ""),
            "org": os.getenv("GITHUB_MCP_ORG", ""),
        },
        "notion": {
            "enabled": bool(os.getenv("NOTION_TOKEN")),
            "token": os.getenv("NOTION_TOKEN", ""),
            "database_id": os.getenv("NOTION_DATABASE_ID", ""),
        },
        "grafana": {
            "enabled": bool(os.getenv("GRAFANA_MCP_URL")),
            "url": os.getenv("GRAFANA_MCP_URL", ""),
            "api_key": os.getenv("GRAFANA_MCP_API_KEY", ""),
        }
    }

    return DevConfigResponse(
        llm_config=llm_config,
        integrations=integrations,
        is_dev_mode=True
    )


@router.get("/full-config")
async def get_full_dev_config():
    """
    Get full development configuration including unmasked values.
    
    WARNING: This endpoint returns sensitive values and should ONLY
    be used in local development environments.
    """
    # Check if we're in dev mode
    node_env = os.getenv("NODE_ENV", "production")
    if node_env != "development":
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available in development mode"
        )

    # Additional check for local development
    api_host = os.getenv("API_HOST", "")
    if api_host not in ["localhost", "127.0.0.1", "0.0.0.0"]:
        raise HTTPException(
            status_code=403,
            detail="Full config is only available on localhost"
        )

    # Return full configuration values
    return {
        "llm_config": {
            "provider": "anthropic",
            "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            "model": os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            "key_name": "Development API Key"
        },
        "integrations": {
            "pagerduty": {
                "api_key": os.getenv("PAGERDUTY_API_KEY", ""),
                "user_email": os.getenv("PAGERDUTY_USER_EMAIL", ""),
                "webhook_secret": os.getenv("PAGERDUTY_WEBHOOK_SECRET", ""),
            },
            "kubernetes": {
                "config_path": os.getenv("K8S_CONFIG_PATH", ""),
                "context": os.getenv("K8S_CONTEXT", ""),
                "namespace": os.getenv("K8S_NAMESPACE", "default"),
            },
            "github": {
                "token": os.getenv("GITHUB_TOKEN", ""),
                "org": os.getenv("GITHUB_MCP_ORG", ""),
            },
            "notion": {
                "token": os.getenv("NOTION_TOKEN", ""),
                "database_id": os.getenv("NOTION_DATABASE_ID", ""),
            },
            "grafana": {
                "url": os.getenv("GRAFANA_MCP_URL", ""),
                "api_key": os.getenv("GRAFANA_MCP_API_KEY", ""),
            }
        },
        "is_dev_mode": True,
        "warning": "This endpoint returns sensitive values. Use only in local development!"
    }
