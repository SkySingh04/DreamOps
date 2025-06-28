"""PagerDuty API client for incident management."""

import logging
from typing import Any

import aiohttp

from .config import get_config

logger = logging.getLogger(__name__)


class PagerDutyClient:
    """Client for interacting with PagerDuty API."""

    def __init__(self):
        """Initialize PagerDuty client."""
        self.config = get_config()
        self.api_key = self.config.pagerduty_api_key
        self.base_url = "https://api.pagerduty.com"
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Enter async context."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self.session:
            await self.session.close()

    def _get_headers(self) -> dict[str, str]:
        """Get headers for PagerDuty API requests."""
        return {
            "Authorization": f"Token token={self.api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json"
        }

    async def resolve_incident(
        self,
        incident_id: str,
        resolution_note: str = "Resolved by Oncall Agent",
        resolver_email: str | None = None
    ) -> bool:
        """Resolve a PagerDuty incident.
        
        Args:
            incident_id: PagerDuty incident ID
            resolution_note: Note explaining the resolution
            resolver_email: Email of the resolver (required by PagerDuty API)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.api_key:
            logger.warning("PagerDuty API key not configured - cannot resolve incident")
            return False

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = f"{self.base_url}/incidents/{incident_id}"
            payload = {
                "incident": {
                    "type": "incident",
                    "status": "resolved",
                    "resolution": resolution_note
                }
            }

            headers = self._get_headers()
            headers["From"] = resolver_email or self.config.pagerduty_user_email  # Required by PagerDuty API

            async with self.session.put(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"✅ Successfully resolved PagerDuty incident: {incident_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to resolve incident {incident_id}: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error resolving PagerDuty incident {incident_id}: {e}")
            return False

    async def acknowledge_incident(
        self,
        incident_id: str,
        acknowledger_email: str | None = None
    ) -> bool:
        """Acknowledge a PagerDuty incident.
        
        Args:
            incident_id: PagerDuty incident ID
            acknowledger_email: Email of the acknowledger
            
        Returns:
            True if successful, False otherwise
        """
        if not self.api_key:
            logger.warning("PagerDuty API key not configured - cannot acknowledge incident")
            return False

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = f"{self.base_url}/incidents/{incident_id}"
            payload = {
                "incident": {
                    "type": "incident",
                    "status": "acknowledged"
                }
            }

            headers = self._get_headers()
            headers["From"] = acknowledger_email or self.config.pagerduty_user_email

            async with self.session.put(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"✅ Successfully acknowledged PagerDuty incident: {incident_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to acknowledge incident {incident_id}: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error acknowledging PagerDuty incident {incident_id}: {e}")
            return False

    async def add_note_to_incident(
        self,
        incident_id: str,
        content: str,
        user_email: str | None = None
    ) -> bool:
        """Add a note to a PagerDuty incident.
        
        Args:
            incident_id: PagerDuty incident ID
            content: Note content
            user_email: Email of the note creator
            
        Returns:
            True if successful, False otherwise
        """
        if not self.api_key:
            logger.warning("PagerDuty API key not configured - cannot add note")
            return False

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = f"{self.base_url}/incidents/{incident_id}/notes"
            payload = {
                "note": {
                    "content": content
                }
            }

            headers = self._get_headers()
            headers["From"] = user_email or self.config.pagerduty_user_email

            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 201:
                    logger.info(f"✅ Successfully added note to incident: {incident_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to add note to incident {incident_id}: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error adding note to incident {incident_id}: {e}")
            return False

    async def trigger_event(
        self,
        summary: str,
        severity: str = "critical",
        source: str = "oncall-agent-chaos",
        dedup_key: str | None = None,
        custom_details: dict[str, Any] | None = None,
        integration_key: str | None = None
    ) -> dict[str, Any]:
        """Trigger a PagerDuty event using Events API v2.
        
        Args:
            summary: Brief description of the event
            severity: One of 'critical', 'error', 'warning', 'info'
            source: Source system that generated the event
            dedup_key: Deduplication key to prevent duplicate incidents
            custom_details: Additional details about the event
            integration_key: Override the default integration key
            
        Returns:
            API response containing event status and dedup_key
        """
        routing_key = integration_key or self.config.pagerduty_events_integration_key

        if not routing_key:
            logger.warning("PagerDuty Events Integration Key not configured - cannot trigger event")
            return {"error": "No integration key configured"}

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            url = "https://events.pagerduty.com/v2/enqueue"

            payload = {
                "routing_key": routing_key,
                "event_action": "trigger",
                "payload": {
                    "summary": summary,
                    "source": source,
                    "severity": severity
                }
            }

            if dedup_key:
                payload["dedup_key"] = dedup_key

            if custom_details:
                payload["payload"]["custom_details"] = custom_details

            headers = {
                "Content-Type": "application/json"
            }

            async with self.session.post(url, json=payload, headers=headers) as response:
                response_data = await response.json()

                if response.status == 202:
                    logger.info(f"✅ Successfully triggered PagerDuty event: {summary}")
                    return response_data
                else:
                    logger.error(f"❌ Failed to trigger event: {response.status} - {response_data}")
                    return {"error": f"Failed with status {response.status}", "details": response_data}

        except Exception as e:
            logger.error(f"❌ Error triggering PagerDuty event: {e}")
            return {"error": str(e)}


# Global instance for easy access
pagerduty_client = PagerDutyClient()


async def resolve_pagerduty_incident(
    incident_id: str,
    resolution_note: str = "Automatically resolved by Oncall Agent"
) -> bool:
    """Convenience function to resolve a PagerDuty incident."""
    async with PagerDutyClient() as client:
        return await client.resolve_incident(incident_id, resolution_note)


async def acknowledge_pagerduty_incident(incident_id: str) -> bool:
    """Convenience function to acknowledge a PagerDuty incident."""
    async with PagerDutyClient() as client:
        return await client.acknowledge_incident(incident_id)


async def trigger_pagerduty_event(
    summary: str,
    severity: str = "critical",
    source: str = "oncall-agent-chaos",
    dedup_key: str | None = None,
    custom_details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Convenience function to trigger a PagerDuty event."""
    async with PagerDutyClient() as client:
        return await client.trigger_event(summary, severity, source, dedup_key, custom_details)
