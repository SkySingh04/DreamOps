"""Analytics and reporting API endpoints."""

import random
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.oncall_agent.api.schemas import (
    AnalyticsQuery,
    IncidentAnalytics,
    ServiceHealth,
    Severity,
    TimeRange,
)
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


def generate_trend_data(days: int, base_value: int = 10) -> list[dict[str, Any]]:
    """Generate mock trend data."""
    trend = []
    now = datetime.now(UTC)

    for i in range(days, -1, -1):
        date = now - timedelta(days=i)
        # Add some variation
        value = base_value + random.randint(-5, 10) + (days - i) // 3
        trend.append({
            "date": date.date().isoformat(),
            "value": max(0, value)
        })

    return trend


@router.post("/incidents", response_model=IncidentAnalytics)
async def get_incident_analytics(
    query: AnalyticsQuery
) -> IncidentAnalytics:
    """Get incident analytics for the specified time range."""
    try:
        # Calculate days in range
        days = (query.time_range.end - query.time_range.start).days

        # Mock data generation
        total = days * 15  # Average 15 incidents per day

        by_severity = {
            Severity.CRITICAL: int(total * 0.05),
            Severity.HIGH: int(total * 0.15),
            Severity.MEDIUM: int(total * 0.30),
            Severity.LOW: int(total * 0.35),
            Severity.INFO: int(total * 0.15)
        }

        by_service = {
            "api-gateway": int(total * 0.25),
            "user-service": int(total * 0.20),
            "payment-service": int(total * 0.15),
            "notification-service": int(total * 0.10),
            "search-service": int(total * 0.10),
            "other": int(total * 0.20)
        }

        by_status = {
            "resolved": int(total * 0.85),
            "active": int(total * 0.05),
            "acknowledged": int(total * 0.05),
            "triggered": int(total * 0.05)
        }

        mttr_by_severity = {
            Severity.CRITICAL: 15.5,
            Severity.HIGH: 28.3,
            Severity.MEDIUM: 45.7,
            Severity.LOW: 120.5,
            Severity.INFO: 180.0
        }

        return IncidentAnalytics(
            total_incidents=total,
            by_severity=by_severity,
            by_service=by_service,
            by_status=by_status,
            mttr_by_severity=mttr_by_severity,
            automation_rate=0.72,  # 72% automated
            trend_data=generate_trend_data(min(days, 30))
        )

    except Exception as e:
        logger.error(f"Error generating incident analytics: {e}")
        raise


@router.get("/services/health")
async def get_services_health(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze")
) -> JSONResponse:
    """Get health metrics for all services."""
    try:
        services = [
            "api-gateway", "user-service", "payment-service",
            "notification-service", "search-service", "auth-service",
            "inventory-service", "recommendation-service"
        ]

        health_data = []
        for service in services:
            # Generate mock health data
            incident_count = random.randint(0, 20)
            availability = 99.9 - (incident_count * 0.1)
            mttr = 20 + random.randint(0, 60)
            health_score = min(100, 100 - (incident_count * 2) - (mttr / 10))

            health_data.append(ServiceHealth(
                service_name=service,
                incident_count=incident_count,
                availability_percentage=availability,
                mttr_minutes=mttr,
                last_incident=datetime.now(UTC) - timedelta(hours=random.randint(1, 168)),
                health_score=health_score
            ))

        # Sort by health score
        health_data.sort(key=lambda x: x.health_score, reverse=True)

        return JSONResponse(content={
            "services": [h.dict() for h in health_data],
            "period_days": days,
            "overall_health": sum(h.health_score for h in health_data) / len(health_data)
        })

    except Exception as e:
        logger.error(f"Error getting service health: {e}")
        raise


