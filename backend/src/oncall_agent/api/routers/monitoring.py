"""Live monitoring and logs API endpoints."""

import asyncio
import random
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse

from src.oncall_agent.api.schemas import (
    LogEntry,
    LogLevel,
    MonitoringMetric,
    SystemStatus,
)
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Active WebSocket connections
active_connections: list[WebSocket] = []


@router.get("/logs")
async def get_logs(
    level: LogLevel | None = Query(None, description="Filter by log level"),
    source: str | None = Query(None, description="Filter by source"),
    limit: int = Query(100, ge=1, le=1000),
    since: datetime | None = Query(None, description="Logs since timestamp")
) -> JSONResponse:
    """Get system logs."""
    try:
        logs = []
        sources = ["api", "agent", "kubernetes", "github", "datadog", "webhook"]

        # Generate mock logs
        now = datetime.now(UTC)
        for i in range(min(limit, 200)):
            timestamp = now - timedelta(seconds=i*30)

            if since and timestamp < since:
                break

            log_level = random.choice(list(LogLevel))
            if level and log_level != level:
                continue

            log_source = random.choice(sources)
            if source and log_source != source:
                continue

            # Generate appropriate message based on level
            if log_level == LogLevel.ERROR:
                messages = [
                    "Failed to connect to database",
                    "API rate limit exceeded",
                    "Timeout waiting for response",
                    "Authentication failed"
                ]
            elif log_level == LogLevel.WARNING:
                messages = [
                    "High memory usage detected",
                    "Slow query performance",
                    "Retry attempt 2 of 3",
                    "Cache miss rate above threshold"
                ]
            elif log_level == LogLevel.INFO:
                messages = [
                    "Processing incident analysis",
                    "Integration health check completed",
                    "Webhook received",
                    "Action executed successfully"
                ]
            else:  # DEBUG
                messages = [
                    "Entering function process_alert",
                    "Query parameters: {limit: 100}",
                    "Response time: 145ms",
                    "Cache hit for key: incident-123"
                ]

            logs.append(LogEntry(
                timestamp=timestamp,
                level=log_level,
                source=log_source,
                message=random.choice(messages),
                context={
                    "request_id": f"req-{1000+i}",
                    "user": f"user{i % 5}@example.com" if i % 3 == 0 else "system"
                }
            ))

        return JSONResponse(content={
            "logs": [log.dict() for log in logs],
            "total": len(logs)
        })

    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise


@router.get("/logs/stream")
async def stream_logs(
    level: LogLevel | None = Query(None, description="Filter by log level"),
    source: str | None = Query(None, description="Filter by source")
) -> StreamingResponse:
    """Stream logs in real-time using Server-Sent Events."""
    async def generate_logs() -> AsyncGenerator[str, None]:
        """Generate log events."""
        sources = ["api", "agent", "kubernetes", "github", "datadog"]

        while True:
            # Generate a random log entry
            log_source = random.choice(sources)
            if source and log_source != source:
                await asyncio.sleep(0.5)
                continue

            log_level = random.choice(list(LogLevel))
            if level and log_level != level:
                await asyncio.sleep(0.5)
                continue

            log_entry = LogEntry(
                timestamp=datetime.now(UTC),
                level=log_level,
                source=log_source,
                message=f"[{log_source}] Sample log message at {datetime.now().isoformat()}",
                context={"stream": True}
            )

            yield f"data: {log_entry.json()}\n\n"
            await asyncio.sleep(random.uniform(0.5, 2.0))

    return StreamingResponse(
        generate_logs(),
        media_type="text/event-stream"
    )


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics."""
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            # Send metrics every second
            metrics = generate_real_time_metrics()
            await websocket.send_json(metrics)
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.remove(websocket)


def generate_real_time_metrics() -> dict[str, Any]:
    """Generate real-time system metrics."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": {
            "cpu_usage": round(20 + random.random() * 60, 2),
            "memory_usage": round(40 + random.random() * 40, 2),
            "request_rate": int(100 + random.random() * 200),
            "error_rate": round(random.random() * 5, 2),
            "active_connections": len(active_connections),
            "queue_size": int(random.random() * 20),
            "response_time_p99": int(50 + random.random() * 150)
        }
    }


