"""Settings management API endpoints."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

from src.oncall_agent.api.schemas import (
    ActionType,
    AISettings,
    AlertSettings,
    APIKeySettings,
    AutomationSettings,
    GlobalSettings,
    IntegrationConfig,
    IntegrationTestResult,
    NotificationSettings,
    SecuritySettings,
    Severity,
    SuccessResponse,
)
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

# Mock settings storage
GLOBAL_SETTINGS = GlobalSettings(
    organization_name="Acme Corp",
    timezone="UTC",
    retention_days=90,
    ai=AISettings(
        model="claude-3-5-sonnet",
        additional_context="You are an expert oncall engineer specializing in Kubernetes and AWS infrastructure.",
        auto_analyze=True,
        confidence_threshold=0.8,
        max_tokens=4000,
        temperature=0.3
    ),
    alerts=AlertSettings(
        priority_threshold=Severity.HIGH,
        auto_acknowledge=False,
        deduplication_enabled=True,
        deduplication_window_minutes=15,
        escalation_delay_minutes=30
    ),
    security=SecuritySettings(
        audit_logs_enabled=True,
        data_retention_days=90,
        require_2fa=False,
        session_timeout_minutes=480,
        ip_whitelist=[]
    ),
    api_keys=APIKeySettings(
        anthropic_api_key="sk-ant-api03-***",
        webhook_url="https://oncall-agent.com/api/alerts",
        webhook_secret="wh_secret_***"
    ),
    notifications=NotificationSettings(
        email_enabled=True,
        slack_enabled=True,
        slack_channel="#incidents",
        severity_threshold=Severity.MEDIUM,
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00"
    ),
    automation=AutomationSettings(
        auto_acknowledge=True,
        auto_resolve=False,
        require_approval_for_actions=True,
        max_automated_actions=5,
        allowed_action_types=[
            ActionType.RESTART_POD,
            ActionType.RUN_DIAGNOSTICS,
            ActionType.CREATE_TICKET
        ]
    ),
    integrations={
        "kubernetes": IntegrationConfig(
            enabled=True,
            config={"namespace": "default", "cluster": "production", "kubeconfig_path": "/etc/kubernetes/config"}
        ),
        "github": IntegrationConfig(
            enabled=True,
            config={"org": "acme-corp", "token": "***", "repos": ["backend", "frontend"]}
        ),
        "pagerduty": IntegrationConfig(
            enabled=True,
            config={"api_key": "***", "service_ids": ["P123456"], "routing_key": "***"}
        ),
        "slack": IntegrationConfig(
            enabled=False,
            config={"webhook_url": "", "channel": "#incidents", "bot_token": "***"}
        ),
        "notion": IntegrationConfig(
            enabled=False,
            config={"token": "***", "database_id": "***"}
        ),
        "grafana": IntegrationConfig(
            enabled=False,
            config={"url": "", "api_key": "***", "org_id": "1"}
        )
    }
)


@router.get("/", response_model=GlobalSettings)
async def get_settings() -> GlobalSettings:
    """Get all system settings."""
    try:
        return GLOBAL_SETTINGS
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/", response_model=SuccessResponse)
async def update_settings(
    settings: GlobalSettings = Body(..., description="Updated settings")
) -> SuccessResponse:
    """Update system settings."""
    try:
        global GLOBAL_SETTINGS
        GLOBAL_SETTINGS = settings

        logger.info("Global settings updated")

        # Log audit trail
        from src.oncall_agent.api.routers.security import AuditAction, create_audit_log
        create_audit_log(
            action=AuditAction.SETTINGS_CHANGED,
            user="admin@example.com",  # In real app, get from auth
            resource_type="settings",
            resource_id="global",
            details={"settings": settings.dict()}
        )

        return SuccessResponse(
            success=True,
            message="Settings updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications", response_model=NotificationSettings)
async def get_notification_settings() -> NotificationSettings:
    """Get notification settings."""
    try:
        return GLOBAL_SETTINGS.notifications
    except Exception as e:
        logger.error(f"Error fetching notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notifications", response_model=SuccessResponse)
async def update_notification_settings(
    settings: NotificationSettings = Body(..., description="Notification settings")
) -> SuccessResponse:
    """Update notification settings."""
    try:
        GLOBAL_SETTINGS.notifications = settings

        logger.info("Notification settings updated")

        return SuccessResponse(
            success=True,
            message="Notification settings updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/automation", response_model=AutomationSettings)
async def get_automation_settings() -> AutomationSettings:
    """Get automation settings."""
    try:
        return GLOBAL_SETTINGS.automation
    except Exception as e:
        logger.error(f"Error fetching automation settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/automation", response_model=SuccessResponse)
async def update_automation_settings(
    settings: AutomationSettings = Body(..., description="Automation settings")
) -> SuccessResponse:
    """Update automation settings."""
    try:
        GLOBAL_SETTINGS.automation = settings

        logger.info("Automation settings updated")

        return SuccessResponse(
            success=True,
            message="Automation settings updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating automation settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/escalation-policies")
async def get_escalation_policies() -> JSONResponse:
    """Get escalation policies."""
    try:
        policies = [
            {
                "id": "policy-001",
                "name": "Critical Incident Escalation",
                "description": "Escalation for critical production incidents",
                "levels": [
                    {
                        "level": 1,
                        "delay_minutes": 0,
                        "targets": ["oncall-primary@example.com"],
                        "notification_methods": ["email", "slack", "phone"]
                    },
                    {
                        "level": 2,
                        "delay_minutes": 15,
                        "targets": ["oncall-secondary@example.com", "team-lead@example.com"],
                        "notification_methods": ["email", "slack", "phone"]
                    },
                    {
                        "level": 3,
                        "delay_minutes": 30,
                        "targets": ["engineering-manager@example.com"],
                        "notification_methods": ["phone"]
                    }
                ],
                "active": True
            },
            {
                "id": "policy-002",
                "name": "Standard Incident Escalation",
                "description": "Default escalation for non-critical incidents",
                "levels": [
                    {
                        "level": 1,
                        "delay_minutes": 0,
                        "targets": ["oncall-primary@example.com"],
                        "notification_methods": ["email", "slack"]
                    },
                    {
                        "level": 2,
                        "delay_minutes": 30,
                        "targets": ["oncall-secondary@example.com"],
                        "notification_methods": ["email", "slack"]
                    }
                ],
                "active": True
            }
        ]

        return JSONResponse(content={
            "policies": policies,
            "total": len(policies)
        })
    except Exception as e:
        logger.error(f"Error fetching escalation policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/oncall-schedules")
async def get_oncall_schedules() -> JSONResponse:
    """Get on-call schedules."""
    try:
        schedules = [
            {
                "id": "schedule-001",
                "name": "Primary On-Call",
                "timezone": "UTC",
                "rotation_type": "weekly",
                "current_oncall": "alice@example.com",
                "next_rotation": (datetime.now(UTC).replace(hour=0, minute=0, second=0) + timedelta(days=7)).isoformat(),
                "members": [
                    {"email": "alice@example.com", "name": "Alice Smith"},
                    {"email": "bob@example.com", "name": "Bob Johnson"},
                    {"email": "charlie@example.com", "name": "Charlie Brown"},
                    {"email": "diana@example.com", "name": "Diana Prince"}
                ]
            },
            {
                "id": "schedule-002",
                "name": "Secondary On-Call",
                "timezone": "UTC",
                "rotation_type": "weekly",
                "current_oncall": "eve@example.com",
                "next_rotation": (datetime.now(UTC).replace(hour=0, minute=0, second=0) + timedelta(days=7)).isoformat(),
                "members": [
                    {"email": "eve@example.com", "name": "Eve Wilson"},
                    {"email": "frank@example.com", "name": "Frank Miller"},
                    {"email": "grace@example.com", "name": "Grace Lee"},
                    {"email": "henry@example.com", "name": "Henry Davis"}
                ]
            }
        ]

        return JSONResponse(content={
            "schedules": schedules,
            "total": len(schedules)
        })
    except Exception as e:
        logger.error(f"Error fetching on-call schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_templates() -> JSONResponse:
    """Get incident response templates."""
    try:
        templates = [
            {
                "id": "template-001",
                "name": "Database Outage",
                "category": "infrastructure",
                "description": "Template for database-related incidents",
                "steps": [
                    "Check database connection and status",
                    "Review recent changes and deployments",
                    "Check disk space and resource usage",
                    "Review slow query logs",
                    "Implement immediate mitigation",
                    "Document root cause"
                ],
                "required_integrations": ["datadog", "pagerduty"],
                "estimated_duration_minutes": 45
            },
            {
                "id": "template-002",
                "name": "API Performance Degradation",
                "category": "application",
                "description": "Template for API performance issues",
                "steps": [
                    "Check API response times and error rates",
                    "Review traffic patterns",
                    "Check upstream dependencies",
                    "Scale if necessary",
                    "Enable caching if applicable",
                    "Monitor recovery"
                ],
                "required_integrations": ["kubernetes", "datadog"],
                "estimated_duration_minutes": 30
            },
            {
                "id": "template-003",
                "name": "Security Incident",
                "category": "security",
                "description": "Template for security-related incidents",
                "steps": [
                    "Isolate affected systems",
                    "Preserve evidence and logs",
                    "Assess scope of breach",
                    "Implement containment measures",
                    "Notify security team",
                    "Begin forensic analysis"
                ],
                "required_integrations": ["github", "pagerduty"],
                "estimated_duration_minutes": 120
            }
        ]

        return JSONResponse(content={
            "templates": templates,
            "total": len(templates)
        })
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base")
async def get_knowledge_base_settings() -> JSONResponse:
    """Get knowledge base configuration."""
    try:
        kb_settings = {
            "enabled": True,
            "sources": [
                {
                    "type": "internal_wiki",
                    "url": "https://wiki.example.com",
                    "enabled": True,
                    "last_sync": (datetime.now(UTC) - timedelta(hours=2)).isoformat()
                },
                {
                    "type": "runbooks",
                    "url": "https://runbooks.example.com",
                    "enabled": True,
                    "last_sync": (datetime.now(UTC) - timedelta(hours=1)).isoformat()
                },
                {
                    "type": "github_issues",
                    "url": "https://github.com/acme-corp/issues",
                    "enabled": True,
                    "last_sync": (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
                }
            ],
            "indexing": {
                "total_documents": 1523,
                "last_full_index": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "index_frequency": "daily",
                "vector_store": "enabled"
            },
            "ai_features": {
                "auto_suggestions": True,
                "similarity_threshold": 0.75,
                "max_suggestions": 5
            }
        }

        return JSONResponse(content=kb_settings)
    except Exception as e:
        logger.error(f"Error fetching knowledge base settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup")
async def create_settings_backup() -> SuccessResponse:
    """Create a backup of all settings."""
    try:
        backup_id = f"backup-{datetime.now().timestamp()}"

        # In real implementation, save to persistent storage
        backup_data = {
            "id": backup_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "settings": GLOBAL_SETTINGS.dict(),
            "version": "1.0.0"
        }

        logger.info(f"Created settings backup: {backup_id}")

        return SuccessResponse(
            success=True,
            message="Settings backup created successfully",
            data={
                "backup_id": backup_id,
                "size_bytes": 4096  # Mock size
            }
        )
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore/{backup_id}")
async def restore_settings_backup(backup_id: str) -> SuccessResponse:
    """Restore settings from a backup."""
    try:
        # In real implementation, load from persistent storage
        logger.info(f"Restored settings from backup: {backup_id}")

        return SuccessResponse(
            success=True,
            message=f"Settings restored from backup {backup_id}"
        )
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Individual settings sections
@router.get("/ai", response_model=AISettings)
async def get_ai_settings() -> AISettings:
    """Get AI configuration settings."""
    try:
        return GLOBAL_SETTINGS.ai
    except Exception as e:
        logger.error(f"Error fetching AI settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/ai", response_model=SuccessResponse)
async def update_ai_settings(
    settings: AISettings = Body(..., description="AI settings")
) -> SuccessResponse:
    """Update AI configuration settings."""
    try:
        GLOBAL_SETTINGS.ai = settings
        logger.info("AI settings updated")

        return SuccessResponse(
            success=True,
            message="AI settings updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating AI settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=AlertSettings)
async def get_alert_settings() -> AlertSettings:
    """Get alert processing settings."""
    try:
        return GLOBAL_SETTINGS.alerts
    except Exception as e:
        logger.error(f"Error fetching alert settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts", response_model=SuccessResponse)
async def update_alert_settings(
    settings: AlertSettings = Body(..., description="Alert settings")
) -> SuccessResponse:
    """Update alert processing settings."""
    try:
        GLOBAL_SETTINGS.alerts = settings
        logger.info("Alert settings updated")

        return SuccessResponse(
            success=True,
            message="Alert settings updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating alert settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security", response_model=SecuritySettings)
async def get_security_settings() -> SecuritySettings:
    """Get security and compliance settings."""
    try:
        return GLOBAL_SETTINGS.security
    except Exception as e:
        logger.error(f"Error fetching security settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/security", response_model=SuccessResponse)
async def update_security_settings(
    settings: SecuritySettings = Body(..., description="Security settings")
) -> SuccessResponse:
    """Update security and compliance settings."""
    try:
        GLOBAL_SETTINGS.security = settings
        logger.info("Security settings updated")

        return SuccessResponse(
            success=True,
            message="Security settings updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating security settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-keys", response_model=APIKeySettings)
async def get_api_key_settings() -> APIKeySettings:
    """Get API keys and authentication settings."""
    try:
        # Mask sensitive values for security
        masked_settings = GLOBAL_SETTINGS.api_keys.copy()
        if masked_settings.anthropic_api_key:
            masked_settings.anthropic_api_key = masked_settings.anthropic_api_key[:12] + "***"
        if masked_settings.webhook_secret:
            masked_settings.webhook_secret = "***"
        return masked_settings
    except Exception as e:
        logger.error(f"Error fetching API key settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api-keys", response_model=SuccessResponse)
async def update_api_key_settings(
    settings: APIKeySettings = Body(..., description="API key settings")
) -> SuccessResponse:
    """Update API keys and authentication settings."""
    try:
        # Only update non-masked values
        if settings.anthropic_api_key and not settings.anthropic_api_key.endswith("***"):
            GLOBAL_SETTINGS.api_keys.anthropic_api_key = settings.anthropic_api_key
        if settings.webhook_secret and settings.webhook_secret != "***":
            GLOBAL_SETTINGS.api_keys.webhook_secret = settings.webhook_secret
        if settings.webhook_url:
            GLOBAL_SETTINGS.api_keys.webhook_url = settings.webhook_url

        logger.info("API key settings updated")

        return SuccessResponse(
            success=True,
            message="API key settings updated successfully"
        )
    except Exception as e:
        logger.error(f"Error updating API key settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Integration test connections
@router.post("/integrations/{integration_name}/test", response_model=IntegrationTestResult)
async def test_integration_connection(integration_name: str) -> IntegrationTestResult:
    """Test connection to a specific integration."""
    try:
        # Get agent instance for real integration testing
        from src.oncall_agent.api.routers.integrations import get_agent_instance
        agent = await get_agent_instance()

        if not agent:
            return IntegrationTestResult(
                success=False,
                message="Agent instance not available",
                details={"error": "Agent not initialized"}
            )

        if integration_name not in agent.mcp_integrations:
            return IntegrationTestResult(
                success=False,
                message=f"Integration '{integration_name}' not found",
                details={"available": list(agent.mcp_integrations.keys())}
            )

        # Test the actual integration
        integration = agent.mcp_integrations[integration_name]
        start_time = datetime.now()

        is_healthy = await integration.health_check()
        latency = (datetime.now() - start_time).total_seconds() * 1000

        if is_healthy:
            capabilities = integration.get_capabilities()
            return IntegrationTestResult(
                success=True,
                message=f"Successfully connected to {integration_name}",
                details={
                    "capabilities": capabilities,
                    "status": "connected"
                },
                latency_ms=latency
            )
        else:
            return IntegrationTestResult(
                success=False,
                message=f"Failed to connect to {integration_name}",
                details={"status": "disconnected"},
                latency_ms=latency
            )

    except Exception as e:
        logger.error(f"Error testing {integration_name} integration: {e}")
        return IntegrationTestResult(
            success=False,
            message=f"Test failed: {str(e)}",
            details={"error": str(e)}
        )