@router.get("/patterns")
async def get_incident_patterns(
    days: int = Query(30, ge=1, le=90),
    min_occurrences: int = Query(3, ge=1)
) -> JSONResponse:
    """Identify incident patterns and recurring issues."""
    try:
        patterns = [
            {
                "pattern_id": "pat-001",
                "name": "Database Connection Spike",
                "description": "Sudden increase in database connections leading to pool exhaustion",
                "occurrences": 8,
                "services_affected": ["user-service", "payment-service"],
                "typical_time": "09:00-10:00 UTC",
                "avg_duration_minutes": 35,
                "recommended_action": "Implement connection pooling and circuit breakers"
            },
            {
                "pattern_id": "pat-002",
                "name": "Memory Leak Pattern",
                "description": "Gradual memory increase in Java services after deployment",
                "occurrences": 5,
                "services_affected": ["api-gateway", "search-service"],
                "typical_time": "After deployment",
                "avg_duration_minutes": 120,
                "recommended_action": "Review heap dumps and implement memory profiling"
            },
            {
                "pattern_id": "pat-003",
                "name": "Traffic Surge Timeouts",
                "description": "Service timeouts during traffic spikes",
                "occurrences": 12,
                "services_affected": ["api-gateway"],
                "typical_time": "18:00-20:00 UTC",
                "avg_duration_minutes": 15,
                "recommended_action": "Implement auto-scaling and request rate limiting"
            }
        ]

        # Filter by minimum occurrences
        filtered_patterns = [p for p in patterns if p["occurrences"] >= min_occurrences]

        return JSONResponse(content={
            "patterns": filtered_patterns,
            "total_patterns": len(filtered_patterns),
            "analysis_period_days": days
        })

    except Exception as e:
        logger.error(f"Error identifying patterns: {e}")
        raise


@router.get("/slo-compliance")
async def get_slo_compliance(
    service: str | None = Query(None, description="Filter by service")
) -> JSONResponse:
    """Get SLO compliance metrics."""
    try:
        slos = []
        services = ["api-gateway", "user-service", "payment-service"] if not service else [service]

        for svc in services:
            # Generate mock SLO data
            availability_target = 99.9
            availability_actual = 99.85 + random.random() * 0.14

            latency_target = 200  # ms
            latency_actual = 150 + random.randint(0, 100)

            error_rate_target = 0.1  # percentage
            error_rate_actual = random.random() * 0.15

            slos.append({
                "service": svc,
                "slos": [
                    {
                        "name": "Availability",
                        "target": availability_target,
                        "actual": round(availability_actual, 2),
                        "unit": "%",
                        "compliant": availability_actual >= availability_target
                    },
                    {
                        "name": "Latency P99",
                        "target": latency_target,
                        "actual": latency_actual,
                        "unit": "ms",
                        "compliant": latency_actual <= latency_target
                    },
                    {
                        "name": "Error Rate",
                        "target": error_rate_target,
                        "actual": round(error_rate_actual, 3),
                        "unit": "%",
                        "compliant": error_rate_actual <= error_rate_target
                    }
                ],
                "overall_compliance": sum(1 for slo in [True, latency_actual <= latency_target, error_rate_actual <= error_rate_target] if slo) / 3
            })

        return JSONResponse(content={
            "slo_compliance": slos,
            "reporting_period": "last_30_days"
        })

    except Exception as e:
        logger.error(f"Error calculating SLO compliance: {e}")
        raise


@router.get("/cost-impact")
async def get_incident_cost_impact(
    days: int = Query(30, ge=1, le=90)
) -> JSONResponse:
    """Estimate cost impact of incidents."""
    try:
        # Mock cost calculation
        incident_costs = []
        total_cost = 0

        cost_factors = [
            {"type": "downtime", "unit_cost": 1000, "unit": "per hour"},
            {"type": "engineering_hours", "unit_cost": 150, "unit": "per hour"},
            {"type": "customer_credits", "unit_cost": 500, "unit": "per incident"},
            {"type": "infrastructure_scaling", "unit_cost": 200, "unit": "per incident"}
        ]

        for factor in cost_factors:
            if factor["type"] == "downtime":
                hours = random.randint(5, 20)
                cost = hours * factor["unit_cost"]
            elif factor["type"] == "engineering_hours":
                hours = random.randint(40, 200)
                cost = hours * factor["unit_cost"]
            elif factor["type"] == "customer_credits":
                incidents = random.randint(2, 10)
                cost = incidents * factor["unit_cost"]
            else:
                incidents = random.randint(5, 15)
                cost = incidents * factor["unit_cost"]

            total_cost += cost
            incident_costs.append({
                "category": factor["type"],
                "amount": cost,
                "details": f"{hours if 'hour' in factor['unit'] else incidents} {factor['unit']}"
            })

        return JSONResponse(content={
            "total_cost": total_cost,
            "cost_breakdown": incident_costs,
            "period_days": days,
            "currency": "USD",
            "savings_from_automation": int(total_cost * 0.3)  # 30% saved through automation
        })

    except Exception as e:
        logger.error(f"Error calculating cost impact: {e}")
        raise