@router.get("/metrics")
async def get_current_metrics() -> JSONResponse:
    """Get current system metrics."""
    try:
        metrics = [
            MonitoringMetric(
                name="cpu_usage_percent",
                value=round(20 + random.random() * 60, 2),
                unit="%"
            ),
            MonitoringMetric(
                name="memory_usage_percent",
                value=round(40 + random.random() * 40, 2),
                unit="%"
            ),
            MonitoringMetric(
                name="disk_usage_percent",
                value=round(60 + random.random() * 20, 2),
                unit="%"
            ),
            MonitoringMetric(
                name="network_in_mbps",
                value=round(10 + random.random() * 50, 2),
                unit="Mbps"
            ),
            MonitoringMetric(
                name="network_out_mbps",
                value=round(15 + random.random() * 40, 2),
                unit="Mbps"
            ),
            MonitoringMetric(
                name="api_requests_per_second",
                value=int(50 + random.random() * 100),
                unit="req/s"
            ),
            MonitoringMetric(
                name="active_incidents",
                value=3,
                unit="count"
            ),
            MonitoringMetric(
                name="agent_queue_size",
                value=int(random.random() * 10),
                unit="tasks"
            )
        ]

        return JSONResponse(content={
            "metrics": [m.dict() for m in metrics],
            "timestamp": datetime.now(UTC).isoformat()
        })

    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise


