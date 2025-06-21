"""Dashboard API endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.oncall_agent.api.schemas import (
    DashboardMetric,
    DashboardStats,
    MetricValue,
)
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# Mock data for now - replace with actual database queries
def get_mock_incidents_data() -> dict[str, Any]:
    """Get mock incident data for dashboard."""
    return {
        "total": 156,
        "active": 3,
        "resolved_today": 12,
        "avg_resolution_minutes": 45.5,
        "by_severity": {
            "critical": 2,
            "high": 5,
            "medium": 8,
            "low": 141
        }
    }


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats() -> DashboardStats:
    """Get dashboard statistics overview."""
    try:
        # Mock data - replace with actual queries
        incidents = get_mock_incidents_data()

        return DashboardStats(
            incidents_total=incidents["total"],
            incidents_active=incidents["active"],
            incidents_resolved_today=incidents["resolved_today"],
            avg_resolution_time_minutes=incidents["avg_resolution_minutes"],
            automation_success_rate=0.87,  # 87% success rate
            integrations_healthy=4,
            integrations_total=5,
            last_incident_time=datetime.now(UTC) - timedelta(hours=2)
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise


@router.get("/metrics/incidents", response_model=DashboardMetric)
async def get_incident_metrics(
    period: str = Query("24h", description="Time period: 24h, 7d, 30d")
) -> DashboardMetric:
    """Get incident trend metrics."""
    try:
        # Calculate time range
        now = datetime.now(UTC)
        if period == "24h":
            start_time = now - timedelta(days=1)
            points = 24
        elif period == "7d":
            start_time = now - timedelta(days=7)
            points = 7 * 4  # 4 points per day
        else:  # 30d
            start_time = now - timedelta(days=30)
            points = 30

        # Generate mock trend data
        trend_data = []
        for i in range(points):
            timestamp = start_time + timedelta(hours=i * 24 / points)
            value = 10 + (i % 5) * 2  # Mock variation
            trend_data.append(MetricValue(
                value=value,
                timestamp=timestamp
            ))

        return DashboardMetric(
            name="incident_count",
            current_value=3,
            change_percentage=-25.0,  # 25% decrease
            trend=trend_data,
            unit="incidents"
        )
    except Exception as e:
        logger.error(f"Error fetching incident metrics: {e}")
        raise


@router.get("/metrics/resolution-time", response_model=DashboardMetric)
async def get_resolution_time_metrics(
    period: str = Query("24h", description="Time period: 24h, 7d, 30d")
) -> DashboardMetric:
    """Get mean time to resolution metrics."""
    try:
        # Mock MTTR data
        current_mttr = 45.5
        previous_mttr = 52.3
        change_pct = ((current_mttr - previous_mttr) / previous_mttr) * 100

        # Generate trend
        now = datetime.now(UTC)
        trend_data = []
        for i in range(24):
            timestamp = now - timedelta(hours=23-i)
            value = 40 + (i % 8) * 5  # Mock variation between 40-75 minutes
            trend_data.append(MetricValue(
                value=value,
                timestamp=timestamp
            ))

        return DashboardMetric(
            name="mttr",
            current_value=current_mttr,
            change_percentage=change_pct,
            trend=trend_data,
            unit="minutes"
        )
    except Exception as e:
        logger.error(f"Error fetching MTTR metrics: {e}")
        raise


@router.get("/metrics/automation", response_model=DashboardMetric)
async def get_automation_metrics() -> DashboardMetric:
    """Get automation success rate metrics."""
    try:
        # Mock automation data
        return DashboardMetric(
            name="automation_success_rate",
            current_value=0.87,
            change_percentage=5.2,  # 5.2% improvement
            trend=[
                MetricValue(value=0.82, timestamp=datetime.now(UTC) - timedelta(days=6)),
                MetricValue(value=0.84, timestamp=datetime.now(UTC) - timedelta(days=5)),
                MetricValue(value=0.83, timestamp=datetime.now(UTC) - timedelta(days=4)),
                MetricValue(value=0.85, timestamp=datetime.now(UTC) - timedelta(days=3)),
                MetricValue(value=0.86, timestamp=datetime.now(UTC) - timedelta(days=2)),
                MetricValue(value=0.85, timestamp=datetime.now(UTC) - timedelta(days=1)),
                MetricValue(value=0.87, timestamp=datetime.now(UTC)),
            ],
            unit="percentage"
        )
    except Exception as e:
        logger.error(f"Error fetching automation metrics: {e}")
        raise


@router.get("/activity-feed")
async def get_activity_feed(
    limit: int = Query(20, ge=1, le=100)
) -> JSONResponse:
    """Get recent activity feed."""
    try:
        # Mock activity data
        activities = []
        now = datetime.now(UTC)

        activity_types = [
            {"type": "incident_created", "message": "New incident: {title}"},
            {"type": "incident_resolved", "message": "Incident resolved: {title}"},
            {"type": "action_executed", "message": "Automated action: {action} on {service}"},
            {"type": "integration_alert", "message": "Integration alert: {integration} - {message}"},
        ]

        for i in range(limit):
            activity_type = activity_types[i % len(activity_types)]
            timestamp = now - timedelta(minutes=i*5)

            activity = {
                "id": f"activity-{i}",
                "timestamp": timestamp.isoformat(),
                "type": activity_type["type"],
                "message": activity_type["message"].format(
                    title=f"Service API High Latency #{100-i}",
                    action="Restart Pod",
                    service="api-service",
                    integration="Kubernetes",
                    message="Node pressure detected"
                ),
                "severity": ["info", "warning", "error"][i % 3],
                "user": "system" if i % 2 == 0 else f"user{i % 3}@example.com"
            }
            activities.append(activity)

        return JSONResponse(content={
            "activities": activities,
            "total": len(activities)
        })
    except Exception as e:
        logger.error(f"Error fetching activity feed: {e}")
        raise


@router.get("/top-services")
async def get_top_affected_services(
    limit: int = Query(5, ge=1, le=20)
) -> JSONResponse:
    """Get top affected services by incident count."""
    try:
        # Mock service data
        services = [
            {"name": "api-gateway", "incidents": 23, "trend": "up"},
            {"name": "payment-service", "incidents": 18, "trend": "down"},
            {"name": "user-service", "incidents": 15, "trend": "stable"},
            {"name": "notification-service", "incidents": 12, "trend": "up"},
            {"name": "search-service", "incidents": 8, "trend": "down"},
        ]

        return JSONResponse(content={
            "services": services[:limit],
            "period": "last_30_days"
        })
    except Exception as e:
        logger.error(f"Error fetching top services: {e}")
        raise


@router.get("/severity-distribution")
async def get_severity_distribution() -> JSONResponse:
    """Get incident distribution by severity."""
    try:
        # Mock severity data
        incidents_data = get_mock_incidents_data()

        total = sum(incidents_data["by_severity"].values())
        distribution = []

        for severity, count in incidents_data["by_severity"].items():
            distribution.append({
                "severity": severity,
                "count": count,
                "percentage": round((count / total) * 100, 1) if total > 0 else 0
            })

        return JSONResponse(content={
            "distribution": distribution,
            "total": total
        })
    except Exception as e:
        logger.error(f"Error fetching severity distribution: {e}")
        raise
