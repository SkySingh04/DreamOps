"""Commands that the agent can execute to provide insights."""

from typing import Any

from src.oncall_agent.services.notion_insights import get_insights_service
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)


class AgentCommands:
    """Commands available to the agent for providing insights."""

    @staticmethod
    async def analyze_recent_chaos() -> dict[str, Any]:
        """Analyze recent chaos engineering results."""
        try:
            service = await get_insights_service()

            # Get very recent incidents (last 2 hours)
            from datetime import datetime, timedelta
            recent_incidents = await service.get_recent_incidents(days=1)

            two_hours_ago = datetime.utcnow() - timedelta(hours=2)
            chaos_incidents = []

            for inc in recent_incidents:
                created_at_str = inc.get("created_at", "")
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if created_at.replace(tzinfo=None) > two_hours_ago:
                        chaos_incidents.append(inc)

            # Generate summary
            summary = {
                "incidents_created": len(chaos_incidents),
                "services_affected": list(set(inc["service_name"] for inc in chaos_incidents)),
                "issue_types": list(set(inc["incident_type"] for inc in chaos_incidents)),
                "incidents": chaos_incidents
            }

            # Create human-readable response
            response = "🔍 **Chaos Engineering Analysis**\n\n"
            response += "I've analyzed the recent chaos engineering session:\n\n"
            response += "📊 **Results:**\n"
            response += f"- Incidents Created: {summary['incidents_created']}\n"
            response += f"- Services Affected: {', '.join(summary['services_affected'])}\n"
            response += f"- Issue Types: {', '.join(summary['issue_types'])}\n\n"

            if chaos_incidents:
                response += "📝 **Documented Incidents:**\n"
                for inc in chaos_incidents[:5]:
                    response += f"- [{inc['title']}]({inc['url']})\n"

                # Add specific insights
                response += "\n💡 **Insights:**\n"
                issue_types = summary['issue_types']
                if 'oom' in issue_types:
                    response += "- Memory issues detected. Consider reviewing resource limits.\n"
                if 'image_pull' in issue_types:
                    response += "- Image pull failures indicate registry access issues.\n"
                if 'crash_loop' in issue_types:
                    response += "- Application crashes need investigation of startup logic.\n"
            else:
                response += "\n⚠️ No incidents were created in the last 2 hours.\n"

            return {
                "success": True,
                "response": response,
                "data": summary
            }

        except Exception as e:
            logger.error(f"Error analyzing chaos: {e}")
            return {
                "success": False,
                "response": f"❌ Error analyzing chaos results: {str(e)}",
                "error": str(e)
            }

    @staticmethod
    async def get_infrastructure_health_report() -> dict[str, Any]:
        """Get a comprehensive infrastructure health report."""
        try:
            service = await get_insights_service()
            report = await service.generate_summary_report()

            return {
                "success": True,
                "response": report,
                "format": "markdown"
            }

        except Exception as e:
            logger.error(f"Error generating health report: {e}")
            return {
                "success": False,
                "response": f"❌ Error generating report: {str(e)}",
                "error": str(e)
            }

    @staticmethod
    async def get_actionable_recommendations() -> dict[str, Any]:
        """Get actionable recommendations based on incident patterns."""
        try:
            service = await get_insights_service()
            analysis = await service.analyze_incidents()

            recommendations = analysis.get("recommendations", [])
            insights = analysis.get("insights", [])

            response = "🎯 **Infrastructure Recommendations**\n\n"
            response += f"Based on {analysis['total_incidents']} incidents in the {analysis['period']}:\n\n"

            if insights:
                response += "📊 **Key Findings:**\n"
                for insight in insights[:3]:
                    response += f"- {insight}\n"
                response += "\n"

            if recommendations:
                response += "💡 **Recommendations:**\n"
                for i, rec in enumerate(recommendations, 1):
                    priority = "🔴" if "Urgent" in rec else "🟡"
                    response += f"{i}. {priority} {rec}\n"
            else:
                response += "✅ No critical issues found. Keep up the good work!\n"

            # Add trend information
            trend = analysis.get("trend", "stable")
            if trend == "increasing":
                response += "\n⚠️ **Warning:** Incident frequency is increasing. Consider scheduling a reliability review."
            elif trend == "decreasing":
                response += "\n✅ **Good News:** Incident frequency is decreasing. Your improvements are working!"

            return {
                "success": True,
                "response": response,
                "data": {
                    "recommendations": recommendations,
                    "insights": insights,
                    "trend": trend
                }
            }

        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return {
                "success": False,
                "response": f"❌ Error getting recommendations: {str(e)}",
                "error": str(e)
            }

    @staticmethod
    async def analyze_service_reliability(service_name: str) -> dict[str, Any]:
        """Analyze reliability of a specific service."""
        try:
            service = await get_insights_service()
            incidents = await service.get_recent_incidents(days=30)

            # Filter incidents for the service
            service_incidents = [
                inc for inc in incidents
                if inc["service_name"].lower() == service_name.lower()
            ]

            if not service_incidents:
                return {
                    "success": True,
                    "response": f"✅ No incidents found for service '{service_name}' in the last 30 days!",
                    "data": {"incident_count": 0}
                }

            # Analyze service-specific patterns
            issue_types = {}
            for inc in service_incidents:
                issue_type = inc["incident_type"]
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

            response = f"📊 **Service Reliability Analysis: {service_name}**\n\n"
            response += f"Incidents in last 30 days: {len(service_incidents)}\n\n"

            response += "**Issue Breakdown:**\n"
            for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
                response += f"- {issue_type.replace('_', ' ').title()}: {count} incidents\n"

            response += "\n**Recent Incidents:**\n"
            for inc in service_incidents[:3]:
                response += f"- [{inc['title']}]({inc['url']})\n"

            # Service-specific recommendations
            response += "\n**Recommendations:**\n"
            if issue_types.get("oom", 0) > 2:
                response += "- 🔴 Multiple OOM incidents - Increase memory limits immediately\n"
            if issue_types.get("crash_loop", 0) > 1:
                response += "- 🟡 Recurring crashes - Review application logs and error handling\n"
            if len(service_incidents) > 5:
                response += "- 🟡 High incident rate - Consider architectural review\n"

            return {
                "success": True,
                "response": response,
                "data": {
                    "incident_count": len(service_incidents),
                    "issue_types": issue_types
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing service: {e}")
            return {
                "success": False,
                "response": f"❌ Error analyzing service: {str(e)}",
                "error": str(e)
            }