@router.get("/team-performance")
async def get_team_performance(
    days: int = Query(30, ge=1, le=90)
) -> JSONResponse:
    """Get on-call team performance metrics."""
    try:
        team_members = ["alice@example.com", "bob@example.com", "charlie@example.com", "diana@example.com"]

        performance_data = []
        for member in team_members:
            incidents_handled = random.randint(10, 50)
            avg_response_time = random.randint(2, 15)
            avg_resolution_time = random.randint(20, 120)

            performance_data.append({
                "member": member,
                "incidents_handled": incidents_handled,
                "avg_response_time_minutes": avg_response_time,
                "avg_resolution_time_minutes": avg_resolution_time,
                "escalation_rate": round(random.random() * 0.2, 2),  # 0-20%
                "customer_satisfaction": round(4 + random.random(), 1)  # 4.0-5.0
            })

        # Team aggregate metrics
        team_metrics = {
            "total_incidents": sum(p["incidents_handled"] for p in performance_data),
            "avg_response_time": sum(p["avg_response_time_minutes"] for p in performance_data) / len(performance_data),
            "avg_resolution_time": sum(p["avg_resolution_time_minutes"] for p in performance_data) / len(performance_data),
            "on_call_coverage": 0.98,  # 98% coverage
            "handoff_efficiency": 0.95  # 95% smooth handoffs
        }

        return JSONResponse(content={
            "individual_performance": performance_data,
            "team_metrics": team_metrics,
            "period_days": days
        })

    except Exception as e:
        logger.error(f"Error getting team performance: {e}")
        raise


@router.get("/predictions")
async def get_incident_predictions() -> JSONResponse:
    """Get AI-based incident predictions."""
    try:
        predictions = [
            {
                "prediction_id": "pred-001",
                "type": "traffic_spike",
                "description": "Expected 3x traffic increase during upcoming sale event",
                "probability": 0.85,
                "impact": "high",
                "recommended_actions": [
                    "Pre-scale API gateway to 10 instances",
                    "Increase cache TTL",
                    "Enable rate limiting"
                ],
                "predicted_time": (datetime.now(UTC) + timedelta(days=3)).isoformat()
            },
            {
                "prediction_id": "pred-002",
                "type": "resource_exhaustion",
                "description": "Database storage expected to reach 90% in 5 days",
                "probability": 0.92,
                "impact": "medium",
                "recommended_actions": [
                    "Archive old data",
                    "Increase storage allocation",
                    "Implement data retention policy"
                ],
                "predicted_time": (datetime.now(UTC) + timedelta(days=5)).isoformat()
            },
            {
                "prediction_id": "pred-003",
                "type": "certificate_expiry",
                "description": "SSL certificate for api.example.com expires in 14 days",
                "probability": 1.0,
                "impact": "critical",
                "recommended_actions": [
                    "Renew SSL certificate",
                    "Update certificate in load balancer",
                    "Test certificate rotation"
                ],
                "predicted_time": (datetime.now(UTC) + timedelta(days=14)).isoformat()
            }
        ]

        return JSONResponse(content={
            "predictions": predictions,
            "generated_at": datetime.now(UTC).isoformat(),
            "model_confidence": 0.88
        })

    except Exception as e:
        logger.error(f"Error generating predictions: {e}")
        raise


@router.post("/reports/generate")
async def generate_report(
    report_type: str = Query(..., description="Report type: executive, technical, compliance"),
    time_range: TimeRange = ...
) -> JSONResponse:
    """Generate a detailed report."""
    try:
        report_id = f"report-{datetime.now().timestamp()}"

        # Mock report generation
        report_data = {
            "report_id": report_id,
            "type": report_type,
            "status": "generating",
            "estimated_completion_seconds": 30,
            "format_options": ["pdf", "csv", "json"],
            "sections": []
        }

        if report_type == "executive":
            report_data["sections"] = [
                "Executive Summary",
                "Key Metrics",
                "Incident Trends",
                "Cost Analysis",
                "Recommendations"
            ]
        elif report_type == "technical":
            report_data["sections"] = [
                "Incident Details",
                "Root Cause Analysis",
                "System Performance",
                "Integration Status",
                "Action Items"
            ]
        elif report_type == "compliance":
            report_data["sections"] = [
                "SLO Compliance",
                "Audit Trail",
                "Security Incidents",
                "Policy Adherence",
                "Remediation Status"
            ]

        return JSONResponse(content=report_data)

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise
