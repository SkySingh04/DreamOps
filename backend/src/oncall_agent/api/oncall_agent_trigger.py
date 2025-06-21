"""Bridge between PagerDuty alerts and the oncall agent."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.api.alert_context_parser import ContextExtractor
from src.oncall_agent.api.models import PagerDutyIncidentData
from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger


class OncallAgentTrigger:
    """Manages triggering the oncall agent from external sources."""

    def __init__(self, agent: OncallAgent | None = None):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.agent = agent
        self.context_extractor = ContextExtractor()

        # Thread pool for async execution
        self.executor = ThreadPoolExecutor(max_workers=5)

        # Queue for managing concurrent alerts
        self.alert_queue = asyncio.Queue(maxsize=100)
        self.processing_alerts = {}

        # Prompt templates
        self.prompt_templates = {
            'critical': """CRITICAL INCIDENT - IMMEDIATE ACTION REQUIRED
{context}

Please provide:
1. Immediate mitigation steps (under 5 minutes)
2. Root cause hypothesis
3. Impact assessment
4. Communication template for stakeholders""",

            'high': """HIGH PRIORITY INCIDENT
{context}

Please analyze and provide:
1. Diagnosis steps
2. Remediation actions
3. Monitoring recommendations
4. Prevention measures""",

            'medium': """INCIDENT ANALYSIS NEEDED
{context}

Please provide:
1. Issue analysis
2. Recommended actions
3. Long-term fixes""",

            'low': """LOW PRIORITY ALERT
{context}

Please provide brief analysis and recommendations."""
        }

    async def initialize(self):
        """Initialize the oncall agent if not provided."""
        if not self.agent:
            self.agent = OncallAgent()
            await self.agent.connect_integrations()
            self.logger.info("OncallAgent initialized for trigger")

    async def trigger_oncall_agent(self, pagerduty_incident: PagerDutyIncidentData,
                                  context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Trigger the oncall agent with PagerDuty context.
        
        Args:
            pagerduty_incident: The PagerDuty incident data
            context: Additional context from the parser
            
        Returns:
            Dict containing agent response and metadata
        """
        try:
            # Extract alert and context
            pager_alert, extracted_context = self.context_extractor.extract_from_incident(pagerduty_incident)

            # Merge provided context with extracted context
            if context:
                extracted_context.update(context)

            # Check if already processing this alert
            if pager_alert.alert_id in self.processing_alerts:
                self.logger.warning(f"Alert {pager_alert.alert_id} already being processed")
                return {
                    "status": "duplicate",
                    "message": "Alert already being processed",
                    "alert_id": pager_alert.alert_id
                }

            # Mark as processing
            self.processing_alerts[pager_alert.alert_id] = datetime.now()

            # Add custom prompt based on severity
            if extracted_context.get("suggested_prompt"):
                prompt_template = self.prompt_templates.get(
                    pager_alert.severity.lower(),
                    self.prompt_templates['medium']
                )
                enhanced_prompt = prompt_template.format(context=extracted_context["suggested_prompt"])
                pager_alert.metadata["custom_prompt"] = enhanced_prompt

            # Add extracted context to alert metadata
            pager_alert.metadata["extracted_context"] = extracted_context

            # Trigger the agent
            self.logger.info(f"Triggering oncall agent for alert {pager_alert.alert_id}")

            # Run in background if queue is getting full
            if self.alert_queue.qsize() > 10:
                asyncio.create_task(self._process_alert_async(pager_alert))
                return {
                    "status": "queued",
                    "message": "Alert queued for processing",
                    "alert_id": pager_alert.alert_id,
                    "queue_size": self.alert_queue.qsize()
                }

            # Process immediately
            if not self.agent:
                await self.initialize()
            assert self.agent is not None
            result = await self.agent.handle_pager_alert(pager_alert)

            # Clean up
            del self.processing_alerts[pager_alert.alert_id]

            return {
                "status": "success",
                "alert_id": pager_alert.alert_id,
                "agent_response": result,
                "context": extracted_context,
                "processing_time": (datetime.now() - self.processing_alerts.get(pager_alert.alert_id, datetime.now())).total_seconds()
            }

        except TimeoutError:
            self.logger.error(f"Timeout processing alert {pagerduty_incident.id}")
            return {
                "status": "timeout",
                "message": "Agent processing timed out",
                "alert_id": pagerduty_incident.id
            }
        except Exception as e:
            self.logger.error(f"Error triggering oncall agent: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "alert_id": pagerduty_incident.id
            }
        finally:
            # Ensure cleanup
            if pagerduty_incident.id in self.processing_alerts:
                del self.processing_alerts[pagerduty_incident.id]

    async def _process_alert_async(self, pager_alert: PagerAlert):
        """Process alert asynchronously in the background."""
        try:
            await self.alert_queue.put(pager_alert)
            if not self.agent:
                await self.initialize()
            assert self.agent is not None
            result = await self.agent.handle_pager_alert(pager_alert)
            self.logger.info(f"Background processing complete for alert {pager_alert.alert_id}")
            return result
        except Exception as e:
            self.logger.error(f"Error in background processing: {e}", exc_info=True)

    async def process_batch_alerts(self, incidents: list[PagerDutyIncidentData]) -> dict[str, Any]:
        """Process multiple alerts concurrently."""
        tasks = []
        for incident in incidents:
            task = asyncio.create_task(self.trigger_oncall_agent(incident))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "total": len(incidents),
            "processed": sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success"),
            "failed": sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, dict) and r.get("status") == "error")),
            "results": results
        }

    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue and processing status."""
        return {
            "queue_size": self.alert_queue.qsize(),
            "processing_count": len(self.processing_alerts),
            "processing_alerts": list(self.processing_alerts.keys()),
            "queue_capacity": self.alert_queue.maxsize
        }

    async def shutdown(self):
        """Gracefully shutdown the trigger."""
        self.logger.info("Shutting down OncallAgentTrigger")

        # Wait for queue to empty
        if not self.alert_queue.empty():
            self.logger.info(f"Waiting for {self.alert_queue.qsize()} alerts to process")
            await self.alert_queue.join()

        # Shutdown executor
        self.executor.shutdown(wait=True)
