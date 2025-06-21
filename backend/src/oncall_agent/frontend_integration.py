"""Integration module to send incident data to the frontend dashboard."""

import logging
from datetime import datetime
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

class FrontendIntegration:
    """Handles sending incident data to the frontend dashboard."""

    def __init__(self, frontend_url: str = "http://localhost:3000"):
        self.frontend_url = frontend_url
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def create_incident(self,
                            title: str,
                            description: str,
                            severity: str,
                            source: str,
                            source_id: str = None,
                            metadata: dict[str, Any] = None) -> dict[str, Any]:
        """Create an incident in the frontend dashboard."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            incident_data = {
                "title": title,
                "description": description,
                "severity": severity,
                "source": source,
                "sourceId": source_id,
                "metadata": metadata or {}
            }

            url = f"{self.frontend_url}/api/dashboard/internal/incidents"
            headers = {"x-internal-api-key": "oncall-agent-internal"}

            async with self.session.post(url, json=incident_data, headers=headers) as response:
                if response.status == 201:
                    result = await response.json()
                    logger.info(f"✅ Created incident in dashboard: {result.get('id')}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to create incident: {response.status} - {error_text}")
                    return {}

        except Exception as e:
            logger.error(f"❌ Error creating incident in dashboard: {e}")
            return {}

    async def record_ai_action(self,
                             action: str,
                             description: str,
                             incident_id: int = None,
                             status: str = "completed",
                             metadata: dict[str, Any] = None) -> bool:
        """Record an AI action in the frontend dashboard."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            action_data = {
                "action": action,
                "description": description,
                "incidentId": incident_id,
                "status": status,
                "metadata": metadata or {}
            }

            url = f"{self.frontend_url}/api/dashboard/internal/ai-actions"
            headers = {"x-internal-api-key": "oncall-agent-internal"}

            async with self.session.post(url, json=action_data, headers=headers) as response:
                if response.status == 201:
                    logger.info(f"✅ Recorded AI action: {action}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to record AI action: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error recording AI action: {e}")
            return False

    def extract_k8s_incident_data(self, alert_data: dict[str, Any]) -> dict[str, str]:
        """Extract incident data from Kubernetes alert."""
        # Extract relevant information from the alert
        title = alert_data.get("alert_name", "Kubernetes Alert")
        description = alert_data.get("description", "No description provided")

        # Determine severity based on alert type
        severity_map = {
            "CrashLoopBackOff": "critical",
            "ImagePullBackOff": "high",
            "OOMKilled": "critical",
            "NodeNotReady": "critical",
            "PodNotReady": "high",
            "DeploymentFailed": "high"
        }

        alert_type = alert_data.get("alert_type", "unknown")
        severity = severity_map.get(alert_type, "medium")

        return {
            "title": f"K8s Alert: {title}",
            "description": description,
            "severity": severity,
            "source": "kubernetes",
            "source_id": alert_data.get("resource_id", f"k8s-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        }

# Global instance for easy access
frontend_integration = FrontendIntegration()

async def send_incident_to_dashboard(alert_data: dict[str, Any]) -> dict[str, Any] | None:
    """Convenience function to send incident to dashboard."""
    async with FrontendIntegration() as integration:
        incident_data = integration.extract_k8s_incident_data(alert_data)
        return await integration.create_incident(**incident_data)

async def send_ai_action_to_dashboard(action: str, description: str, incident_id: int = None) -> bool:
    """Convenience function to send AI action to dashboard."""
    async with FrontendIntegration() as integration:
        return await integration.record_ai_action(action, description, incident_id)
