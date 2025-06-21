"""
API routes for real-time agent logs streaming.
"""
import uuid

from fastapi import APIRouter, Query, Request

from ..log_streaming import create_sse_response, log_stream_manager

router = APIRouter(
    prefix="/agent-logs",
    tags=["agent-logs"],
    responses={404: {"description": "Not found"}},
)


@router.get("/stream")
async def stream_agent_logs(
    request: Request,
    incident_id: str | None = Query(None, description="Filter logs by incident ID"),
    client_id: str | None = Query(None, description="Client ID for the connection")
):
    """
    Stream real-time AI agent logs via Server-Sent Events (SSE).
    
    This endpoint provides a real-time stream of AI agent activity logs,
    including webhook processing, context gathering, Claude analysis, and
    completion status.
    
    Log levels:
    - ALERT: Critical events like agent activation
    - INFO: General information
    - SUCCESS: Successful operations
    - WARNING: Warning messages
    - ERROR: Error messages
    
    Returns:
        EventSourceResponse: SSE stream of log events
    """
    # Generate client ID if not provided
    if not client_id:
        client_id = str(uuid.uuid4())

    # TODO: Add filtering by incident_id if provided

    return create_sse_response(request, client_id)


@router.post("/test")
async def test_log_stream():
    """
    Test endpoint to generate sample log entries.
    
    This endpoint is useful for testing the log streaming functionality
    without triggering actual PagerDuty webhooks.
    """
    incident_id = f"test-{uuid.uuid4().hex[:8]}"

    # Simulate AI agent activation
    await log_stream_manager.log_alert(
        "🚨 AI AGENT ACTIVATED - Processing test incident",
        incident_id=incident_id,
        stage="activation",
        progress=0.0
    )

    # Simulate webhook received
    await log_stream_manager.log_info(
        "📨 PAGERDUTY WEBHOOK RECEIVED!",
        incident_id=incident_id,
        stage="webhook_received",
        progress=0.1,
        metadata={
            "webhook_type": "incident.triggered",
            "service": "test-service"
        }
    )

    # Simulate agent triggered
    await log_stream_manager.log_info(
        "🤖 ONCALL AGENT TRIGGERED",
        incident_id=incident_id,
        stage="agent_triggered",
        progress=0.2
    )

    # Simulate context gathering
    await log_stream_manager.log_info(
        "🔍 Gathering context from Kubernetes integration",
        incident_id=incident_id,
        integration="kubernetes",
        stage="gathering_context",
        progress=0.3
    )

    await log_stream_manager.log_info(
        "🔍 Gathering context from GitHub integration",
        incident_id=incident_id,
        integration="github",
        stage="gathering_context",
        progress=0.4
    )

    # Simulate Claude analysis
    await log_stream_manager.log_info(
        "🤖 Starting Claude analysis...",
        incident_id=incident_id,
        stage="claude_analysis",
        progress=0.5
    )

    await log_stream_manager.log_info(
        "📊 Claude is analyzing the incident context",
        incident_id=incident_id,
        stage="claude_analysis",
        progress=0.7
    )

    # Simulate completion
    await log_stream_manager.log_success(
        "✅ AI ANALYSIS COMPLETE - 3.45s response time",
        incident_id=incident_id,
        stage="complete",
        progress=1.0,
        metadata={
            "response_time": "3.45s",
            "actions_recommended": 3,
            "severity": "high"
        }
    )

    return {
        "success": True,
        "message": "Test logs generated successfully",
        "incident_id": incident_id
    }
