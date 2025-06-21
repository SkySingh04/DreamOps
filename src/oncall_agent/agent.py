"""Main agent logic using AGNO framework for oncall incident response."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

import agno
from anthropic import AsyncAnthropic

from .config import get_config
from .mcp_integrations.base import MCPIntegration


class PagerAlert(BaseModel):
    """Model for incoming pager alerts."""
    alert_id: str
    severity: str
    service_name: str
    description: str
    timestamp: str
    metadata: Dict[str, Any] = {}


class OncallAgent:
    """AI agent for handling oncall incidents using AGNO framework."""
    
    def __init__(self):
        """Initialize the oncall agent with configuration."""
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.mcp_integrations: Dict[str, MCPIntegration] = {}
        
        # Initialize Anthropic client
        self.anthropic_client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
        
        # Initialize AGNO agent
        self.agent = self._create_agent()
        
    def _create_agent(self) -> agno.Agent:
        """Create and configure the AGNO agent."""
        agent = agno.Agent(
            name="oncall-agent",
            version="0.1.0",
            description="AI agent for automated oncall incident response"
        )
        
        # Register tools for the agent
        @agent.tool
        async def analyze_alert(alert: PagerAlert) -> Dict[str, Any]:
            """Analyze a pager alert and determine the appropriate response."""
            self.logger.info(f"Analyzing alert: {alert.alert_id}")
            
            # Placeholder for alert analysis logic
            analysis = {
                "alert_id": alert.alert_id,
                "severity_assessment": alert.severity,
                "affected_service": alert.service_name,
                "recommended_actions": [
                    "Check service health metrics",
                    "Review recent deployments",
                    "Examine error logs"
                ],
                "priority": "high" if alert.severity in ["critical", "high"] else "medium"
            }
            
            return analysis
        
        @agent.tool
        async def fetch_mcp_context(integration_name: str, context_type: str) -> Dict[str, Any]:
            """Fetch context from MCP integrations."""
            if integration_name not in self.mcp_integrations:
                return {"error": f"MCP integration '{integration_name}' not found"}
            
            integration = self.mcp_integrations[integration_name]
            try:
                context = await integration.fetch_context(context_type)
                return {"integration": integration_name, "context": context}
            except Exception as e:
                self.logger.error(f"Error fetching context from {integration_name}: {e}")
                return {"error": str(e)}
        
        @agent.tool
        async def execute_mcp_action(integration_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
            """Execute an action through MCP integrations."""
            if integration_name not in self.mcp_integrations:
                return {"error": f"MCP integration '{integration_name}' not found"}
            
            integration = self.mcp_integrations[integration_name]
            try:
                result = await integration.execute_action(action, params)
                return {"integration": integration_name, "result": result}
            except Exception as e:
                self.logger.error(f"Error executing action on {integration_name}: {e}")
                return {"error": str(e)}
        
        return agent
    
    def register_mcp_integration(self, name: str, integration: MCPIntegration) -> None:
        """Register an MCP integration with the agent."""
        self.logger.info(f"Registering MCP integration: {name}")
        self.mcp_integrations[name] = integration
    
    async def connect_integrations(self) -> None:
        """Connect all registered MCP integrations."""
        for name, integration in self.mcp_integrations.items():
            try:
                await integration.connect()
                self.logger.info(f"Connected to MCP integration: {name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {name}: {e}")
    
    async def handle_pager_alert(self, alert: PagerAlert) -> Dict[str, Any]:
        """Handle an incoming pager alert."""
        self.logger.info(f"Handling pager alert: {alert.alert_id} for service: {alert.service_name}")
        
        try:
            # Create a prompt for Claude to analyze the alert
            prompt = f"""
            Analyze this oncall alert and provide a response plan:
            
            Alert ID: {alert.alert_id}
            Service: {alert.service_name}
            Severity: {alert.severity}
            Description: {alert.description}
            Timestamp: {alert.timestamp}
            Metadata: {alert.metadata}
            
            Please provide:
            1. Initial assessment of the issue
            2. Recommended immediate actions
            3. Data to collect from monitoring systems
            4. Potential root causes
            5. Escalation criteria
            """
            
            # Use Claude for analysis
            response = await self.anthropic_client.messages.create(
                model=self.config.claude_model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the response
            analysis = response.content[0].text if response.content else "No analysis available"
            
            # Create response structure
            result = {
                "alert_id": alert.alert_id,
                "status": "analyzed",
                "analysis": analysis,
                "timestamp": alert.timestamp,
                "available_integrations": list(self.mcp_integrations.keys())
            }
            
            # Log the handling
            self.logger.info(f"Alert {alert.alert_id} analyzed successfully")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error handling alert {alert.alert_id}: {e}")
            return {
                "alert_id": alert.alert_id,
                "status": "error",
                "error": str(e)
            }
    
    async def shutdown(self) -> None:
        """Shutdown the agent and disconnect integrations."""
        self.logger.info("Shutting down oncall agent")
        for name, integration in self.mcp_integrations.items():
            try:
                await integration.disconnect()
                self.logger.info(f"Disconnected from {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")