"""Notion insights service for analyzing incidents and providing recommendations."""

from collections import Counter
from datetime import datetime
from typing import Any

from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration
from src.oncall_agent.services.notion_activity_tracker import notion_tracker
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)


class NotionInsightsService:
    """Service for analyzing Notion incident data and providing insights."""

    def __init__(self):
        self.config = get_config()
        self.logger = logger
        self.notion = None

    async def connect(self):
        """Connect to Notion API."""
        if self.config.notion_token:
            self.notion = NotionDirectIntegration({
                "notion_token": self.config.notion_token,
                "database_id": self.config.notion_database_id,
                "notion_version": self.config.notion_version
            })
            await self.notion.connect()
            self.logger.info("Connected to Notion for insights analysis")
        else:
            raise ValueError("Notion credentials not configured")

    async def disconnect(self):
        """Disconnect from Notion."""
        if self.notion:
            await self.notion.disconnect()

    async def get_recent_incidents(self, days: int = 7) -> list[dict[str, Any]]:
        """Get incidents from the last N days."""
        try:
            # Query the database with date filter
            response = await self.notion.client.post(
                f"/databases/{self.config.notion_database_id}/query",
                json={
                    "filter": {
                        "property": "Date Created",
                        "date": {
                            "past_week": {}
                        }
                    },
                    "sorts": [
                        {
                            "property": "Date Created",
                            "direction": "descending"
                        }
                    ],
                    "page_size": 100
                }
            )

            if response.status_code == 200:
                data = response.json()
                incidents = []

                # Track the database query
                await notion_tracker.log_operation("query_database", {
                    "database_id": self.config.notion_database_id,
                    "filter": "past_week",
                    "results_count": len(data.get("results", [])),
                    "purpose": "incident_analysis"
                })

                for page in data.get("results", []):
                    incident = self._parse_incident_page(page)
                    if incident:
                        incidents.append(incident)

                return incidents
            else:
                self.logger.error(f"Failed to query Notion: {response.status_code}")
                return []

        except Exception as e:
            self.logger.error(f"Error fetching recent incidents: {e}")
            return []

    def _parse_incident_page(self, page: dict[str, Any]) -> dict[str, Any]:
        """Parse a Notion page into incident data."""
        try:
            # Extract title
            title = "Unknown"
            name_prop = page.get("properties", {}).get("Name", {})
            if name_prop.get("title"):
                title_arr = name_prop["title"]
                if title_arr and len(title_arr) > 0:
                    title = title_arr[0].get("text", {}).get("content", "Unknown")

            # Extract service name and type from title
            service_name = "unknown"
            incident_type = "general"

            # Parse title format: "Incident: service-name - alert-id"
            if ":" in title and " - " in title:
                try:
                    # Split "Incident: service-name - alert-id"
                    after_colon = title.split(":", 1)[1].strip()
                    if " - " in after_colon:
                        service_name = after_colon.split(" - ")[0].strip()
                    else:
                        service_name = after_colon
                except:
                    pass

            # Detect incident type from title
            title_lower = title.lower()
            if "oom" in title_lower or "memory" in title_lower:
                incident_type = "oom"
            elif "imagepull" in title_lower or "pull" in title_lower:
                incident_type = "image_pull"
            elif "crashloop" in title_lower or "crash" in title_lower:
                incident_type = "crash_loop"
            elif "deployment" in title_lower:
                incident_type = "deployment_failed"
            elif "service" in title_lower and "down" in title_lower:
                incident_type = "service_down"

            return {
                "id": page.get("id"),
                "title": title,
                "service_name": service_name,
                "incident_type": incident_type,
                "created_at": page.get("created_time"),
                "url": page.get("url"),
                "status": page.get("properties", {}).get("Status", {}).get("status", {}).get("name", "Unknown")
            }

        except Exception as e:
            self.logger.error(f"Error parsing incident page: {e}")
            return None

    async def analyze_incidents(self) -> dict[str, Any]:
        """Analyze recent incidents and provide insights."""
        incidents = await self.get_recent_incidents(days=30)

        if not incidents:
            return {
                "total_incidents": 0,
                "insights": ["No incidents found in the last 30 days"],
                "recommendations": ["Keep up the good work!"]
            }

        # Analyze incident patterns
        service_counts = Counter(inc["service_name"] for inc in incidents)
        type_counts = Counter(inc["incident_type"] for inc in incidents)

        # Calculate metrics
        total_incidents = len(incidents)
        most_problematic_services = service_counts.most_common(3)
        most_common_issues = type_counts.most_common(3)

        # Time-based analysis
        incidents_by_day = self._group_incidents_by_day(incidents)
        trend = self._calculate_trend(incidents_by_day)

        # Generate insights
        insights = []
        recommendations = []

        # Service insights
        if most_problematic_services:
            top_service = most_problematic_services[0]
            insights.append(f"'{top_service[0]}' has the most incidents ({top_service[1]} total)")

            if top_service[1] > 5:
                recommendations.append(f"Consider reviewing the architecture and monitoring for '{top_service[0]}'")

        # Issue type insights
        if most_common_issues:
            top_issue = most_common_issues[0]
            issue_percent = (top_issue[1] / total_incidents) * 100
            insights.append(f"{top_issue[0].replace('_', ' ').title()} accounts for {issue_percent:.1f}% of incidents")

            # Issue-specific recommendations
            if top_issue[0] == "oom":
                recommendations.append("Review memory limits and implement resource monitoring")
                recommendations.append("Consider implementing horizontal pod autoscaling")
            elif top_issue[0] == "image_pull":
                recommendations.append("Verify image repository access and credentials")
                recommendations.append("Consider using a private registry with caching")
            elif top_issue[0] == "crash_loop":
                recommendations.append("Review application logs and health checks")
                recommendations.append("Implement proper error handling and graceful shutdowns")

        # Trend insights
        if trend == "increasing":
            insights.append("⚠️ Incident frequency is increasing")
            recommendations.append("Schedule a reliability review to identify root causes")
        elif trend == "decreasing":
            insights.append("✅ Incident frequency is decreasing")

        # Pattern detection
        patterns = self._detect_patterns(incidents)
        insights.extend(patterns["insights"])
        recommendations.extend(patterns["recommendations"])

        return {
            "total_incidents": total_incidents,
            "period": "last 30 days",
            "services_affected": len(service_counts),
            "most_problematic_services": [
                {"name": name, "count": count}
                for name, count in most_problematic_services
            ],
            "incident_types": [
                {"type": type_name, "count": count}
                for type_name, count in type_counts.items()
            ],
            "insights": insights,
            "recommendations": recommendations,
            "trend": trend,
            "recent_incidents": incidents[:5]  # Last 5 incidents
        }

    def _group_incidents_by_day(self, incidents: list[dict[str, Any]]) -> dict[str, int]:
        """Group incidents by day."""
        by_day = {}
        for incident in incidents:
            created_at = incident.get("created_at", "")
            if created_at:
                day = created_at.split("T")[0]
                by_day[day] = by_day.get(day, 0) + 1
        return by_day

    def _calculate_trend(self, incidents_by_day: dict[str, int]) -> str:
        """Calculate if incidents are increasing or decreasing."""
        if len(incidents_by_day) < 2:
            return "stable"

        # Sort days and split into two halves
        sorted_days = sorted(incidents_by_day.keys())
        mid = len(sorted_days) // 2

        first_half = sum(incidents_by_day[day] for day in sorted_days[:mid])
        second_half = sum(incidents_by_day[day] for day in sorted_days[mid:])

        if second_half > first_half * 1.2:
            return "increasing"
        elif second_half < first_half * 0.8:
            return "decreasing"
        else:
            return "stable"

    def _detect_patterns(self, incidents: list[dict[str, Any]]) -> dict[str, list[str]]:
        """Detect patterns in incidents."""
        insights = []
        recommendations = []

        # Check for recurring issues
        service_type_combo = Counter()
        for inc in incidents:
            combo = f"{inc['service_name']}:{inc['incident_type']}"
            service_type_combo[combo] += 1

        # Find recurring patterns
        for combo, count in service_type_combo.items():
            if count >= 3:
                service, issue_type = combo.split(":")
                insights.append(f"'{service}' has recurring {issue_type.replace('_', ' ')} issues ({count} times)")

                if issue_type == "oom" and count >= 5:
                    recommendations.append(f"Urgent: '{service}' needs memory optimization or limit increase")

        # Time-based patterns
        hour_counts = Counter()
        for inc in incidents:
            created_at = inc.get("created_at", "")
            if created_at and "T" in created_at:
                hour = int(created_at.split("T")[1].split(":")[0])
                hour_counts[hour] += 1

        if hour_counts:
            peak_hour = hour_counts.most_common(1)[0]
            if peak_hour[1] >= 3:
                insights.append(f"Most incidents occur around {peak_hour[0]}:00 UTC")
                recommendations.append("Review deployment schedules and traffic patterns during peak hours")

        return {
            "insights": insights,
            "recommendations": recommendations
        }

    async def generate_summary_report(self) -> str:
        """Generate a markdown summary report."""
        analysis = await self.analyze_incidents()

        report = f"""# 📊 Kubernetes Infrastructure Health Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

## 📈 Overview
- **Total Incidents**: {analysis['total_incidents']} ({analysis['period']})
- **Services Affected**: {analysis['services_affected']}
- **Trend**: {analysis['trend'].upper()}

## 🔍 Key Insights
"""

        for insight in analysis['insights']:
            report += f"- {insight}\n"

        report += "\n## 🏆 Most Problematic Services\n"
        for service in analysis['most_problematic_services']:
            report += f"- **{service['name']}**: {service['count']} incidents\n"

        report += "\n## 📊 Incident Types Distribution\n"
        for inc_type in analysis['incident_types']:
            report += f"- **{inc_type['type'].replace('_', ' ').title()}**: {inc_type['count']} incidents\n"

        report += "\n## 💡 Recommendations\n"
        for i, rec in enumerate(analysis['recommendations'], 1):
            report += f"{i}. {rec}\n"

        report += "\n## 📝 Recent Incidents\n"
        for inc in analysis['recent_incidents'][:5]:
            report += f"- [{inc['title']}]({inc['url']})\n"

        report += "\n---\n*Report generated by DreamOps AI Agent*"

        return report


# Singleton instance
_insights_service = None

async def get_insights_service() -> NotionInsightsService:
    """Get or create the insights service instance."""
    global _insights_service
    if _insights_service is None:
        _insights_service = NotionInsightsService()
        await _insights_service.connect()
    return _insights_service
