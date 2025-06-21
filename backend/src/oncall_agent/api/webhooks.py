"""PagerDuty webhook endpoints."""

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from src.oncall_agent.api.models import PagerDutyWebhookPayload
from src.oncall_agent.api.oncall_agent_trigger import OncallAgentTrigger
from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger

router = APIRouter(prefix="/webhook", tags=["webhooks"])
logger = get_logger(__name__)
config = get_config()

# Global trigger instance
agent_trigger: OncallAgentTrigger | None = None


async def get_agent_trigger() -> OncallAgentTrigger:
    """Get or create the agent trigger instance."""
    global agent_trigger
    if agent_trigger is None:
        agent_trigger = OncallAgentTrigger()
        await agent_trigger.initialize()
    return agent_trigger


def verify_pagerduty_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify PagerDuty webhook signature."""
    if not secret:
        return True  # Skip verification if no secret configured

    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/pagerduty")
async def pagerduty_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_pagerduty_signature: str | None = Header(None)
) -> JSONResponse:
    """
    Handle PagerDuty webhook events.
    
    Processes incident.triggered events and automatically triggers the oncall agent.
    """
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
        payload = PagerDutyWebhookPayload(**payload_dict)

        logger.info(f"Received PagerDuty webhook with {len(payload.messages)} messages")

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
                    {"webhook_event": payload.event}
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
                    {"webhook_event": payload.event}
                )
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
