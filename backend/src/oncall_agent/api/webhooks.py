"""PagerDuty webhook endpoints."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from src.oncall_agent.api.dependencies import get_user_from_request
from src.oncall_agent.api.log_streaming import log_stream_manager
from src.oncall_agent.api.models import (
    PagerDutyIncidentData,
    PagerDutyService,
    PagerDutyWebhookPayload,
)
from src.oncall_agent.api.oncall_agent_trigger import OncallAgentTrigger
from src.oncall_agent.api.schemas import Incident, IncidentStatus, Severity
from src.oncall_agent.config import get_config
from src.oncall_agent.services import agent_settings_service
from src.oncall_agent.services.dashboard_sync_service import (
    record_ai_action,
    sync_incident_to_dashboard,
    update_incident_status,
)
from src.oncall_agent.services.incident_service import (
    AnalysisService,
    IncidentService,
)
from src.oncall_agent.services.slack_notifier import get_slack_notifier
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

                    # Update incident status in database
                    try:
                        existing_incident = await IncidentService.get(incident_id)
                        if existing_incident:
                            existing_incident.status = IncidentStatus.RESOLVED
                            existing_incident.resolved_at = datetime.now(UTC)
                            await IncidentService.update(existing_incident)
                    except Exception as db_err:
                        logger.warning(f"Could not update incident status in DB: {db_err}")

                    # Update dashboard incident status
                    try:
                        await update_incident_status(incident_id, "resolved")
                        logger.info(f"Updated dashboard incident status: {incident_id}")
                    except Exception as sync_err:
                        logger.warning(f"Could not update dashboard incident status: {sync_err}")

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

                # Get user from request headers (falls back to demo user if no Authentik headers)
                current_user = await get_user_from_request(request)
                user_id = current_user.user_id
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

                # Store incident in database
                db_incident = Incident(
                    id=incident.id,
                    title=incident.title,
                    description=incident.description or "",
                    severity=Severity.HIGH if incident.urgency == 'high' else Severity.MEDIUM,
                    status=IncidentStatus.TRIGGERED,
                    service_name=incident.service.name if incident.service else "Unknown Service",
                    alert_source="pagerduty",
                    created_at=datetime.now(UTC),
                    metadata={
                        "source_id": incident.id,
                        "urgency": incident.urgency,
                        "html_url": incident.html_url,
                        "userId": int(user_id) if user_id.isdigit() else 1
                    }
                )
                try:
                    await IncidentService.create(db_incident)
                except Exception as db_err:
                    logger.warning(f"Could not store incident in DB: {db_err}")

                # Sync to dashboard table for frontend
                dashboard_incident_id = None
                try:
                    dashboard_incident_id = await sync_incident_to_dashboard(
                        source_id=incident.id,
                        title=incident.title,
                        description=incident.description or "",
                        severity="high" if incident.urgency == 'high' else "medium",
                        status="triggered",
                        source="pagerduty",
                        user_id=int(user_id) if user_id.isdigit() else None,
                        metadata={
                            "urgency": incident.urgency,
                            "html_url": incident.html_url,
                            "service": incident.service.name if incident.service else "Unknown"
                        }
                    )
                    logger.info(f"Synced incident to dashboard: {dashboard_incident_id}")
                except Exception as sync_err:
                    logger.warning(f"Could not sync incident to dashboard: {sync_err}")

                # Check if AI agent is enabled before processing
                # ENV VAR takes precedence over UI toggle
                env_ai_enabled = config.ai_agent_enabled
                if not env_ai_enabled:
                    # AI agent is disabled via ENV VAR - this takes precedence
                    logger.info(f"⏸️ AI agent is DISABLED via ENV VAR (AI_AGENT_ENABLED=false) - skipping analysis for incident: {incident.id}")
                    await log_stream_manager.log_info(
                        "⏸️ AI agent is disabled via environment variable - incident logged but not analyzed",
                        incident_id=incident.id,
                        stage="ai_agent_disabled",
                        metadata={
                            "ai_agent_enabled": False,
                            "reason": "AI_AGENT_ENABLED environment variable is set to false"
                        }
                    )

                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "skipped",
                            "event_type": v3_payload.event.event_type,
                            "incident_id": incident.id,
                            "message": "AI agent is disabled via environment variable. Incident logged but not analyzed.",
                            "ai_agent_enabled": False,
                            "disabled_by": "environment_variable"
                        }
                    )

                # Check UI toggle (only if ENV VAR allows)
                ui_ai_enabled = await agent_settings_service.is_ai_agent_enabled(user_id=1)
                if not ui_ai_enabled:
                    # AI agent is disabled via UI toggle
                    logger.info(f"⏸️ AI agent is DISABLED via UI toggle - skipping analysis for incident: {incident.id}")
                    await log_stream_manager.log_info(
                        "⏸️ AI agent is disabled via UI toggle - incident logged but not analyzed",
                        incident_id=incident.id,
                        stage="ai_agent_disabled",
                        metadata={
                            "ai_agent_enabled": False,
                            "reason": "AI agent toggle is OFF in UI"
                        }
                    )

                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "skipped",
                            "event_type": v3_payload.event.event_type,
                            "incident_id": incident.id,
                            "message": "AI agent is disabled via UI toggle. Incident logged but not analyzed.",
                            "ai_agent_enabled": False,
                            "disabled_by": "ui_toggle"
                        }
                    )

                # Process incident via agent
                logger.info(f"🤖 Processing incident via agent: {incident.id}")
                result = await trigger.trigger_oncall_agent(incident)
                results.append(result)

                # Log the result
                logger.info(f"📊 Agent processing result: {result}")

                # Record AI action in dashboard
                if dashboard_incident_id:
                    try:
                        ai_mode = result.get("agent_response", {}).get("ai_mode", "analysis")
                        action_type = f"incident_analysis ({ai_mode})"
                        await record_ai_action(
                            action=action_type,
                            description=f"Analyzed incident: {incident.title}",
                            incident_id=dashboard_incident_id,
                            user_id=int(user_id) if user_id.isdigit() else None,
                            status="completed",
                            metadata={
                                "ai_mode": ai_mode,
                                "k8s_alert_type": result.get("agent_response", {}).get("k8s_alert_type"),
                                "pagerduty_incident_id": incident.id
                            }
                        )
                    except Exception as action_err:
                        logger.warning(f"Could not record AI action: {action_err}")

                # Store the analysis in database for report downloads
                if result.get("agent_response", {}).get("analysis"):
                    agent_response = result["agent_response"]
                    analysis_data = {
                        "status": "analyzed",
                        "analysis": agent_response["analysis"],
                        "parsed_analysis": agent_response.get("parsed_analysis", {}),
                        "ai_mode": agent_response.get("ai_mode", "standard"),
                        "k8s_alert_type": agent_response.get("k8s_alert_type"),
                        "confidence_score": agent_response.get("confidence_score", 0.85),
                        "risk_level": agent_response.get("risk_level", "medium"),
                        "context": result.get("context", {}),
                        "processed_at": datetime.now(UTC).isoformat()
                    }
                    try:
                        await AnalysisService.save(incident.id, analysis_data)
                    except Exception as db_err:
                        logger.warning(f"Could not store analysis in DB: {db_err}")

                # Post analysis to Slack if configured
                try:
                    slack_notifier = get_slack_notifier()
                    if slack_notifier.enabled and result.get("agent_response", {}).get("analysis"):
                        analysis = result["agent_response"]["analysis"]
                        severity = "high" if incident.urgency == "high" else "medium"
                        slack_result = await slack_notifier.post_incident_analysis(
                            incident_id=incident.id,
                            title=incident.title,
                            severity=severity,
                            analysis=analysis
                        )
                        if slack_result.get("success"):
                            logger.info(f"📢 Posted incident analysis to Slack for {incident.id}")
                        else:
                            logger.warning(f"Failed to post to Slack: {slack_result.get('error')}")
                except Exception as slack_err:
                    logger.error(f"Error posting to Slack: {slack_err}")

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
                    # Get user from request headers (falls back to demo user if no Authentik headers)
                    current_user = await get_user_from_request(request)
                    user_id = current_user.user_id
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

                    # Store incident in database
                    db_incident = Incident(
                        id=incident.id,
                        title=incident.title,
                        description=incident.description or "",
                        severity=Severity.HIGH if incident.urgency == 'high' else Severity.MEDIUM,
                        status=IncidentStatus.TRIGGERED,
                        service_name=incident.service.name if hasattr(incident, 'service') and incident.service else "Unknown Service",
                        alert_source="pagerduty",
                        created_at=datetime.now(UTC),
                        metadata={
                            "source_id": incident.id,
                            "urgency": getattr(incident, 'urgency', 'medium'),
                            "userId": int(user_id) if user_id.isdigit() else 1
                        }
                    )
                    try:
                        await IncidentService.create(db_incident)
                    except Exception as db_err:
                        logger.warning(f"Could not store incident in DB: {db_err}")

                    # Sync to dashboard table for frontend
                    dashboard_incident_id = None
                    try:
                        dashboard_incident_id = await sync_incident_to_dashboard(
                            source_id=incident.id,
                            title=incident.title,
                            description=incident.description or "",
                            severity="high" if getattr(incident, 'urgency', 'medium') == 'high' else "medium",
                            status="triggered",
                            source="pagerduty",
                            user_id=int(user_id) if user_id.isdigit() else None,
                            metadata={
                                "urgency": getattr(incident, 'urgency', 'medium'),
                                "service": incident.service.name if hasattr(incident, 'service') and incident.service else "Unknown"
                            }
                        )
                        logger.info(f"Synced incident to dashboard: {dashboard_incident_id}")
                    except Exception as sync_err:
                        logger.warning(f"Could not sync incident to dashboard: {sync_err}")

                    # Check if AI agent is enabled before processing
                    # ENV VAR takes precedence over UI toggle
                    env_ai_enabled = config.ai_agent_enabled
                    if not env_ai_enabled:
                        logger.info(f"⏸️ AI agent is DISABLED via ENV VAR (AI_AGENT_ENABLED=false) - skipping analysis for incident: {incident.id}")
                        await log_stream_manager.log_info(
                            "⏸️ AI agent is disabled via environment variable - incident logged but not analyzed",
                            incident_id=incident.id,
                            stage="ai_agent_disabled",
                            metadata={
                                "ai_agent_enabled": False,
                                "reason": "AI_AGENT_ENABLED environment variable is set to false"
                            }
                        )
                        continue

                    ui_ai_enabled = await agent_settings_service.is_ai_agent_enabled(user_id=1)
                    if not ui_ai_enabled:
                        logger.info(f"⏸️ AI agent is DISABLED via UI toggle - skipping analysis for incident: {incident.id}")
                        await log_stream_manager.log_info(
                            "⏸️ AI agent is disabled via UI toggle - incident logged but not analyzed",
                            incident_id=incident.id,
                            stage="ai_agent_disabled",
                            metadata={
                                "ai_agent_enabled": False,
                                "reason": "AI agent toggle is OFF in UI"
                            }
                        )
                        continue

                    # Process with agent
                    logger.info(f"🤖 Triggering DreamOps agent for incident: {incident.id}")
                    result = await trigger.trigger_oncall_agent(incident)
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


@router.post("/pagerduty/test")
async def send_test_pagerduty_event() -> dict[str, Any]:
    """
    Send a test PagerDuty event and IMMEDIATELY resolve it.

    This is safe to use for testing - the incident is resolved within seconds
    to avoid disturbing on-call engineers.

    The event summary includes "(TEST BY SKY)" to clearly mark it as a test.
    """
    import time

    # Get the routing key from config
    routing_key = getattr(config, 'pagerduty_events_integration_key', None)
    if not routing_key:
        raise HTTPException(
            status_code=400,
            detail="PagerDuty Events Integration Key not configured. Set PAGERDUTY_EVENTS_INTEGRATION_KEY in environment."
        )

    # Generate unique dedup key
    dedup_key = f"test-sky-{int(time.time())}"

    try:
        # Send trigger event with realistic K8s details for proper agent analysis
        trigger_payload = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "dedup_key": dedup_key,
            "payload": {
                "summary": "(TEST BY SKY) K8s Pod CrashLoopBackOff - dreamops-backend-7f8b9c6d5d-test123 in namespace default",
                "severity": "warning",
                "source": "dreamops-test-button",
                "component": "kubernetes",
                "group": "infrastructure",
                "class": "pod_crash",
                "custom_details": {
                    "test": True,
                    "triggered_by": "DreamOps Test Button",
                    "environment": "production",
                    "auto_resolve": True,
                    "alert_type": "pod_crash",
                    "namespace": "default",
                    "pod_name": "dreamops-backend-7f8b9c6d5d-test123",
                    "container_name": "backend",
                    "restart_count": 5,
                    "exit_code": 137,
                    "reason": "OOMKilled",
                    "last_state": "Terminated",
                    "message": "Container exceeded memory limit and was killed by OOM killer",
                    "node": "k8s-worker-01",
                    "deployment": "dreamops-backend",
                    "labels": {
                        "app": "dreamops-backend",
                        "version": "v1.2.3"
                    }
                }
            }
        }

        async with httpx.AsyncClient() as client:
            # Trigger the incident
            trigger_response = await client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=trigger_payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )

            if trigger_response.status_code != 202:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to trigger test event: {trigger_response.text}"
                )

            trigger_result = trigger_response.json()
            logger.info(f"Test event triggered: {trigger_result}")

            # IMMEDIATELY resolve the incident (within 1 second)
            resolve_payload = {
                "routing_key": routing_key,
                "event_action": "resolve",
                "dedup_key": dedup_key
            }

            resolve_response = await client.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=resolve_payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )

            if resolve_response.status_code != 202:
                logger.error(f"Failed to resolve test event: {resolve_response.text}")
                # Still return success but warn about resolution failure
                return {
                    "status": "partial_success",
                    "message": "Test event triggered but failed to auto-resolve. Please resolve manually!",
                    "dedup_key": dedup_key,
                    "trigger_result": trigger_result,
                    "warning": "RESOLVE THIS INCIDENT MANUALLY TO AVOID DISTURBING ON-CALL"
                }

            resolve_result = resolve_response.json()
            logger.info(f"Test event resolved: {resolve_result}")

            return {
                "status": "success",
                "message": "Test event triggered and immediately resolved",
                "dedup_key": dedup_key,
                "trigger_result": trigger_result,
                "resolve_result": resolve_result
            }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout connecting to PagerDuty")
    except Exception as e:
        logger.error(f"Error sending test event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pagerduty/status")
async def webhook_status() -> dict[str, Any]:
    """Get PagerDuty webhook configuration status."""
    api_key_configured = bool(getattr(config, 'pagerduty_api_key', None))

    return {
        "webhook_enabled": config.pagerduty_enabled,
        "secret_configured": bool(getattr(config, 'pagerduty_webhook_secret', None)),
        "api_key_configured": api_key_configured,
        "user_email_configured": bool(getattr(config, 'pagerduty_user_email', None)),
        "webhook_url": f"{config.api_host}:{config.api_port}/webhook/pagerduty",
        "agent_status": {
            "initialized": agent_trigger is not None,
            "agent_available": agent_trigger is not None
        },
        "features": {
            "webhook_receiving": True,  # Always available
            "incident_acknowledgment": api_key_configured,
            "incident_resolution": api_key_configured,
            "incident_notes": api_key_configured
        },
        "note": "API key is optional. Without it, incidents will be received and processed, but cannot be updated in PagerDuty."
    }
