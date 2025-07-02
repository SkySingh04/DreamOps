"""PagerDuty webhook endpoints."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx

from src.oncall_agent.api.log_streaming import log_stream_manager
from src.oncall_agent.api.models import (
    PagerDutyIncidentData,
    PagerDutyService,
    PagerDutyWebhookPayload,
)
from src.oncall_agent.api.oncall_agent_trigger import OncallAgentTrigger
from src.oncall_agent.api.routers.incidents import ANALYSIS_DB, INCIDENTS_DB
from src.oncall_agent.api.schemas import AIAnalysis, Incident, IncidentStatus, Severity
from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger

router = APIRouter(prefix="/webhook", tags=["webhooks"])
logger = get_logger(__name__)
config = get_config()

# Global trigger instance
agent_trigger: OncallAgentTrigger | None = None

UTC = UTC


async def get_agent_trigger() -> OncallAgentTrigger:
    """Get or create the agent trigger instance."""
    global agent_trigger
    if agent_trigger is None:
        agent_trigger = OncallAgentTrigger(use_enhanced=True)
        await agent_trigger.initialize()
    return agent_trigger


def verify_pagerduty_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify PagerDuty webhook signature."""
    if not secret:
        return True  # Skip verification if no secret configured

    # Handle PagerDuty V3 signature format: v1=<signature>
    if signature and signature.startswith('v1='):
        signature = signature[3:]  # Remove 'v1=' prefix

    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def record_alert_usage(team_id: str, incident_id: str, alert_type: str = "pagerduty"):
    """Record alert usage for the team."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/alert-tracking/record",
                json={
                    "team_id": team_id,
                    "alert_type": alert_type,
                    "incident_id": incident_id,
                    "metadata": {"source": "pagerduty_webhook"}
                }
            )
            if response.status_code == 403:
                # Alert limit reached
                logger.warning(f"Alert limit reached for team {team_id}")
                return False, response.json()
            elif response.status_code == 200:
                data = response.json()
                logger.info(f"Alert recorded: {data['alerts_used']}/{data.get('alerts_remaining', 'unlimited')} used")
                return True, data
            else:
                logger.error(f"Failed to record alert usage: {response.status_code}")
                return True, None  # Don't block on tracking failures
    except Exception as e:
        logger.error(f"Error recording alert usage: {e}")
        return True, None  # Don't block on tracking failures


@router.post("/pagerduty")
async def pagerduty_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_pagerduty_signature: str | None = Header(None)
) -> JSONResponse:
    """
    Handle PagerDuty webhook events.
    
    Processes incident.triggered events and automatically triggers the DreamOps agent.
    """
    logger.info("=" * 80)
    logger.info("📨 PAGERDUTY WEBHOOK RECEIVED!")
    logger.info("=" * 80)

    try:
        # Get raw body for signature verification
        body = await request.body()

        # Verify signature if configured
        webhook_secret = getattr(config, 'pagerduty_webhook_secret', None)
        if webhook_secret and x_pagerduty_signature:
            if not verify_pagerduty_signature(body, x_pagerduty_signature, webhook_secret):
                logger.warning("Invalid PagerDuty webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse payload
        payload_dict = await request.json()

        # Log the raw payload for debugging
        # logger.debug(f"Raw webhook payload: {payload_dict}")

        # Detect if this is a V3 webhook
        logger.info(f"Webhook payload keys: {list(payload_dict.keys())}")
        if 'event' in payload_dict and isinstance(payload_dict['event'], dict):
            # V3 webhook format
            from src.oncall_agent.api.models import PagerDutyV3WebhookPayload
            v3_payload = PagerDutyV3WebhookPayload(**payload_dict)

            logger.info(f"Received PagerDuty V3 webhook: {v3_payload.event.event_type}")

            # Get agent trigger
            trigger = await get_agent_trigger()

            # Process V3 event
            event_data = v3_payload.event.data
            results = []

            # Handle incident events
            if v3_payload.event.event_type.startswith('incident.'):
                incident_data = event_data.get('incident', event_data)

                # Handle different incident statuses
                incident_status = incident_data.get('status')
                incident_id = incident_data.get('id')

                if incident_status == 'resolved':
                    # Log incident resolution
                    logger.info(f"Incident {incident_id} resolved")

                    # Update incident status in DB
                    if incident_id in INCIDENTS_DB:
                        INCIDENTS_DB[incident_id].status = IncidentStatus.RESOLVED
                        INCIDENTS_DB[incident_id].resolved_at = datetime.now(UTC)

                    # Send resolution log to frontend
                    resolved_by = 'System'
                    if v3_payload.event.agent:
                        resolved_by = v3_payload.event.agent.summary or v3_payload.event.agent.type or 'Unknown'

                    await log_stream_manager.log_success(
                        f"✅ Incident resolved: {incident_data.get('title', 'Unknown')}",
                        incident_id=incident_id,
                        stage="incident_resolved",
                        progress=1.0,
                        metadata={
                            "event_type": v3_payload.event.event_type,
                            "resolved_by": resolved_by,
                            "resolved_at": v3_payload.event.occurred_at.isoformat()
                        }
                    )

                    return JSONResponse(
                        status_code=200,
                        content={"status": "success", "message": "Incident resolution logged"}
                    )

                elif incident_status != 'triggered':
                    logger.info(f"Skipping incident {incident_id} with status {incident_status}")
                    return JSONResponse(
                        status_code=200,
                        content={"status": "success", "message": "Incident not in triggered state"}
                    )

                # Convert V3 incident to our format
                incident = PagerDutyIncidentData(
                    id=incident_data.get('id'),
                    incident_number=incident_data.get('incident_number', 0),
                    title=incident_data.get('title', 'Unknown'),
                    description=incident_data.get('description'),
                    created_at=incident_data.get('created_at', v3_payload.event.occurred_at),
                    status=incident_data.get('status', 'triggered'),
                    incident_key=incident_data.get('incident_key'),
                    service=PagerDutyService(
                        id=incident_data.get('service', {}).get('id', 'unknown'),
                        name=incident_data.get('service', {}).get('summary', 'Unknown Service')
                    ) if incident_data.get('service') else None,
                    urgency=incident_data.get('urgency', 'high'),
                    html_url=incident_data.get('html_url', '')
                )

                logger.info(
                    f"Processing V3 incident {incident.incident_number}: {incident.title} "
                    f"(severity: {incident.urgency}, service: {incident.service.name if incident.service else 'unknown'})"
                )

                # Emit structured log for webhook received
                await log_stream_manager.log_info(
                    "📨 PAGERDUTY WEBHOOK RECEIVED!",
                    incident_id=incident.id,
                    stage="webhook_received",
                    progress=0.1,
                    metadata={
                        "webhook_type": v3_payload.event.event_type,
                        "service": incident.service.name if incident.service else "unknown",
                        "urgency": incident.urgency,
                        "title": incident.title
                    }
                )

                # Store incident in our database
                severity_map = {
                    "low": Severity.LOW,
                    "medium": Severity.MEDIUM,
                    "high": Severity.HIGH,
                    "critical": Severity.CRITICAL
                }

                # Create incident record
                inc_record = Incident(
                    id=incident.id,
                    title=incident.title,
                    description=incident.description or "",
                    severity=severity_map.get(incident.urgency.lower(), Severity.HIGH),
                    status=IncidentStatus.TRIGGERED,
                    service_name=incident.service.name if incident.service else "unknown",
                    alert_source="pagerduty",
                    created_at=datetime.now(UTC),
                    metadata={
                        "incident_number": incident.incident_number,
                        "html_url": incident.html_url,
                        "webhook_event": v3_payload.event.event_type
                    },
                    timeline=[{
                        "timestamp": datetime.now(UTC).isoformat(),
                        "event": "incident_created",
                        "description": "Incident triggered via PagerDuty webhook"
                    }]
                )

                INCIDENTS_DB[incident.id] = inc_record

                # Record alert usage for this incident
                team_id = "team_123"  # TODO: Get actual team ID from incident or service
                can_process, usage_data = await record_alert_usage(team_id, incident.id, "pagerduty")
                
                if not can_process:
                    # Alert limit reached
                    logger.warning(f"Alert limit reached for team {team_id}, skipping agent processing")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "status": "error",
                            "message": "Alert limit reached. Please upgrade your subscription.",
                            "alert_usage": usage_data
                        }
                    )

                # Process immediately
                result = await trigger.trigger_oncall_agent(
                    incident,
                    {"webhook_event": v3_payload.event.event_type}
                )

                # Store the analysis result
                if result.get("status") == "success" and result.get("agent_response"):
                    agent_response = result["agent_response"]

                    # Store full analysis data
                    ANALYSIS_DB[incident.id] = {
                        "incident_id": incident.id,
                        "status": "analyzed",
                        "analysis": agent_response.get("analysis", ""),
                        "parsed_analysis": agent_response.get("parsed_analysis", {}),
                        "confidence_score": agent_response.get("confidence_score", 0.85),
                        "risk_level": agent_response.get("risk_level", "medium"),
                        "context_gathered": agent_response.get("context_gathered", {}),
                        "full_context": agent_response.get("full_context", {}),
                        "timestamp": datetime.now(UTC).isoformat(),
                        "processing_time": result.get("processing_time", 0)
                    }

                    # Update incident with AI analysis
                    inc_record.ai_analysis = AIAnalysis(
                        summary=agent_response.get("parsed_analysis", {}).get("root_cause", ["Analysis processing"])[0] if agent_response.get("parsed_analysis", {}).get("root_cause") else "AI analysis completed",
                        root_cause=" ".join(agent_response.get("parsed_analysis", {}).get("root_cause", [])),
                        impact_assessment=" ".join(agent_response.get("parsed_analysis", {}).get("impact", [])),
                        recommended_actions=[
                            {
                                "action": action,
                                "reason": "AI recommended action",
                                "priority": "high" if i < 2 else "medium"
                            }
                            for i, action in enumerate(agent_response.get("parsed_analysis", {}).get("immediate_actions", [])[:5])
                        ],
                        confidence_score=agent_response.get("confidence_score", 0.85),
                        related_incidents=[],
                        knowledge_base_references=[]
                    )

                    # Add to timeline
                    inc_record.timeline.append({
                        "timestamp": datetime.now(UTC).isoformat(),
                        "event": "ai_analysis_complete",
                        "description": f"AI analysis completed with {agent_response.get('confidence_score', 0.85)*100:.0f}% confidence",
                        "automated": True
                    })

                    logger.info("\n" + "="*80)
                    logger.info("🤖 AGENT ANALYSIS COMPLETE:")
                    logger.info("="*80)
                    analysis = agent_response.get("analysis", "")
                    for line in analysis.split('\n'):
                        if line.strip():
                            logger.info(line)
                    logger.info("="*80 + "\n")

                    # Log context gathered
                    if agent_response.get("context_gathered"):
                        logger.info("📊 Context gathered from integrations:")
                        for integration, success in agent_response["context_gathered"].items():
                            logger.info(f"  - {integration}: {'✅ Success' if success else '❌ Failed'}")

                results.append(result)
            else:
                logger.info(f"Ignoring non-incident event: {v3_payload.event.event_type}")
                return JSONResponse(
                    status_code=200,
                    content={"status": "success", "message": f"Event type {v3_payload.event.event_type} acknowledged"}
                )

        else:
            # Legacy V2 format
            payload = PagerDutyWebhookPayload(**payload_dict)

            if not payload.messages:
                return JSONResponse(
                    status_code=200,
                    content={"status": "success", "message": "No messages to process"}
                )

            logger.info(f"Received PagerDuty V2 webhook with {len(payload.messages)} messages")

            # Get agent trigger
            trigger = await get_agent_trigger()

            # Process each message
            results = []
            for message in payload.messages:
                incident = message.incident

                # Only process triggered incidents
                if incident.status != "triggered":
                    logger.info(f"Skipping incident {incident.id} with status {incident.status}")
                    continue

                # Log incident details
                logger.info(
                    f"Processing incident {incident.incident_number}: {incident.title} "
                    f"(severity: {incident.urgency}, service: {incident.service.name if incident.service else 'unknown'})"
                )

                # Trigger agent in background for faster webhook response
                if len(payload.messages) > 1:
                    # Multiple alerts - process in background
                    background_tasks.add_task(
                        trigger.trigger_oncall_agent,
                        incident,
                        {"webhook_event": "incident.triggered"}
                    )
                    results.append({
                        "incident_id": incident.id,
                        "status": "queued",
                        "message": "Incident queued for processing"
                    })
                else:
                    # Single alert - process immediately
                    result = await trigger.trigger_oncall_agent(
                        incident,
                        {"webhook_event": "incident.triggered"}
                    )

                    # Log the agent's analysis for visibility
                    if result.get("status") == "success" and result.get("agent_response", {}).get("analysis"):
                        logger.info("\n" + "="*80)
                        logger.info("🤖 AGENT ANALYSIS COMPLETE:")
                        logger.info("="*80)
                        analysis = result["agent_response"]["analysis"]
                        for line in analysis.split('\n'):
                            if line.strip():
                                logger.info(line)
                        logger.info("="*80 + "\n")

                        # Log context gathered
                        if result.get("agent_response", {}).get("context_gathered"):
                            logger.info("📊 Context gathered from integrations:")
                            for integration, success in result["agent_response"]["context_gathered"].items():
                                logger.info(f"  - {integration}: {'✅ Success' if success else '❌ Failed'}")

                        # Log executed actions in YOLO mode
                        if result.get("agent_response", {}).get("execution_mode") == "YOLO":
                            logger.info("\n🚀 YOLO MODE - Automated Actions Executed:")

                            # Log regular automated actions
                            if result.get("agent_response", {}).get("executed_actions"):
                                logger.info("📌 Automated actions:")
                                for action in result["agent_response"]["executed_actions"]:
                                    status_icon = "✅" if action['status'] == 'success' else "❌"
                                    logger.info(f"  {status_icon} {action['action']}")

                            # Log remediation commands
                            if result.get("agent_response", {}).get("remediation_commands_executed"):
                                logger.info("🔧 Remediation commands from Claude's analysis:")
                                for cmd_result in result["agent_response"]["remediation_commands_executed"]:
                                    status_icon = "✅" if cmd_result['status'] == 'success' else "❌"
                                    logger.info(f"  {status_icon} {cmd_result['command']}")
                                    if cmd_result['status'] != 'success' and 'error' in cmd_result:
                                        logger.info(f"     Error: {cmd_result['error']}")

                    results.append(result)

        # Return response
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Processed {len(results)} incidents",
                "results": results,
                "queue_status": trigger.get_queue_status()
            }
        )

    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/pagerduty/status")
async def webhook_status() -> dict[str, Any]:
    """Get webhook processing status."""
    trigger = await get_agent_trigger()
    return {
        "status": "healthy",
        "queue": trigger.get_queue_status(),
        "webhook_secret_configured": bool(getattr(config, 'pagerduty_webhook_secret', None))
    }


@router.post("/pagerduty/test")
async def test_webhook() -> dict[str, Any]:
    """Test endpoint to verify webhook configuration."""
    return {
        "status": "success",
        "message": "Webhook endpoint is configured correctly",
        "config": {
            "secret_configured": bool(getattr(config, 'pagerduty_webhook_secret', None)),
            "agent_available": agent_trigger is not None
        }
    }
