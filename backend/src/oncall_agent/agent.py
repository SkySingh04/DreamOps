"""Main agent logic using AGNO framework for oncall incident response."""

import logging
import re
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from .config import get_config
from .frontend_integration import (
    send_ai_action_to_dashboard,
    send_incident_to_dashboard,
)
from .mcp_integrations.base import MCPIntegration
from .mcp_integrations.github_mcp import GitHubMCPIntegration
from .mcp_integrations.grafana_mcp import GrafanaMCPIntegration
from .mcp_integrations.kubernetes import KubernetesMCPIntegration
from .mcp_integrations.notion import NotionMCPIntegration


class PagerAlert(BaseModel):
    """Model for incoming pager alerts."""
    alert_id: str
    severity: str
    service_name: str
    description: str
    timestamp: str
    metadata: dict[str, Any] = {}


class OncallAgent:
    """AI agent for handling oncall incidents using AGNO framework."""

    def __init__(self):
        """Initialize the oncall agent with configuration."""
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.mcp_integrations: dict[str, MCPIntegration] = {}

        # Initialize Anthropic client
        self.anthropic_client = AsyncAnthropic(api_key=self.config.anthropic_api_key)

        # Define Kubernetes alert patterns
        self.k8s_alert_patterns = {
            "pod_crash": re.compile(r"(Pod|pod).*(?:CrashLoopBackOff|crash|restarting)", re.IGNORECASE),
            "image_pull": re.compile(r"(ImagePullBackOff|ErrImagePull|Failed to pull image)", re.IGNORECASE),
            "high_memory": re.compile(r"(memory|Memory).*(?:high|above threshold|exceeded)", re.IGNORECASE),
            "high_cpu": re.compile(r"(cpu|CPU).*(?:high|above threshold|exceeded)", re.IGNORECASE),
            "service_down": re.compile(r"(Service|service).*(?:down|unavailable|not responding)", re.IGNORECASE),
            "deployment_failed": re.compile(r"(Deployment|deployment).*(?:failed|failing|error)", re.IGNORECASE),
            "node_issue": re.compile(r"(Node|node).*(?:NotReady|unreachable|down)", re.IGNORECASE),
        }

        # Initialize Kubernetes integration if enabled
        if self.config.k8s_enabled:
            self.k8s_integration = KubernetesMCPIntegration()
            self.register_mcp_integration("kubernetes", self.k8s_integration)

        # Initialize Notion integration if configured
        if self.config.notion_token:
            self.notion_integration = NotionMCPIntegration({
                "notion_token": self.config.notion_token,
                "database_id": self.config.notion_database_id,
                "notion_version": self.config.notion_version
            })
            self.register_mcp_integration("notion", self.notion_integration)

        # Initialize Grafana integration if configured
        if self.config.grafana_url and (self.config.grafana_api_key or (self.config.grafana_username and self.config.grafana_password)):
            self.grafana_integration = GrafanaMCPIntegration({
                "grafana_url": self.config.grafana_url,
                "grafana_api_key": self.config.grafana_api_key,
                "grafana_username": self.config.grafana_username,
                "grafana_password": self.config.grafana_password,
                "mcp_server_path": self.config.grafana_mcp_server_path,
                "server_host": self.config.grafana_mcp_host,
                "server_port": self.config.grafana_mcp_port
            })
            self.register_mcp_integration("grafana", self.grafana_integration)

        # Initialize GitHub integration if configured
        if self.config.github_token:
            self.github_integration = GitHubMCPIntegration({
                "github_token": self.config.github_token,
                "mcp_server_path": self.config.github_mcp_server_path,
                "server_host": self.config.github_mcp_host,
                "server_port": self.config.github_mcp_port
            })
            self.register_mcp_integration("github", self.github_integration)

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

    async def handle_pager_alert(self, alert: PagerAlert) -> dict[str, Any]:
        """Handle an incoming pager alert."""
        self.logger.info(f"Handling pager alert: {alert.alert_id} for service: {alert.service_name}")

        import time
        start_time = time.time()

        # Import here to avoid circular dependency
        try:
            from .api.log_streaming import log_stream_manager
            has_log_streaming = True
        except ImportError:
            has_log_streaming = False

        self.logger.info("=" * 80)
        self.logger.info("🚨 ONCALL AGENT TRIGGERED 🚨")
        self.logger.info("=" * 80)
        self.logger.info(f"Alert ID: {alert.alert_id}")
        self.logger.info(f"Service: {alert.service_name}")
        self.logger.info(f"Severity: {alert.severity}")
        self.logger.info(f"Description: {alert.description[:200]}...")

        try:
            # STEP 0: Send incident to frontend dashboard
            self.logger.info("📊 Sending incident to dashboard...")
            try:
                alert_data = {
                    "alert_name": alert.service_name,
                    "description": alert.description,
                    "alert_type": self._detect_k8s_alert_type(alert.description) or "general",
                    "resource_id": alert.alert_id,
                    "severity": alert.severity,
                    "metadata": alert.metadata
                }
                dashboard_incident = await send_incident_to_dashboard(alert_data)
                incident_id = dashboard_incident.get("id") if dashboard_incident else None
                self.logger.info(f"✅ Incident sent to dashboard with ID: {incident_id}")
            except Exception as e:
                self.logger.error(f"❌ Failed to send incident to dashboard: {e}")
                incident_id = None

            # STEP 1: Gather context from ALL available MCP integrations
            self.logger.info("🔍 Gathering context from MCP integrations...")

            # Emit structured log if available
            if has_log_streaming:
                await log_stream_manager.log_info(
                    "🔍 Gathering context from MCP integrations",
                    incident_id=alert.alert_id,
                    stage="gathering_context",
                    progress=0.3
                )
            all_context = {}

            # Send context gathering action to dashboard
            try:
                await send_ai_action_to_dashboard(
                    action="context_gathering_started",
                    description=f"Started gathering context from {len(self.mcp_integrations)} MCP integrations",
                    incident_id=incident_id
                )
            except Exception as e:
                self.logger.error(f"❌ Failed to send context gathering action to dashboard: {e}")

            # Detect if this is a Kubernetes-related alert
            k8s_alert_type = self._detect_k8s_alert_type(alert.description)
            k8s_context = {}

            # Gather GitHub context if available
            github_context = {}
            if "github" in self.mcp_integrations:
                github_context = await self._gather_github_context(alert)

            # Gather Kubernetes context if available
            if "kubernetes" in self.mcp_integrations:
                self.logger.info("📊 Fetching Kubernetes context...")
                if has_log_streaming:
                    await log_stream_manager.log_info(
                        "🔍 Gathering context from Kubernetes integration",
                        incident_id=alert.alert_id,
                        integration="kubernetes",
                        stage="gathering_context",
                        progress=0.35
                    )
                try:
                    if k8s_alert_type:
                        k8s_context = await self._gather_k8s_context(alert, k8s_alert_type)
                        all_context["kubernetes"] = k8s_context
                    else:
                        # Even for non-K8s specific alerts, get general cluster status
                        k8s = self.mcp_integrations["kubernetes"]
                        namespace = alert.metadata.get("namespace", "default")
                        pods = await k8s.list_pods(namespace)
                        all_context["kubernetes"] = {
                            "cluster_status": "connected",
                            "namespace": namespace,
                            "pod_count": len(pods.get("pods", [])),
                            "unhealthy_pods": [p for p in pods.get("pods", [])
                                             if p.get("status") not in ["Running", "Completed"]]
                        }
                except Exception as e:
                    self.logger.error(f"Error fetching Kubernetes context: {e}")
                    all_context["kubernetes"] = {"error": str(e)}

            # Gather Grafana context if available
            if "grafana" in self.mcp_integrations:
                self.logger.info("📈 Fetching Grafana metrics...")
                if has_log_streaming:
                    await log_stream_manager.log_info(
                        "🔍 Gathering context from Grafana integration",
                        incident_id=alert.alert_id,
                        integration="grafana",
                        stage="gathering_context",
                        progress=0.4
                    )
                try:
                    grafana = self.mcp_integrations["grafana"]
                    # Try to find relevant dashboards based on service name
                    dashboards = await grafana.fetch_context({"action": "search_dashboards", "query": alert.service_name})
                    all_context["grafana"] = {
                        "dashboards": dashboards,
                        "service": alert.service_name
                    }
                except Exception as e:
                    self.logger.error(f"Error fetching Grafana context: {e}")
                    all_context["grafana"] = {"error": str(e)}

            # Gather Notion context if available (for runbooks, etc.)
            if "notion" in self.mcp_integrations:
                self.logger.info("📚 Fetching Notion documentation...")
                try:
                    notion = self.mcp_integrations["notion"]
                    # Search for relevant runbooks or documentation
                    docs = await notion.fetch_context({
                        "action": "search",
                        "query": f"{alert.service_name} {alert.description[:50]}"
                    })
                    all_context["notion"] = docs
                except Exception as e:
                    self.logger.error(f"Error fetching Notion context: {e}")
                    all_context["notion"] = {"error": str(e)}

            # STEP 2: Create a comprehensive prompt for Claude
            prompt = f"""
            You are an expert SRE/DevOps engineer helping to resolve an oncall incident. 
            Analyze this alert and the context from various monitoring tools to provide actionable recommendations.
            
            🚨 ALERT DETAILS:
            - Alert ID: {alert.alert_id}
            - Service: {alert.service_name}
            - Severity: {alert.severity}
            - Description: {alert.description}
            - Timestamp: {alert.timestamp}
            - Metadata: {alert.metadata}
            
            {f"Kubernetes Alert Type: {k8s_alert_type}" if k8s_alert_type else ""}
            {f"Kubernetes Context: {k8s_context}" if k8s_context else ""}
            {f"GitHub Context: {github_context}" if github_context else ""}
            📊 CONTEXT FROM MONITORING TOOLS:
            {self._format_context_for_prompt(all_context)}
            
            Based on the alert and the context gathered from our monitoring tools, please provide:
            
            1. 🎯 IMMEDIATE ACTIONS (What to do RIGHT NOW - be specific with commands)
            2. 🔍 ROOT CAUSE ANALYSIS (What likely caused this based on the context)
            3. 💥 IMPACT ASSESSMENT (Who/what is affected and how severely)
            4. 🛠️ REMEDIATION STEPS (Step-by-step guide to fix the issue)
            5. 📊 MONITORING (What metrics/logs to watch during resolution)
            6. 🚀 AUTOMATION OPPORTUNITIES (Can this be auto-remediated? How?)
            7. 📝 FOLLOW-UP ACTIONS (What to do after the incident is resolved)
            
            Be specific and actionable. Include exact commands, dashboard links, and clear steps.
            If you see patterns in the monitoring data that suggest a specific issue, highlight them.
            
            {"For this Kubernetes issue, also suggest specific kubectl commands or automated fixes." if k8s_alert_type else ""}
            """

            # STEP 3: Call Claude for analysis
            self.logger.info("🤖 Calling Claude for comprehensive analysis...")
            if has_log_streaming:
                await log_stream_manager.log_info(
                    "🤖 Starting Claude analysis...",
                    incident_id=alert.alert_id,
                    stage="claude_analysis",
                    progress=0.5
                )
            response = await self.anthropic_client.messages.create(
                model=self.config.claude_model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract the response
            analysis = response.content[0].text if response.content else "No analysis available"

            # Create response structure
            if has_log_streaming:
                await log_stream_manager.log_info(
                    "📊 Claude is analyzing the incident context",
                    incident_id=alert.alert_id,
                    stage="claude_analysis",
                    progress=0.7
                )

            # Parse the analysis into structured sections
            parsed_analysis = self._parse_claude_analysis(analysis)

            # Stream the complete analysis to the frontend
            if has_log_streaming:
                await log_stream_manager.log_success(
                    "✅ AI ANALYSIS COMPLETE",
                    incident_id=alert.alert_id,
                    stage="complete",
                    progress=1.0,
                    metadata={
                        "analysis": analysis,  # Full markdown analysis
                        "parsed_analysis": parsed_analysis,
                        "confidence_score": parsed_analysis.get("confidence_score", 0.85),
                        "risk_level": parsed_analysis.get("risk_level", "medium"),
                        "response_time": f"{time.time() - start_time:.2f}s"
                    }
                )

            # STEP 4: Send AI analysis action to dashboard
            try:
                await send_ai_action_to_dashboard(
                    action="analysis_complete",
                    description=f"AI analysis completed for {alert.service_name} incident",
                    incident_id=incident_id
                )
                self.logger.info("✅ AI analysis action sent to dashboard")
            except Exception as e:
                self.logger.error(f"❌ Failed to send AI action to dashboard: {e}")

            # STEP 5: Log the analysis to console for visibility
            self.logger.info("\n" + "="*80)
            self.logger.info("🤖 CLAUDE'S ANALYSIS:")
            self.logger.info("="*80)
            for line in analysis.split('\n'):
                if line.strip():
                    self.logger.info(line)
            self.logger.info("="*80 + "\n")

            # STEP 6: Create comprehensive response
            result = {
                "alert_id": alert.alert_id,
                "status": "analyzed",
                "analysis": analysis,
                "parsed_analysis": parsed_analysis,
                "timestamp": alert.timestamp,
                "severity": alert.severity,
                "service": alert.service_name,
                "context_gathered": {
                    integration: bool(context) and "error" not in context
                    for integration, context in all_context.items()
                },
                "full_context": all_context,
                "available_integrations": list(self.mcp_integrations.keys()),
                "k8s_alert_type": k8s_alert_type,
                "k8s_context": k8s_context,
                "github_context": github_context
            }

            # If it's a Kubernetes alert and we have confidence, suggest automated actions
            if k8s_alert_type and k8s_context.get("automated_actions"):
                result["suggested_actions"] = k8s_context["automated_actions"]

            # Add automated actions if available
            if k8s_alert_type and all_context.get("kubernetes", {}).get("automated_actions"):
                result["automated_actions"] = all_context["kubernetes"]["automated_actions"]
                self.logger.info("🤖 Automated actions available:")
                for action in result["automated_actions"]:
                    self.logger.info(f"  - {action['action']}: {action['reason']} (confidence: {action['confidence']})")

                    # Send each automated action suggestion to dashboard
                    try:
                        await send_ai_action_to_dashboard(
                            action=f"automated_suggestion_{action['action']}",
                            description=f"Suggested automated action: {action['action']} - {action['reason']} (confidence: {action['confidence']})",
                            incident_id=incident_id
                        )
                    except Exception as e:
                        self.logger.error(f"❌ Failed to send automated action to dashboard: {e}")

            # Log summary
            self.logger.info(f"✅ Alert {alert.alert_id} analyzed successfully")
            self.logger.info(f"📊 Context gathered from: {', '.join(k for k, v in all_context.items() if v and 'error' not in v)}")

            return result

        except Exception as e:
            self.logger.error(f"Error handling alert {alert.alert_id}: {e}")
            return {
                "alert_id": alert.alert_id,
                "status": "error",
                "error": str(e)
            }

    def _format_context_for_prompt(self, context: dict[str, Any]) -> str:
        """Format the context from various integrations for the Claude prompt."""
        formatted = []

        for integration, data in context.items():
            if not data or "error" in data:
                continue

            formatted.append(f"\n📌 {integration.upper()} CONTEXT:")

            if integration == "kubernetes":
                if "alert_type" in data:
                    formatted.append(f"  - Alert Type: {data.get('alert_type')}")
                if "pod_logs" in data:
                    formatted.append(f"  - Recent Pod Logs: {data.get('pod_logs', '')[:500]}...")
                if "pod_events" in data:
                    formatted.append(f"  - Pod Events: {data.get('pod_events', '')[:300]}...")
                if "problematic_pods" in data:
                    formatted.append(f"  - Problematic Pods: {len(data.get('problematic_pods', []))}")
                if "unhealthy_pods" in data:
                    formatted.append(f"  - Unhealthy Pods: {data.get('unhealthy_pods', [])}")
                if "deployment_status" in data:
                    formatted.append(f"  - Deployment Status: {data.get('deployment_status', {})}")

            elif integration == "grafana":
                if "dashboards" in data:
                    formatted.append(f"  - Related Dashboards: {data.get('dashboards', [])}")

            elif integration == "notion":
                formatted.append(f"  - Documentation/Runbooks: {data}")

        return "\n".join(formatted) if formatted else "No additional context available from integrations."

    def _detect_k8s_alert_type(self, description: str) -> str | None:
        """Detect if an alert is Kubernetes-related and return the type."""
        for alert_type, pattern in self.k8s_alert_patterns.items():
            if pattern.search(description):
                return alert_type
        return None

    async def _gather_k8s_context(self, alert: PagerAlert, alert_type: str) -> dict[str, Any]:
        """Gather Kubernetes-specific context based on alert type."""
        k8s = self.mcp_integrations.get("kubernetes")
        if not k8s:
            return {}

        context = {"alert_type": alert_type}
        metadata = alert.metadata
        namespace = metadata.get("namespace", "default")

        try:
            if alert_type == "pod_crash":
                pod_name = metadata.get("pod_name")
                if pod_name:
                    # Get pod logs
                    logs = await k8s.get_pod_logs(pod_name, namespace, tail_lines=100)
                    context["pod_logs"] = logs

                    # Get pod events
                    events = await k8s.get_pod_events(pod_name, namespace)
                    context["pod_events"] = events

                    # Get pod description
                    description = await k8s.describe_pod(pod_name, namespace)
                    context["pod_description"] = description
                    logs_result = await k8s.get_pod_logs(pod_name, namespace, tail_lines=100)
                    if logs_result.get("success"):
                        context["pod_logs"] = logs_result.get("logs", "")

                    # Get pod events
                    events_result = await k8s.get_pod_events(pod_name, namespace)
                    if events_result.get("success"):
                        context["pod_events"] = events_result.get("events", [])

                    # Get pod description
                    desc_result = await k8s.describe_pod(pod_name, namespace)
                    if desc_result.get("success"):
                        context["pod_description"] = desc_result.get("description", "")

                    # Suggest automated actions
                    context["automated_actions"] = [
                        {
                            "action": "restart_pod",
                            "confidence": 0.7,
                            "params": {"pod_name": pod_name, "namespace": namespace},
                            "reason": "Pod is in CrashLoopBackOff, restart may resolve transient issues"
                        }
                    ]
                else:
                    # List all problematic pods
                    pods = await k8s.list_pods(namespace)
                    context["problematic_pods"] = [
                        p for p in pods.get("pods", [])
                        if p.get("status") in ["CrashLoopBackOff", "Error"]
                    ]

            elif alert_type == "image_pull":
                pod_name = metadata.get("pod_name")
                if pod_name:
                    events = await k8s.get_pod_events(pod_name, namespace)
                    context["pod_events"] = events
                    context["recommendation"] = "Check image name, registry credentials, and network connectivity"

            elif alert_type in ["high_memory", "high_cpu"]:
                # Get resource usage
                deployment_name = metadata.get("deployment_name")
                if deployment_name:
                    deployment_status = await k8s.get_deployment_status(deployment_name, namespace)
                    context["deployment_status"] = deployment_status

                    # Suggest scaling
                    current_replicas = deployment_status.get("deployment", {}).get("replicas", {}).get("desired", 1)
                    context["automated_actions"] = [
                        {
                            "action": "scale_deployment",
                            "confidence": 0.6,
                            "params": {
                                "deployment_name": deployment_name,
                                "namespace": namespace,
                                "replicas": current_replicas + 1
                            },
                            "reason": f"High {alert_type.split('_')[1]} usage, scaling up may help"
                        }
                    ]

            elif alert_type == "service_down":
                service_name = metadata.get("service_name", alert.service_name)
                service_status = await k8s.get_service_status(service_name, namespace)
                context["service_status"] = service_status

                # Check if pods are running
                if service_status.get("service", {}).get("endpoint_count", 0) == 0:
                    context["issue"] = "No endpoints available for service"
                    # Get pods matching service selector
                    selector = service_status.get("service", {}).get("selector", {})
                    if selector:
                        pods = await k8s.list_pods(namespace)
                        matching_pods = [
                            p for p in pods.get("pods", [])
                            if all(p.get("labels", {}).get(k) == v for k, v in selector.items())
                        ]
                        context["matching_pods"] = matching_pods

            elif alert_type == "deployment_failed":
                deployment_name = metadata.get("deployment_name")
                if deployment_name:
                    deployment_status = await k8s.get_deployment_status(deployment_name, namespace)
                    context["deployment_status"] = deployment_status

                    # Check if rollback is needed
                    if not deployment_status.get("deployment", {}).get("healthy", True):
                        context["automated_actions"] = [
                            {
                                "action": "rollback_deployment",
                                "confidence": 0.8,
                                "params": {
                                    "deployment_name": deployment_name,
                                    "namespace": namespace
                                },
                                "reason": "Deployment is unhealthy, rolling back to previous version"
                            }
                        ]

        except Exception as e:
            self.logger.error(f"Error gathering Kubernetes context: {e}")
            context["error"] = str(e)

        return context

    async def _gather_github_context(self, alert: PagerAlert) -> dict[str, Any]:
        """Gather GitHub-specific context for the alert."""
        github = self.mcp_integrations.get("github")
        if not github:
            return {}

        context = {}

        try:
            # Get repository for the service
            github_integration = github
            if hasattr(github_integration, 'get_repository_for_service'):
                repository = github_integration.get_repository_for_service(alert.service_name)
            else:
                # Fallback to metadata or service name
                repository = alert.metadata.get("repository", f"myorg/{alert.service_name}")

            if repository:
                self.logger.info(f"Gathering GitHub context for repository: {repository}")

                # Fetch recent commits
                commits_data = await github.fetch_context("recent_commits", repository=repository, since_hours=24)
                context["recent_commits"] = commits_data

                # Fetch open issues with incident label
                issues_data = await github.fetch_context("open_issues", repository=repository, labels=["incident", "bug"])
                context["open_issues"] = issues_data

                # Fetch GitHub Actions status
                actions_data = await github.fetch_context("github_actions_status", repository=repository)
                context["actions_status"] = actions_data

                # Fetch recent pull requests
                prs_data = await github.fetch_context("pull_requests", repository=repository, state="merged")
                context["recent_pull_requests"] = prs_data

                # Add repository info to context
                context["repository"] = repository

                # If high severity, prepare to create an issue
                if alert.severity in ["critical", "high"]:
                    context["will_create_issue"] = True

        except Exception as e:
            self.logger.error(f"Error gathering GitHub context: {e}")
            context["error"] = str(e)

        return context

    async def shutdown(self) -> None:
        """Shutdown the agent and disconnect integrations."""
        self.logger.info("Shutting down oncall agent")
        for name, integration in self.mcp_integrations.items():
            try:
                await integration.disconnect()
                self.logger.info(f"Disconnected from {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")

    def _parse_claude_analysis(self, analysis: str) -> dict[str, Any]:
        """Parse Claude's analysis into structured sections."""
        import re

        sections = {
            "immediate_actions": [],
            "root_cause": [],
            "impact": [],
            "remediation": [],
            "monitoring": [],
            "automation": [],
            "follow_up": [],
            "confidence_score": 0.85,
            "risk_level": "medium",
            "commands": []
        }

        # Section patterns
        section_patterns = {
            "immediate_actions": r"(?:IMMEDIATE ACTIONS?|🎯.*IMMEDIATE.*?)[\s:]*\n(.*?)(?=\n\d+\.|🔍|💥|🛠️|📊|🚀|📝|$)",
            "root_cause": r"(?:ROOT CAUSE.*?|🔍.*ROOT CAUSE.*?)[\s:]*\n(.*?)(?=\n\d+\.|🎯|💥|🛠️|📊|🚀|📝|$)",
            "impact": r"(?:IMPACT.*?|💥.*IMPACT.*?)[\s:]*\n(.*?)(?=\n\d+\.|🎯|🔍|🛠️|📊|🚀|📝|$)",
            "remediation": r"(?:REMEDIATION.*?|🛠️.*REMEDIATION.*?)[\s:]*\n(.*?)(?=\n\d+\.|🎯|🔍|💥|📊|🚀|📝|$)",
            "monitoring": r"(?:MONITORING.*?|📊.*MONITORING.*?)[\s:]*\n(.*?)(?=\n\d+\.|🎯|🔍|💥|🛠️|🚀|📝|$)",
            "automation": r"(?:AUTOMATION.*?|🚀.*AUTOMATION.*?)[\s:]*\n(.*?)(?=\n\d+\.|🎯|🔍|💥|🛠️|📊|📝|$)",
            "follow_up": r"(?:FOLLOW-?UP.*?|📝.*FOLLOW.*?)[\s:]*\n(.*?)(?=\n\d+\.|🎯|🔍|💥|🛠️|📊|🚀|$)"
        }

        # Extract sections
        for section, pattern in section_patterns.items():
            match = re.search(pattern, analysis, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # Split by newlines and clean up
                items = [line.strip() for line in content.split('\n') if line.strip()]
                # Remove numbering and clean up
                cleaned_items = []
                for item in items:
                    # Remove leading numbers, bullets, etc.
                    cleaned = re.sub(r'^[\d\-\*\•]+\.\s*', '', item)
                    if cleaned and not cleaned.startswith(('🎯', '🔍', '💥', '🛠️', '📊', '🚀', '📝')):
                        cleaned_items.append(cleaned)
                sections[section] = cleaned_items

        # Extract all commands (bash/kubectl commands)
        command_pattern = r'(?:```(?:bash|sh)?\n(.*?)```|`([^`]+)`)'
        commands = []
        for match in re.finditer(command_pattern, analysis, re.DOTALL):
            if match.group(1):  # Multi-line code block
                cmds = [cmd.strip() for cmd in match.group(1).split('\n') if cmd.strip()]
                commands.extend(cmds)
            elif match.group(2):  # Inline code
                commands.append(match.group(2).strip())

        sections["commands"] = commands

        # Extract confidence score if mentioned
        confidence_match = re.search(r'(?:confidence|confident)[\s:]*(\d+)%', analysis, re.IGNORECASE)
        if confidence_match:
            sections["confidence_score"] = int(confidence_match.group(1)) / 100.0

        # Extract risk level if mentioned
        risk_match = re.search(r'(?:risk|severity)[\s:]*(?:is\s+)?(\w+)', analysis, re.IGNORECASE)
        if risk_match:
            risk = risk_match.group(1).lower()
            if risk in ["low", "medium", "high", "critical"]:
                sections["risk_level"] = risk

        return sections