@router.get("/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """Get overall system status."""
    try:
        components = {
            "api": "healthy",
            "agent": "healthy",
            "database": "healthy",
            "cache": "healthy",
            "queue": "healthy",
            "kubernetes": "healthy",
            "github": "degraded" if random.random() > 0.8 else "healthy",
            "pagerduty": "healthy",
            "datadog": "healthy"
        }

        # Determine overall status
        if any(status == "down" for status in components.values()):
            overall_status = "critical"
        elif any(status == "degraded" for status in components.values()):
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        # Current metrics
        metrics = [
            MonitoringMetric(name="uptime_hours", value=720, unit="hours"),
            MonitoringMetric(name="error_rate", value=0.02, unit="%"),
            MonitoringMetric(name="avg_response_time", value=145, unit="ms")
        ]

        # Active alerts
        alerts = []
        if random.random() > 0.7:
            alerts.append({
                "id": "alert-001",
                "severity": "warning",
                "message": "High memory usage on api-server-2",
                "timestamp": datetime.now(UTC).isoformat()
            })

        return SystemStatus(
            status=overall_status,
            components=components,
            metrics=metrics,
            alerts=alerts
        )

    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise


@router.get("/traces")
async def get_distributed_traces(
    service: str | None = Query(None, description="Filter by service"),
    duration_min: int | None = Query(None, description="Minimum duration in ms"),
    limit: int = Query(20, ge=1, le=100)
) -> JSONResponse:
    """Get distributed traces."""
    try:
        traces = []
        services = ["api-gateway", "user-service", "payment-service", "notification-service"]

        for i in range(min(limit, 50)):
            trace_service = random.choice(services)
            if service and trace_service != service:
                continue

            duration = int(50 + random.random() * 500)
            if duration_min and duration < duration_min:
                continue

            trace = {
                "trace_id": f"trace-{uuid.uuid4().hex[:16]}",
                "service": trace_service,
                "operation": random.choice(["GET /api/users", "POST /api/orders", "GET /api/products"]),
                "duration_ms": duration,
                "timestamp": (datetime.now(UTC) - timedelta(minutes=i*5)).isoformat(),
                "status": "success" if random.random() > 0.1 else "error",
                "spans": [
                    {
                        "service": trace_service,
                        "operation": "http_request",
                        "duration_ms": int(duration * 0.3)
                    },
                    {
                        "service": "database",
                        "operation": "query",
                        "duration_ms": int(duration * 0.5)
                    },
                    {
                        "service": "cache",
                        "operation": "get",
                        "duration_ms": int(duration * 0.2)
                    }
                ]
            }
            traces.append(trace)

        return JSONResponse(content={
            "traces": traces,
            "total": len(traces)
        })

    except Exception as e:
        logger.error(f"Error fetching traces: {e}")
        raise


@router.get("/alerts/active")
async def get_active_alerts() -> JSONResponse:
    """Get currently active monitoring alerts."""
    try:
        alerts = []

        # Generate some mock active alerts
        alert_templates = [
            {
                "name": "High CPU Usage",
                "condition": "cpu_usage > 80%",
                "severity": "warning",
                "service": "api-gateway"
            },
            {
                "name": "Memory Pressure",
                "condition": "memory_usage > 85%",
                "severity": "critical",
                "service": "user-service"
            },
            {
                "name": "Disk Space Low",
                "condition": "disk_free < 10GB",
                "severity": "warning",
                "service": "database"
            },
            {
                "name": "High Error Rate",
                "condition": "error_rate > 5%",
                "severity": "critical",
                "service": "payment-service"
            },
            {
                "name": "Slow Response Time",
                "condition": "p99_latency > 1000ms",
                "severity": "warning",
                "service": "search-service"
            }
        ]

        # Randomly select some alerts to be active
        for i, template in enumerate(alert_templates):
            if random.random() > 0.6:  # 40% chance of being active
                alerts.append({
                    "id": f"alert-{i}",
                    "name": template["name"],
                    "condition": template["condition"],
                    "severity": template["severity"],
                    "service": template["service"],
                    "triggered_at": (datetime.now(UTC) - timedelta(minutes=random.randint(5, 120))).isoformat(),
                    "value": f"{random.randint(81, 95)}%" if "%" in template["condition"] else f"{random.randint(500, 2000)}ms",
                    "status": "firing"
                })

        return JSONResponse(content={
            "alerts": alerts,
            "total": len(alerts),
            "by_severity": {
                "critical": len([a for a in alerts if a["severity"] == "critical"]),
                "warning": len([a for a in alerts if a["severity"] == "warning"]),
                "info": 0
            }
        })

    except Exception as e:
        logger.error(f"Error fetching active alerts: {e}")
        raise


@router.get("/profiling")
async def get_profiling_data(
    service: str = Query(..., description="Service to profile"),
    type: str = Query("cpu", description="Profile type: cpu, memory, goroutines")
) -> JSONResponse:
    """Get service profiling data."""
    try:
        profiling_data = {
            "service": service,
            "type": type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {}
        }

        if type == "cpu":
            profiling_data["data"] = {
                "top_functions": [
                    {"name": "handleRequest", "cpu_percent": 25.3},
                    {"name": "queryDatabase", "cpu_percent": 18.7},
                    {"name": "serializeResponse", "cpu_percent": 12.4},
                    {"name": "validateInput", "cpu_percent": 8.2},
                    {"name": "logRequest", "cpu_percent": 5.1}
                ],
                "total_cpu_seconds": 3600
            }
        elif type == "memory":
            profiling_data["data"] = {
                "heap_alloc_mb": 512,
                "heap_inuse_mb": 420,
                "stack_inuse_mb": 8,
                "gc_runs": 1523,
                "top_allocators": [
                    {"function": "parseJSON", "alloc_mb": 120},
                    {"function": "buildResponse", "alloc_mb": 85},
                    {"function": "cacheSet", "alloc_mb": 60}
                ]
            }

        return JSONResponse(content=profiling_data)

    except Exception as e:
        logger.error(f"Error fetching profiling data: {e}")
        raise
