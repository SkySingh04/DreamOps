"""PagerDuty webhook endpoints."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from src.oncall_agent.api.log_streaming import log_stream_manager
from src.oncall_agent.api.models import (
    PagerDutyIncidentData,
    PagerDutyService,
    PagerDutyWebhookPayload,
)
from src.oncall_agent.api.oncall_agent_trigger import OncallAgentTrigger
from src.oncall_agent.api.routers.incidents import INCIDENTS_DB
from src.oncall_agent.api.schemas import Incident, IncidentStatus, Severity
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


async def record_alert_usage(user_id: str, incident_id: str, alert_type: str = "pagerduty"):
    """Record alert usage for the user."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/v1/alert-tracking/record",
                json={
                    "user_id": user_id,
                    "alert_type": alert_type,
                    "incident_id": incident_id,
                    "metadata": {"source": "pagerduty_webhook"}
                }
            )
            if response.status_code == 403:
                # Alert limit reached
                logger.warning(f"Alert limit reached for user {user_id}")
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

                # Check alert usage - using user_id "1" for now (should be from incident context)
                user_id = "1"  # Default user for webhook incidents
                allowed, usage_data = await record_alert_usage(user_id, incident.id)

                if not allowed:
                    # Alert limit reached
                    logger.warning(f"Alert limit reached for user {user_id}, incident {incident.id} not processed")

                    # Send limit reached notification
                    await log_stream_manager.log_warning(
                        "⚠️ Alert limit reached for user. Upgrade required.",
                        incident_id=incident.id,
                        stage="alert_limit_reached",
                        metadata={
                            "alerts_used": usage_data.get("detail", {}).get("alerts_used", 0),
                            "alerts_limit": usage_data.get("detail", {}).get("alerts_limit", 3),
                            "account_tier": usage_data.get("detail", {}).get("account_tier", "free")
                        }
                    )

                    return JSONResponse(
                        status_code=403,
                        content={
                            "status": "limit_reached",
                            "message": "Alert limit reached. Please upgrade your subscription.",
                            "usage": usage_data.get("detail", {})
                        }
                    )

                # Process incident
                await log_stream_manager.log_info(
                    f"🔍 Processing incident: {incident.title}",
                    incident_id=incident.id,
                    stage="webhook_received",
                    metadata={
                        "service": incident.service.name if incident.service else "Unknown",
                        "urgency": incident.urgency,
                        "alerts_used": usage_data.get("alerts_used") if usage_data else None
                    }
                )

                # Store incident in memory
                memory_incident = Incident(
                    id=incident.id,
                    title=incident.title,
                    description=incident.description or "",
                    severity=Severity.HIGH if incident.urgency == 'high' else Severity.MEDIUM,
                    status=IncidentStatus.OPEN,
                    source="pagerduty",
                    source_id=incident.id,
                    created_at=datetime.now(UTC),
                    userId=1  # Default user ID
                )
                INCIDENTS_DB[incident.id] = memory_incident

                # Process incident via agent
                logger.info(f"🤖 Processing incident via agent: {incident.id}")
                result = await trigger.process_incident_async(incident)
                results.append(result)

                # Log the result
                logger.info(f"📊 Agent processing result: {result}")

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "event_type": v3_payload.event.event_type,
                    "incidents_processed": len(results),
                    "results": results
                }
            )

        else:
            # Legacy webhook format
            payload = PagerDutyWebhookPayload(**payload_dict)
            logger.info(f"Received PagerDuty webhook with {len(payload.messages)} messages")

            # Process each message
            results = []
            trigger = await get_agent_trigger()

            for message in payload.messages:
                event = message.event
                incident = message.incident

                logger.info(f"Processing event: {event} for incident: {incident.incident_number}")

                # Only process triggered incidents
                if event == "incident.trigger":
                    # Check alert usage - using user_id "1" for now
                    user_id = "1"  # Default user for webhook incidents
                    allowed, usage_data = await record_alert_usage(user_id, incident.id)

                    if not allowed:
                        # Alert limit reached
                        logger.warning(f"Alert limit reached for user {user_id}, incident {incident.id} not processed")

                        # Send limit reached notification
                        await log_stream_manager.log_warning(
                            "⚠️ Alert limit reached for user. Upgrade required.",
                            incident_id=incident.id,
                            stage="alert_limit_reached",
                            metadata={
                                "alerts_used": usage_data.get("detail", {}).get("alerts_used", 0),
                                "alerts_limit": usage_data.get("detail", {}).get("alerts_limit", 3),
                                "account_tier": usage_data.get("detail", {}).get("account_tier", "free")
                            }
                        )

                        return JSONResponse(
                            status_code=403,
                            content={
                                "status": "limit_reached",
                                "message": "Alert limit reached. Please upgrade your subscription.",
                                "usage": usage_data.get("detail", {})
                            }
                        )

                    # Process incident
                    await log_stream_manager.log_info(
                        f"🔍 Processing incident: {incident.title}",
                        incident_id=incident.id,
                        stage="webhook_received",
                        metadata={
                            "service": incident.service.name if incident.service else "Unknown",
                            "urgency": incident.urgency,
                            "event": event,
                            "alerts_used": usage_data.get("alerts_used") if usage_data else None
                        }
                    )

                    # Store incident in memory
                    memory_incident = Incident(
                        id=incident.id,
                        title=incident.title,
                        description=incident.description or "",
                        severity=Severity.HIGH if incident.urgency == 'high' else Severity.MEDIUM,
                        status=IncidentStatus.OPEN,
                        source="pagerduty",
                        source_id=incident.id,
                        created_at=datetime.now(UTC),
                        userId=1  # Default user ID
                    )
                    INCIDENTS_DB[incident.id] = memory_incident

                    # Process with agent
                    logger.info(f"🤖 Triggering DreamOps agent for incident: {incident.id}")
                    result = await trigger.process_incident_async(incident)
                    results.append(result)

                    # Log the result
                    await log_stream_manager.log_success(
                        "✅ Incident processed successfully",
                        incident_id=incident.id,
                        stage="agent_triggered",
                        progress=0.5,
                        metadata={"agent_result": result}
                    )

                    logger.info(f"✅ Agent triggered successfully: {result}")
                else:
                    logger.info(f"Skipping event {event} - only processing incident.trigger events")

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": f"Processed {len(results)} incidents",
                    "results": results
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)

        # Log error to frontend
        await log_stream_manager.log_error(
            f"❌ Error processing webhook: {str(e)}",
            stage="webhook_error",
            metadata={"error": str(e)}
        )

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pagerduty/status")
async def webhook_status() -> dict[str, Any]:
    """Get PagerDuty webhook configuration status."""
    return {
        "webhook_enabled": config.pagerduty_enabled,
        "secret_configured": bool(getattr(config, 'pagerduty_webhook_secret', None)),
        "api_key_configured": bool(getattr(config, 'pagerduty_api_key', None)),
        "user_email_configured": bool(getattr(config, 'pagerduty_user_email', None)),
        "webhook_url": f"{config.api_host}:{config.api_port}/webhook/pagerduty",
        "agent_status": {
            "initialized": agent_trigger is not None,
            "agent_available": agent_trigger is not None
        }
    }
