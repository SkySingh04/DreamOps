"""Main agent logic using AGNO framework for oncall incident response."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from anthropic import AsyncAnthropic

from .config import get_config
from .mcp_integrations.base import MCPIntegration
from .mcp_integrations.github_mcp import GitHubMCPIntegration


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
        """Initialize the DreamOps agent with configuration."""
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.mcp_integrations: Dict[str, MCPIntegration] = {}
        
        # Initialize Anthropic client
        self.anthropic_client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
        
        # Auto-register GitHub MCP integration if configured
        if self.config.github_token:
            github_integration = GitHubMCPIntegration({
                "github_token": self.config.github_token,
                "mcp_server_path": self.config.github_mcp_server_path,
                "server_host": self.config.github_mcp_host,
                "server_port": self.config.github_mcp_port
            })
            self.register_mcp_integration("github", github_integration)
    
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
            # Gather context from MCP integrations
            context_data = await self._gather_context_for_alert(alert)
            
            # Create a comprehensive prompt for Claude
            prompt = f"""
            Analyze this oncall alert and provide a response plan:
            
            Alert ID: {alert.alert_id}
            Service: {alert.service_name}
            Severity: {alert.severity}
            Description: {alert.description}
            Timestamp: {alert.timestamp}
            Metadata: {alert.metadata}
            
            Additional Context:
            {self._format_context_data(context_data)}
            
            Please provide:
            1. Initial assessment of the issue
            2. Recommended immediate actions
            3. Data to collect from monitoring systems
            4. Potential root causes
            5. Escalation criteria
            6. Recommended GitHub actions (if applicable)
            """
            
            # Use Claude for analysis
            response = await self.anthropic_client.messages.create(
                model=self.config.claude_model,
                max_tokens=1500,
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
                "available_integrations": list(self.mcp_integrations.keys()),
                "context_data": context_data
            }
            
            # Auto-create GitHub issue if configured and severity is high
            if (alert.severity == "high" and "github" in self.mcp_integrations and 
                "api-gateway" in alert.service_name):
                await self._create_incident_issue(alert, analysis)
            
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
    
    async def _gather_context_for_alert(self, alert: PagerAlert) -> Dict[str, Any]:
        """Gather context data from all available MCP integrations."""
        context_data = {}
        
        for name, integration in self.mcp_integrations.items():
            try:
                if name == "github":
                    # Fetch GitHub context relevant to the service
                    repo_name = self._get_repository_for_service(alert.service_name)
                    if repo_name:
                        context_data[name] = {
                            "recent_commits": await integration.fetch_context(
                                "recent_commits", repository=repo_name, limit=5
                            ),
                            "open_issues": await integration.fetch_context(
                                "open_issues", repository=repo_name, limit=10
                            ),
                            "actions_status": await integration.fetch_context(
                                "actions_status", repository=repo_name
                            )
                        }
                        
                        # Add code analysis for specific error types
                        if "error" in alert.description.lower() or "exception" in alert.description.lower():
                            try:
                                # Search for error handling code
                                context_data[name]["error_handling_code"] = await integration.fetch_context(
                                    "search_code", 
                                    query="try catch exception error",
                                    repository=repo_name,
                                    language="python",
                                    limit=5
                                )
                                
                                # Get main application files
                                context_data[name]["main_code"] = await integration.fetch_context(
                                    "file_contents",
                                    repository=repo_name,
                                    path="src/" if alert.service_name == "api-gateway" else "app/"
                                )
                            except Exception as e:
                                self.logger.warning(f"Failed to fetch code context: {e}")
                                
                        # Add configuration files for deployment issues
                        if "deployment" in alert.description.lower() or "config" in alert.description.lower():
                            try:
                                context_data[name]["config_files"] = await integration.fetch_context(
                                    "search_code",
                                    query="config.yaml docker-compose.yml Dockerfile",
                                    repository=repo_name,
                                    limit=3
                                )
                            except Exception as e:
                                self.logger.warning(f"Failed to fetch config context: {e}")
                else:
                    # For other integrations, fetch general context
                    context_data[name] = await integration.fetch_context("general")
                    
            except Exception as e:
                self.logger.warning(f"Failed to gather context from {name}: {e}")
                context_data[name] = {"error": str(e)}
        
        return context_data
    
    def _get_repository_for_service(self, service_name: str) -> Optional[str]:
        """Map service name to GitHub repository."""
        # This is a simple mapping - in production, you'd have a more sophisticated service catalog
        service_repo_mapping = {
            "api-gateway": "myorg/api-gateway",
            "user-service": "myorg/user-service", 
            "payment-service": "myorg/payment-service",
            "notification-service": "myorg/notification-service"
        }
        return service_repo_mapping.get(service_name)
    
    def _format_context_data(self, context_data: Dict[str, Any]) -> str:
        """Format context data for inclusion in Claude prompt."""
        formatted_parts = []
        
        for integration_name, data in context_data.items():
            if "error" in data:
                formatted_parts.append(f"{integration_name.upper()}: Error - {data['error']}")
            else:
                formatted_parts.append(f"{integration_name.upper()}:")
                if integration_name == "github":
                    if "recent_commits" in data and data["recent_commits"]:
                        formatted_parts.append("  Recent Commits:")
                        for commit in data["recent_commits"].get("commits", [])[:3]:
                            formatted_parts.append(f"    - {commit.get('message', 'No message')}")
                    
                    if "open_issues" in data and data["open_issues"]:
                        formatted_parts.append("  Open Issues:")
                        for issue in data["open_issues"].get("issues", [])[:3]:
                            formatted_parts.append(f"    - {issue.get('title', 'No title')}")
                    
                    if "actions_status" in data and data["actions_status"]:
                        formatted_parts.append("  Latest Workflow Runs:")
                        for run in data["actions_status"].get("workflow_runs", [])[:2]:
                            status = run.get("conclusion", "running")
                            formatted_parts.append(f"    - {run.get('name', 'Unknown')}: {status}")
                    
                    if "error_handling_code" in data and data["error_handling_code"]:
                        formatted_parts.append("  Error Handling Code Found:")
                        for item in data["error_handling_code"].get("items", [])[:2]:
                            formatted_parts.append(f"    - {item.get('name', 'Unknown file')}: {item.get('path', 'Unknown path')}")
                    
                    if "main_code" in data and data["main_code"]:
                        formatted_parts.append("  Main Application Structure:")
                        if isinstance(data["main_code"], list):
                            for item in data["main_code"][:3]:
                                formatted_parts.append(f"    - {item.get('name', 'Unknown')}")
                        else:
                            formatted_parts.append(f"    - Code analysis available")
                    
                    if "config_files" in data and data["config_files"]:
                        formatted_parts.append("  Configuration Files:")
                        for item in data["config_files"].get("items", [])[:2]:
                            formatted_parts.append(f"    - {item.get('name', 'Unknown file')}")
                else:
                    formatted_parts.append(f"  Data: {str(data)[:200]}...")
        
        return "\n".join(formatted_parts) if formatted_parts else "No additional context available"
    
    async def _create_incident_issue(self, alert: PagerAlert, analysis: str) -> None:
        """Create a GitHub issue for high-severity incidents."""
        try:
            github_integration = self.mcp_integrations.get("github")
            if not github_integration:
                return
            
            repo_name = self._get_repository_for_service(alert.service_name)
            if not repo_name:
                self.logger.warning(f"No repository mapping found for service: {alert.service_name}")
                return
            
            # Create issue title and body
            title = f"[INCIDENT] {alert.service_name} - {alert.description[:100]}"
            body = f"""
## Incident Report

**Alert ID:** {alert.alert_id}
**Service:** {alert.service_name}
**Severity:** {alert.severity}
**Timestamp:** {alert.timestamp}

### Description
{alert.description}

### Metadata
```json
{alert.metadata}
```

### AI Analysis
{analysis}

---
                *This issue was automatically created by DreamOps.*
            """
            
            # Create the issue
            result = await github_integration.execute_action("create_issue", {
                "repository": repo_name,
                "title": title,
                "body": body.strip(),
                "labels": ["incident", f"severity-{alert.severity}", "auto-generated"]
            })
            
            if "error" not in result:
                self.logger.info(f"Created GitHub issue for alert {alert.alert_id}: {result.get('html_url', 'Unknown URL')}")
            else:
                self.logger.error(f"Failed to create GitHub issue: {result['error']}")
                
        except Exception as e:
            self.logger.error(f"Error creating incident issue: {e}")

    async def shutdown(self) -> None:
        """Shutdown the agent and disconnect integrations."""
        self.logger.info("Shutting down DreamOps agent")
        for name, integration in self.mcp_integrations.items():
            try:
                await integration.disconnect()
                self.logger.info(f"Disconnected from {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")