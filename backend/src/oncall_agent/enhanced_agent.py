"""Enhanced oncall agent with complete repository access and intelligent analysis."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from .config import get_config
from .mcp_integrations.base import MCPIntegration
from .mcp_integrations.enhanced_github_mcp import EnhancedGitHubMCPIntegration


class EnhancedPagerAlert(BaseModel):
    """Enhanced model for incoming pager alerts with timeline information."""
    alert_id: str
    severity: str
    service_name: str
    description: str
    timestamp: str
    metadata: dict[str, Any] = {}
    incident_start_time: str | None = None  # When the issue actually started
    detection_delay: int | None = None  # Minutes between start and detection


class EnhancedOncallAgent:
    """Enhanced AI agent with complete repository access and intelligent problem detection."""

    def __init__(self):
        """Initialize the enhanced oncall agent."""
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.mcp_integrations: dict[str, MCPIntegration] = {}

        # Initialize Anthropic client
        self.anthropic_client = AsyncAnthropic(api_key=self.config.anthropic_api_key)

        # Auto-register Enhanced GitHub MCP integration if configured
        if self.config.github_token:
            enhanced_github = EnhancedGitHubMCPIntegration({
                "github_token": self.config.github_token,
                "mcp_server_path": self.config.github_mcp_server_path,
                "server_host": self.config.github_mcp_host,
                "server_port": self.config.github_mcp_port,
                "repos_cache_dir": "/tmp/oncall_repos",
                "max_cache_age_hours": 2
            })
            self.register_mcp_integration("enhanced_github", enhanced_github)

    def register_mcp_integration(self, name: str, integration: MCPIntegration) -> None:
        """Register an MCP integration with the agent."""
        self.logger.info(f"Registering enhanced MCP integration: {name}")
        self.mcp_integrations[name] = integration

    async def connect_integrations(self) -> None:
        """Connect all registered MCP integrations."""
        for name, integration in self.mcp_integrations.items():
            try:
                await integration.connect()
                self.logger.info(f"Connected to enhanced integration: {name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {name}: {e}")

    async def handle_enhanced_incident(self, alert: EnhancedPagerAlert) -> dict[str, Any]:
        """Handle incident with complete repository analysis and intelligent detection."""
        self.logger.info(f"Handling enhanced incident analysis: {alert.alert_id}")

        try:
            # Determine incident timeline
            incident_time = await self._determine_incident_time(alert)

            # Get service repository mapping
            repository = self._get_repository_for_service(alert.service_name)
            if not repository:
                return {
                    "alert_id": alert.alert_id,
                    "status": "error",
                    "error": f"No repository mapping found for service: {alert.service_name}"
                }

            # Perform comprehensive analysis
            self.logger.info(f"Starting comprehensive analysis for repository: {repository}")

            enhanced_github = self.mcp_integrations.get("enhanced_github")
            if not enhanced_github:
                return {
                    "alert_id": alert.alert_id,
                    "status": "error",
                    "error": "Enhanced GitHub integration not available"
                }

            # Get complete incident analysis
            full_analysis = await enhanced_github.fetch_context(
                "full_incident_analysis",
                repository=repository,
                incident_time=incident_time,
                alert_description=alert.description
            )

            # Generate intelligent analysis with Claude
            intelligent_analysis = await self._generate_intelligent_analysis(alert, full_analysis)

            # Create comprehensive response
            result = {
                "alert_id": alert.alert_id,
                "service_name": alert.service_name,
                "repository": repository,
                "incident_time": incident_time.isoformat(),
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "status": "comprehensive_analysis_complete",

                # Raw analysis data
                "repository_analysis": full_analysis,

                # AI-generated insights
                "intelligent_insights": intelligent_analysis,

                # Action recommendations
                "immediate_actions": await self._generate_immediate_actions(full_analysis),
                "investigation_steps": await self._generate_investigation_steps(full_analysis),
                "prevention_measures": await self._generate_prevention_measures(full_analysis)
            }

            # Auto-create detailed incident issue if high severity
            if alert.severity in ["critical", "high"]:
                issue_result = await self._create_comprehensive_incident_issue(alert, result)
                result["incident_issue"] = issue_result

            self.logger.info(f"Enhanced incident analysis completed for {alert.alert_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error in enhanced incident handling: {e}", exc_info=True)
            return {
                "alert_id": alert.alert_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }

    async def _determine_incident_time(self, alert: EnhancedPagerAlert) -> datetime:
        """Determine the actual incident start time."""
        if alert.incident_start_time:
            return datetime.fromisoformat(alert.incident_start_time.replace('Z', '+00:00'))

        # Parse alert timestamp
        alert_time = datetime.fromisoformat(alert.timestamp.replace('Z', '+00:00'))

        # If detection delay is provided, calculate start time
        if alert.detection_delay:
            return alert_time - timedelta(minutes=alert.detection_delay)

        # Default: assume incident started 1 hour before alert
        return alert_time - timedelta(hours=1)

    def _get_repository_for_service(self, service_name: str) -> str | None:
        """Map service name to GitHub repository."""
        service_repo_mapping = {
            "api-gateway": "myorg/api-gateway",
            "user-service": "myorg/user-service",
            "payment-service": "myorg/payment-service",
            "notification-service": "myorg/notification-service",
            "auth-service": "myorg/auth-service",
            "order-service": "myorg/order-service",
            "inventory-service": "myorg/inventory-service"
        }
        return service_repo_mapping.get(service_name)

    async def _generate_intelligent_analysis(self, alert: EnhancedPagerAlert, full_analysis: dict[str, Any]) -> dict[str, Any]:
        """Generate intelligent analysis using Claude with complete repository context."""

        # Create comprehensive prompt with all available data
        prompt = f"""
        You are an expert site reliability engineer analyzing a critical production incident.
        
        INCIDENT DETAILS:
        - Alert ID: {alert.alert_id}
        - Service: {alert.service_name} 
        - Severity: {alert.severity}
        - Description: {alert.description}
        - Alert Time: {alert.timestamp}
        - Incident Start: {full_analysis.get('incident_time', 'Unknown')}
        
        COMPLETE REPOSITORY ANALYSIS:
        {self._format_analysis_for_claude(full_analysis)}
        
        Based on this comprehensive analysis of the entire codebase, recent changes, deployment history, 
        and commit timeline, provide:
        
        1. ROOT CAUSE ANALYSIS:
           - Most likely root cause based on evidence
           - Contributing factors
           - Timeline correlation analysis
        
        2. IMPACT ASSESSMENT:
           - Affected components and services
           - User impact estimation
           - Business impact assessment
        
        3. IMMEDIATE RESOLUTION STRATEGY:
           - Step-by-step resolution plan
           - Rollback considerations
           - Risk mitigation steps
        
        4. CODE-LEVEL INSIGHTS:
           - Specific files/functions to investigate
           - Code patterns that may be causing issues
           - Configuration or dependency problems
        
        5. PREVENTION ANALYSIS:
           - How this could have been prevented
           - Monitoring improvements needed
           - Process improvements required
        
        Be specific and actionable. Reference actual file names, commit hashes, and code patterns 
        from the analysis data.
        """

        try:
            response = await self.anthropic_client.messages.create(
                model=self.config.claude_model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            analysis_text = response.content[0].text if response.content else "Analysis failed"

            return {
                "claude_analysis": analysis_text,
                "analysis_confidence": await self._calculate_analysis_confidence(full_analysis),
                "evidence_strength": await self._assess_evidence_strength(full_analysis),
                "recommended_priority": await self._determine_recommended_priority(alert, full_analysis)
            }

        except Exception as e:
            self.logger.error(f"Failed to generate intelligent analysis: {e}")
            return {
                "claude_analysis": f"Analysis generation failed: {e}",
                "analysis_confidence": "low",
                "evidence_strength": "insufficient"
            }

    def _format_analysis_for_claude(self, analysis: dict[str, Any]) -> str:
        """Format the comprehensive analysis for Claude's consumption."""
        formatted_parts = []

        # Repository information
        if "repository_data" in analysis:
            repo_data = analysis["repository_data"]
            formatted_parts.append(f"REPOSITORY: {repo_data.get('repository', 'Unknown')}")
            if "file_structure" in repo_data:
                structure = repo_data["file_structure"]
                formatted_parts.append(f"- Total files: {structure.get('total_files', 0)}")
                formatted_parts.append(f"- Key files: {', '.join(structure.get('key_files', []))}")
                formatted_parts.append(f"- Languages: {dict(list(structure.get('languages', {}).items())[:5])}")

        # Commit timeline
        if "commit_timeline" in analysis:
            timeline = analysis["commit_timeline"]
            timeline_analysis = timeline.get("analysis", {})
            formatted_parts.append("\nCOMMIT TIMELINE:")
            formatted_parts.append(f"- Total commits: {timeline_analysis.get('total_commits', 0)}")
            formatted_parts.append(f"- Commit frequency: {timeline_analysis.get('commit_frequency', 0):.2f}/hour")
            formatted_parts.append(f"- Authors: {', '.join(timeline_analysis.get('authors', []))}")

            if timeline_analysis.get("fix_commits"):
                formatted_parts.append("- Recent fix commits:")
                for commit in timeline_analysis["fix_commits"][:3]:
                    formatted_parts.append(f"  * {commit.get('hash', '')[:8]}: {commit.get('message', '')}")

        # Deployment analysis
        if "deployment_analysis" in analysis:
            deploy = analysis["deployment_analysis"]
            formatted_parts.append("\nDEPLOYMENT CHANGES:")

            if deploy.get("deployment_files"):
                formatted_parts.append("- Deployment files changed:")
                for file_info in deploy["deployment_files"][:3]:
                    formatted_parts.append(f"  * {file_info.get('path', '')}")

            if deploy.get("config_changes"):
                formatted_parts.append("- Configuration files changed:")
                for config in deploy["config_changes"][:3]:
                    formatted_parts.append(f"  * {config.get('path', '')}")

        # Code changes
        if "recent_code_changes" in analysis:
            changes = analysis["recent_code_changes"]
            changes_analysis = changes.get("analysis", {})
            formatted_parts.append("\nRECENT CODE CHANGES:")
            formatted_parts.append(f"- Files changed: {changes_analysis.get('total_files_changed', 0)}")
            formatted_parts.append(f"- Risk assessment: {changes_analysis.get('risk_assessment', 'Unknown')}")

            if changes_analysis.get("critical_files_changed"):
                formatted_parts.append("- Critical files modified:")
                for file in changes_analysis["critical_files_changed"][:5]:
                    formatted_parts.append(f"  * {file}")

        # Error patterns
        if "error_pattern_analysis" in analysis:
            errors = analysis["error_pattern_analysis"]
            if errors.get("error_patterns"):
                formatted_parts.append("\nERROR PATTERNS FOUND:")
                for pattern in errors["error_patterns"][:5]:
                    formatted_parts.append(f"- {pattern.get('file', '')}: {pattern.get('content', '')}")

        # Problem detection
        if "problem_detection" in analysis:
            problems = analysis["problem_detection"]
            if problems.get("high_probability"):
                formatted_parts.append("\nHIGH PROBABILITY ISSUES:")
                for problem in problems["high_probability"]:
                    formatted_parts.append(f"- {problem.get('type', '')}: {problem.get('description', '')}")

        return "\n".join(formatted_parts)

    async def _calculate_analysis_confidence(self, analysis: dict[str, Any]) -> str:
        """Calculate confidence level in the analysis."""
        confidence_score = 0

        # Check data completeness
        if analysis.get("repository_data"):
            confidence_score += 20
        if analysis.get("commit_timeline", {}).get("commits"):
            confidence_score += 20
        if analysis.get("recent_code_changes", {}).get("changed_files"):
            confidence_score += 20
        if analysis.get("deployment_analysis", {}).get("deployment_files"):
            confidence_score += 20
        if analysis.get("problem_detection", {}).get("high_probability"):
            confidence_score += 20

        if confidence_score >= 80:
            return "high"
        elif confidence_score >= 60:
            return "medium"
        else:
            return "low"

    async def _assess_evidence_strength(self, analysis: dict[str, Any]) -> str:
        """Assess the strength of available evidence."""
        evidence_indicators = 0

        # Strong evidence indicators
        if analysis.get("recent_code_changes", {}).get("analysis", {}).get("critical_files_changed"):
            evidence_indicators += 2

        if analysis.get("deployment_analysis", {}).get("deployment_files"):
            evidence_indicators += 2

        if analysis.get("problem_detection", {}).get("high_probability"):
            evidence_indicators += 2

        # Medium evidence indicators
        if analysis.get("commit_timeline", {}).get("analysis", {}).get("fix_commits"):
            evidence_indicators += 1

        if analysis.get("error_pattern_analysis", {}).get("error_patterns"):
            evidence_indicators += 1

        if evidence_indicators >= 4:
            return "strong"
        elif evidence_indicators >= 2:
            return "moderate"
        else:
            return "weak"

    async def _determine_recommended_priority(self, alert: EnhancedPagerAlert, analysis: dict[str, Any]) -> str:
        """Determine recommended priority based on analysis."""
        base_priority = alert.severity

        # Escalate if critical files were changed recently
        if analysis.get("recent_code_changes", {}).get("analysis", {}).get("critical_files_changed"):
            if base_priority == "high":
                return "critical"

        # Escalate if recent deployment changes
        if analysis.get("deployment_analysis", {}).get("deployment_files"):
            if base_priority in ["medium", "high"]:
                return "critical"

        return base_priority

    async def _generate_immediate_actions(self, analysis: dict[str, Any]) -> list[str]:
        """Generate immediate action recommendations."""
        actions = []

        # Based on deployment changes
        if analysis.get("deployment_analysis", {}).get("deployment_files"):
            actions.append("🔄 Consider rolling back recent deployment changes")
            actions.append("📋 Review deployment logs for errors")

        # Based on code changes
        if analysis.get("recent_code_changes", {}).get("analysis", {}).get("critical_files_changed"):
            actions.append("🔍 Review recent commits to critical files")
            actions.append("⚠️ Consider reverting recent code changes")

        # Based on problem detection
        problems = analysis.get("problem_detection", {})
        if problems.get("high_probability"):
            for problem in problems["high_probability"][:3]:
                actions.append(f"🚨 Address: {problem.get('description', '')}")

        # Default actions
        if not actions:
            actions.extend([
                "📊 Check application metrics and logs",
                "🔍 Verify service health endpoints",
                "📈 Monitor resource utilization"
            ])

        return actions

    async def _generate_investigation_steps(self, analysis: dict[str, Any]) -> list[str]:
        """Generate detailed investigation steps."""
        steps = []

        # Timeline-based investigation
        if analysis.get("commit_timeline", {}).get("commits"):
            steps.append("📅 Review commit timeline around incident time")

        # Code-based investigation
        code_analysis = analysis.get("recent_code_changes", {}).get("analysis", {})
        if code_analysis.get("critical_files_changed"):
            steps.append("📁 Examine changes in critical files:")
            for file in code_analysis["critical_files_changed"][:3]:
                steps.append(f"   - {file}")

        # Error pattern investigation
        if analysis.get("error_pattern_analysis", {}).get("error_patterns"):
            steps.append("🔍 Investigate error patterns in code")

        # Dependency investigation
        if analysis.get("dependency_analysis", {}).get("dependency_files"):
            steps.append("📦 Check for dependency issues or version conflicts")

        return steps

    async def _generate_prevention_measures(self, analysis: dict[str, Any]) -> list[str]:
        """Generate prevention measures based on analysis."""
        measures = []

        # Based on analysis findings
        if analysis.get("recent_code_changes", {}).get("analysis", {}).get("risk_assessment") == "HIGH":
            measures.append("🛡️ Implement stricter code review for critical files")
            measures.append("🧪 Add more comprehensive testing before deployment")

        if analysis.get("deployment_analysis", {}).get("deployment_files"):
            measures.append("🚀 Implement blue-green deployment strategy")
            measures.append("📋 Add deployment rollback procedures")

        # General measures
        measures.extend([
            "📊 Enhance monitoring and alerting coverage",
            "🔔 Set up early warning systems for similar issues",
            "📝 Document incident response procedures"
        ])

        return measures

    async def _create_comprehensive_incident_issue(self, alert: EnhancedPagerAlert, analysis_result: dict[str, Any]) -> dict[str, Any]:
        """Create a comprehensive GitHub issue with full analysis."""
        try:
            enhanced_github = self.mcp_integrations.get("enhanced_github")
            if not enhanced_github:
                return {"error": "Enhanced GitHub integration not available"}

            # Create detailed issue content
            title = f"[INCIDENT] {alert.service_name} - {alert.description[:80]}"

            body = f"""
# Incident Report - {alert.alert_id}

## 🚨 Alert Information
- **Service**: {alert.service_name}
- **Severity**: {alert.severity}
- **Alert Time**: {alert.timestamp}
- **Incident Start**: {analysis_result.get('incident_time', 'Unknown')}
- **Description**: {alert.description}

## 🔍 AI Analysis Summary
{analysis_result.get('intelligent_insights', {}).get('claude_analysis', 'Analysis not available')[:1000]}...

## ⚡ Immediate Actions Required
{chr(10).join(f"- {action}" for action in analysis_result.get('immediate_actions', []))}

## 🔬 Investigation Steps
{chr(10).join(f"- {step}" for step in analysis_result.get('investigation_steps', []))}

## 🛡️ Prevention Measures
{chr(10).join(f"- {measure}" for measure in analysis_result.get('prevention_measures', []))}

## 📊 Analysis Confidence
- **Confidence Level**: {analysis_result.get('intelligent_insights', {}).get('analysis_confidence', 'unknown')}
- **Evidence Strength**: {analysis_result.get('intelligent_insights', {}).get('evidence_strength', 'unknown')}

## 🔗 Repository Analysis
- **Repository**: {analysis_result.get('repository', 'Unknown')}
- **Analysis Timestamp**: {analysis_result.get('analysis_timestamp', 'Unknown')}

---
*This comprehensive incident report was automatically generated by the Enhanced Oncall Agent with complete repository analysis.*
            """

            # Create the issue (implementation would depend on the enhanced integration)
            return {
                "title": title,
                "body": body,
                "status": "created",
                "labels": ["incident", f"severity-{alert.severity}", "auto-generated", "enhanced-analysis"]
            }

        except Exception as e:
            self.logger.error(f"Failed to create comprehensive incident issue: {e}")
            return {"error": str(e)}

    async def shutdown(self) -> None:
        """Shutdown the enhanced agent."""
        self.logger.info("Shutting down enhanced oncall agent")

        for name, integration in self.mcp_integrations.items():
            try:
                await integration.disconnect()
                self.logger.info(f"Disconnected from enhanced integration: {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")

        self.logger.info("Enhanced oncall agent shutdown complete")
