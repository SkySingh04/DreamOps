"""Prometheus metrics for DreamOps backend."""

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
from functools import wraps
import time

# Application info
app_info = Info('dreamops_app', 'DreamOps application information')
app_info.info({
    'version': '1.0.0',
    'name': 'dreamops-backend',
    'environment': 'production'
})

# Incident metrics
incidents_total = Counter(
    'dreamops_incidents_total',
    'Total number of incidents processed',
    ['severity', 'status', 'alert_source']
)

incidents_active = Gauge(
    'dreamops_incidents_active',
    'Number of currently active incidents',
    ['severity']
)

incident_resolution_time = Histogram(
    'dreamops_incident_resolution_seconds',
    'Time taken to resolve incidents',
    ['severity'],
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400]
)

# AI Agent metrics
agent_analysis_total = Counter(
    'dreamops_agent_analysis_total',
    'Total number of AI analyses performed',
    ['mode', 'status']
)

agent_analysis_duration = Histogram(
    'dreamops_agent_analysis_seconds',
    'Time taken for AI analysis',
    ['mode'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

agent_actions_total = Counter(
    'dreamops_agent_actions_total',
    'Total number of actions executed by AI agent',
    ['action_type', 'status', 'automated']
)

agent_confidence_score = Gauge(
    'dreamops_agent_confidence_score',
    'Current AI agent confidence score for actions',
    ['incident_id']
)

agent_mode = Gauge(
    'dreamops_agent_mode',
    'Current AI agent operation mode (1=yolo, 2=plan, 3=approval)'
)

# Integration metrics
integration_health = Gauge(
    'dreamops_integration_health',
    'Health status of integrations (1=healthy, 0=unhealthy)',
    ['integration_name']
)

integration_requests_total = Counter(
    'dreamops_integration_requests_total',
    'Total requests to integrations',
    ['integration_name', 'method', 'status']
)

integration_request_duration = Histogram(
    'dreamops_integration_request_seconds',
    'Duration of integration requests',
    ['integration_name', 'method'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)

# API metrics
http_requests_total = Counter(
    'dreamops_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'dreamops_http_request_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

http_requests_in_progress = Gauge(
    'dreamops_http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method']
)

# Database metrics
db_connections_active = Gauge(
    'dreamops_db_connections_active',
    'Number of active database connections'
)

db_query_duration = Histogram(
    'dreamops_db_query_seconds',
    'Duration of database queries',
    ['operation'],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1, 5]
)

# Webhook metrics
webhook_received_total = Counter(
    'dreamops_webhook_received_total',
    'Total webhooks received',
    ['source', 'event_type']
)

webhook_processing_duration = Histogram(
    'dreamops_webhook_processing_seconds',
    'Duration of webhook processing',
    ['source'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)


def get_metrics() -> Response:
    """Generate Prometheus metrics response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def track_request_time(endpoint: str):
    """Decorator to track request timing."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            method = kwargs.get('request', {}).method if hasattr(kwargs.get('request'), 'method') else 'UNKNOWN'
            http_requests_in_progress.labels(method=method).inc()

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status='success'
                ).inc()
                return result
            except Exception as e:
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status='error'
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                http_request_duration.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                http_requests_in_progress.labels(method=method).dec()

        return wrapper
    return decorator


# Helper functions to update metrics
def record_incident(severity: str, status: str, alert_source: str):
    """Record a new incident."""
    incidents_total.labels(
        severity=severity,
        status=status,
        alert_source=alert_source
    ).inc()


def update_active_incidents(severity: str, count: int):
    """Update the count of active incidents."""
    incidents_active.labels(severity=severity).set(count)


def record_incident_resolution(severity: str, resolution_time_seconds: float):
    """Record incident resolution time."""
    incident_resolution_time.labels(severity=severity).observe(resolution_time_seconds)


def record_agent_analysis(mode: str, status: str, duration_seconds: float):
    """Record an AI agent analysis."""
    agent_analysis_total.labels(mode=mode, status=status).inc()
    agent_analysis_duration.labels(mode=mode).observe(duration_seconds)


def record_agent_action(action_type: str, status: str, automated: bool):
    """Record an AI agent action."""
    agent_actions_total.labels(
        action_type=action_type,
        status=status,
        automated=str(automated).lower()
    ).inc()


def update_agent_mode(mode: str):
    """Update the current agent mode."""
    mode_values = {'yolo': 1, 'plan': 2, 'approval': 3}
    agent_mode.set(mode_values.get(mode, 0))


def update_integration_health(integration_name: str, is_healthy: bool):
    """Update integration health status."""
    integration_health.labels(integration_name=integration_name).set(1 if is_healthy else 0)


def record_integration_request(integration_name: str, method: str, status: str, duration: float):
    """Record an integration request."""
    integration_requests_total.labels(
        integration_name=integration_name,
        method=method,
        status=status
    ).inc()
    integration_request_duration.labels(
        integration_name=integration_name,
        method=method
    ).observe(duration)


def record_webhook(source: str, event_type: str, processing_duration: float):
    """Record a webhook event."""
    webhook_received_total.labels(source=source, event_type=event_type).inc()
    webhook_processing_duration.labels(source=source).observe(processing_duration)


def update_db_connections(count: int):
    """Update active database connections."""
    db_connections_active.set(count)


def record_db_query(operation: str, duration: float):
    """Record a database query."""
    db_query_duration.labels(operation=operation).observe(duration)
