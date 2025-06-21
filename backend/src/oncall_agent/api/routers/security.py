"""Security and audit trail API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.oncall_agent.api.schemas import (
    AuditAction,
    AuditLogEntry,
    AuditLogList,
    SuccessResponse,
)
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/security", tags=["security"])

# Mock audit log storage
AUDIT_LOGS: list[AuditLogEntry] = []


def create_audit_log(
    action: AuditAction,
    user: str | None,
    resource_type: str,
    resource_id: str,
    details: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None
) -> AuditLogEntry:
    """Create an audit log entry."""
    entry = AuditLogEntry(
        id=str(uuid.uuid4()),
        action=action,
        user=user,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        created_at=datetime.now(UTC),
        ip_address=ip_address,
        user_agent=user_agent
    )
    AUDIT_LOGS.append(entry)
    return entry


# Initialize with some mock audit logs
def init_mock_audit_logs():
    """Initialize mock audit log data."""
    actions = [
        (AuditAction.INCIDENT_CREATED, "system", "incident", "inc-001", {"severity": "high", "service": "api-gateway"}),
        (AuditAction.INCIDENT_UPDATED, "alice@example.com", "incident", "inc-001", {"status": "acknowledged"}),
        (AuditAction.ACTION_EXECUTED, "ai-agent", "incident", "inc-001", {"action": "restart_pod", "automated": True}),
        (AuditAction.INCIDENT_RESOLVED, "bob@example.com", "incident", "inc-001", {"resolution": "Pod restarted"}),
        (AuditAction.INTEGRATION_CONFIGURED, "admin@example.com", "integration", "kubernetes", {"enabled": True}),
        (AuditAction.SETTINGS_CHANGED, "admin@example.com", "settings", "notifications", {"slack_enabled": True}),
        (AuditAction.USER_LOGIN, "charlie@example.com", "auth", "session-123", {"method": "sso"}),
    ]

    now = datetime.now(UTC)
    for i, (action, user, resource_type, resource_id, details) in enumerate(actions):
        entry = AuditLogEntry(
            id=str(uuid.uuid4()),
            action=action,
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            created_at=now - timedelta(hours=i),
            ip_address=f"192.168.1.{100 + i}",
            user_agent="Mozilla/5.0"
        )
        AUDIT_LOGS.append(entry)


@router.get("/audit-logs", response_model=AuditLogList)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: AuditAction | None = None,
    user: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> AuditLogList:
    """Get audit log entries with filtering."""
    try:
        # Filter logs
        filtered_logs = AUDIT_LOGS.copy()

        if action:
            filtered_logs = [log for log in filtered_logs if log.action == action]
        if user:
            filtered_logs = [log for log in filtered_logs if log.user == user]
        if resource_type:
            filtered_logs = [log for log in filtered_logs if log.resource_type == resource_type]
        if start_date:
            filtered_logs = [log for log in filtered_logs if log.created_at >= start_date]
        if end_date:
            filtered_logs = [log for log in filtered_logs if log.created_at <= end_date]

        # Sort by created_at descending
        filtered_logs.sort(key=lambda x: x.created_at, reverse=True)

        # Paginate
        total = len(filtered_logs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        logs = filtered_logs[start_idx:end_idx]

        return AuditLogList(
            entries=logs,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-logs/export")
async def export_audit_logs(
    format: str = Query("csv", description="Export format: csv, json"),
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> JSONResponse:
    """Export audit logs."""
    try:
        # Filter logs for export
        logs_to_export = AUDIT_LOGS.copy()

        if start_date:
            logs_to_export = [log for log in logs_to_export if log.created_at >= start_date]
        if end_date:
            logs_to_export = [log for log in logs_to_export if log.created_at <= end_date]

        # Mock export response
        export_data = {
            "export_id": str(uuid.uuid4()),
            "format": format,
            "status": "ready",
            "download_url": f"/api/v1/security/audit-logs/download/{uuid.uuid4()}.{format}",
            "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            "record_count": len(logs_to_export)
        }

        return JSONResponse(content=export_data)

    except Exception as e:
        logger.error(f"Error exporting audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permissions")
async def get_user_permissions(
    user_email: str = Query(..., description="User email address")
) -> JSONResponse:
    """Get user permissions and roles."""
    try:
        # Mock permission data
        permissions = {
            "user": user_email,
            "roles": [],
            "permissions": []
        }

        # Assign roles based on email patterns (mock logic)
        if "admin" in user_email:
            permissions["roles"] = ["admin", "operator"]
            permissions["permissions"] = [
                "incidents.read", "incidents.write", "incidents.delete",
                "integrations.read", "integrations.write",
                "settings.read", "settings.write",
                "analytics.read", "audit.read"
            ]
        elif "oncall" in user_email or "@example.com" in user_email:
            permissions["roles"] = ["operator"]
            permissions["permissions"] = [
                "incidents.read", "incidents.write",
                "integrations.read",
                "analytics.read"
            ]
        else:
            permissions["roles"] = ["viewer"]
            permissions["permissions"] = [
                "incidents.read",
                "analytics.read"
            ]

        permissions["effective_permissions"] = list(set(permissions["permissions"]))

        return JSONResponse(content=permissions)

    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/access-logs")
async def get_access_logs(
    limit: int = Query(100, ge=1, le=1000),
    user: str | None = None
) -> JSONResponse:
    """Get API access logs."""
    try:
        # Mock access log data
        access_logs = []
        endpoints = [
            "/api/v1/incidents", "/api/v1/dashboard/stats",
            "/api/v1/integrations", "/api/v1/agent/analyze",
            "/api/v1/analytics/incidents"
        ]
        methods = ["GET", "POST", "PUT", "DELETE"]
        status_codes = [200, 200, 200, 201, 400, 401, 404, 500]

        for i in range(min(limit, 50)):
            timestamp = datetime.now(UTC) - timedelta(minutes=i*5)
            log_user = user if user else f"user{i % 5}@example.com"

            access_logs.append({
                "timestamp": timestamp.isoformat(),
                "user": log_user,
                "method": methods[i % len(methods)],
                "endpoint": endpoints[i % len(endpoints)],
                "status_code": status_codes[i % len(status_codes)],
                "response_time_ms": 50 + (i * 10),
                "ip_address": f"192.168.1.{100 + (i % 50)}",
                "user_agent": "Mozilla/5.0"
            })

        return JSONResponse(content={
            "access_logs": access_logs,
            "total": len(access_logs)
        })

    except Exception as e:
        logger.error(f"Error fetching access logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/security-events")
async def get_security_events(
    severity: str | None = Query(None, description="Filter by severity: low, medium, high, critical"),
    days: int = Query(7, ge=1, le=90)
) -> JSONResponse:
    """Get security-related events."""
    try:
        events = []
        event_types = [
            {"type": "failed_login", "severity": "medium", "description": "Multiple failed login attempts"},
            {"type": "permission_denied", "severity": "low", "description": "Access denied to restricted resource"},
            {"type": "api_rate_limit", "severity": "low", "description": "API rate limit exceeded"},
            {"type": "suspicious_activity", "severity": "high", "description": "Unusual access pattern detected"},
            {"type": "integration_auth_failure", "severity": "high", "description": "Integration authentication failed"},
            {"type": "data_export", "severity": "medium", "description": "Large data export initiated"},
        ]

        for i in range(20):
            event = event_types[i % len(event_types)].copy()
            timestamp = datetime.now(UTC) - timedelta(hours=i*8)

            if severity and event["severity"] != severity:
                continue

            events.append({
                "id": f"sec-event-{i}",
                "timestamp": timestamp.isoformat(),
                "type": event["type"],
                "severity": event["severity"],
                "description": event["description"],
                "user": f"user{i % 5}@example.com" if i % 3 != 0 else "unknown",
                "ip_address": f"192.168.1.{100 + i}",
                "resolved": i > 5  # Older events are resolved
            })

        return JSONResponse(content={
            "security_events": events,
            "total": len(events),
            "unresolved": len([e for e in events if not e["resolved"]])
        })

    except Exception as e:
        logger.error(f"Error fetching security events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rotate-api-key")
async def rotate_api_key(
    service: str = Query(..., description="Service name for API key rotation")
) -> SuccessResponse:
    """Rotate API keys for integrations."""
    try:
        # Mock API key rotation
        new_key_preview = f"{service[:3].upper()}-****-****-****-{uuid.uuid4().hex[:8]}"

        # Log the rotation
        create_audit_log(
            action=AuditAction.SETTINGS_CHANGED,
            user="system",
            resource_type="api_key",
            resource_id=service,
            details={"action": "rotate_key", "service": service}
        )

        return SuccessResponse(
            success=True,
            message=f"API key rotated successfully for {service}",
            data={
                "service": service,
                "new_key_preview": new_key_preview,
                "expires_at": (datetime.now(UTC) + timedelta(days=90)).isoformat()
            }
        )

    except Exception as e:
        logger.error(f"Error rotating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance-report")
async def get_compliance_report() -> JSONResponse:
    """Get security compliance report."""
    try:
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "compliance_status": {
                "overall": "compliant",
                "score": 0.92  # 92% compliant
            },
            "checks": [
                {
                    "name": "Access Control",
                    "status": "pass",
                    "details": "All users have appropriate role-based access"
                },
                {
                    "name": "Audit Logging",
                    "status": "pass",
                    "details": "All critical actions are logged"
                },
                {
                    "name": "Data Encryption",
                    "status": "pass",
                    "details": "All data encrypted in transit and at rest"
                },
                {
                    "name": "API Security",
                    "status": "pass",
                    "details": "API authentication and rate limiting enabled"
                },
                {
                    "name": "Secret Management",
                    "status": "warning",
                    "details": "Some API keys approaching rotation deadline"
                },
                {
                    "name": "Incident Response",
                    "status": "pass",
                    "details": "Incident response procedures documented and tested"
                }
            ],
            "recommendations": [
                "Rotate API keys for services approaching 90-day limit",
                "Review and update access permissions quarterly",
                "Conduct security training for new team members"
            ]
        }

        return JSONResponse(content=report)

    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threat-detection")
async def get_threat_detection_status() -> JSONResponse:
    """Get threat detection system status."""
    try:
        status = {
            "enabled": True,
            "last_scan": (datetime.now(UTC) - timedelta(minutes=15)).isoformat(),
            "threat_level": "low",
            "active_threats": 0,
            "blocked_ips": ["203.0.113.45", "198.51.100.12"],  # Example IPs
            "rules": {
                "total": 1250,
                "active": 1180,
                "custom": 45
            },
            "recent_alerts": [
                {
                    "timestamp": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
                    "type": "rate_limit_exceeded",
                    "source": "203.0.113.45",
                    "action": "blocked"
                },
                {
                    "timestamp": (datetime.now(UTC) - timedelta(hours=5)).isoformat(),
                    "type": "suspicious_pattern",
                    "source": "198.51.100.12",
                    "action": "monitored"
                }
            ]
        }

        return JSONResponse(content=status)

    except Exception as e:
        logger.error(f"Error getting threat detection status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Initialize mock data
init_mock_audit_logs()
