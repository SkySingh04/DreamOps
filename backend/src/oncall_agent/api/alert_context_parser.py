"""Parse and transform PagerDuty incident data into rich context for the oncall agent."""

import re
from datetime import datetime
from typing import Any

from src.oncall_agent.agent import PagerAlert
from src.oncall_agent.api.models import PagerDutyIncidentData
from src.oncall_agent.utils import get_logger


class ContextExtractor:
    """Extract and parse context from PagerDuty incidents."""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Patterns for extracting technical details
        self.patterns = {
            'error_code': re.compile(r'(?:error|code|status)[:=\s]*(\d{3,4}|\w+Error)', re.I),
            'ip_address': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            'memory_usage': re.compile(r'memory[:=\s]*(\d+(?:\.\d+)?)\s*(%|MB|GB)', re.I),
            'cpu_usage': re.compile(r'cpu[:=\s]*(\d+(?:\.\d+)?)\s*%', re.I),
            'latency': re.compile(r'latency[:=\s]*(\d+(?:\.\d+)?)\s*(ms|s)', re.I),
            'query_time': re.compile(r'query\s+time[:=\s]*(\d+(?:\.\d+)?)\s*(ms|s)', re.I),
            'connection_count': re.compile(r'connections?[:=\s]*(\d+)', re.I),
            'pod_name': re.compile(r'pod/(\S+)|pod[:=\s]*(\S+)', re.I),
            'namespace': re.compile(r'namespace[:=\s]*(\S+)', re.I),
            'deployment': re.compile(r'deployment/(\S+)|deployment[:=\s]*(\S+)', re.I),
        }

        # Alert type classifiers
        self.alert_classifiers = {
            'database': ['database', 'mysql', 'postgres', 'mongodb', 'redis', 'query', 'connection pool'],
            'server': ['server', 'cpu', 'memory', 'disk', 'load average', 'process', 'oom'],
            'security': ['security', 'auth', 'unauthorized', 'attack', 'vulnerability', 'breach'],
            'network': ['network', 'latency', 'packet loss', 'connectivity', 'timeout', 'dns'],
            'kubernetes': ['pod', 'deployment', 'service', 'namespace', 'container', 'k8s'],
        }

    def extract_from_incident(self, incident: PagerDutyIncidentData) -> tuple[PagerAlert, dict[str, Any]]:
        """
        Extract context from PagerDuty incident and convert to PagerAlert.
        
        Returns:
            Tuple of (PagerAlert, extracted_context)
        """
        # Determine alert type
        alert_type = self._classify_alert(incident)

        # Extract technical details
        technical_context = self._extract_technical_details(incident)

        # Calculate confidence score
        confidence_score = self._calculate_confidence(technical_context)

        # Create PagerAlert
        pager_alert = PagerAlert(
            alert_id=incident.id,
            severity=self._map_urgency_to_severity(incident.urgency),
            service_name=incident.service.name if incident.service else "unknown",
            description=incident.description or incident.title,
            timestamp=incident.created_at.isoformat() if hasattr(incident.created_at, 'isoformat') else str(incident.created_at),
            metadata={
                "incident_number": incident.incident_number,
                "status": incident.status,
                "html_url": incident.html_url,
                "alert_type": alert_type,
                "custom_details": incident.custom_details or {},
            }
        )

        # Build complete context
        context = {
            "alert_type": alert_type,
            "technical_details": technical_context,
            "confidence_score": confidence_score,
            "time_context": self._get_time_context(incident.created_at),
            "suggested_prompt": self._generate_prompt(alert_type, technical_context, incident),
        }

        return pager_alert, context

    def _classify_alert(self, incident: PagerDutyIncidentData) -> str:
        """Classify the alert type based on incident details."""
        text = f"{incident.title} {incident.description or ''} {str(incident.custom_details or '')}".lower()

        scores = {}
        for alert_type, keywords in self.alert_classifiers.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[alert_type] = score

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return "general"

    def _extract_technical_details(self, incident: PagerDutyIncidentData) -> dict[str, Any]:
        """Extract technical details from incident using regex patterns."""
        details = {}

        # Combine all text sources
        text_sources = [
            incident.title,
            incident.description or "",
            str(incident.custom_details or {})
        ]
        full_text = " ".join(text_sources)

        # Extract using patterns
        for detail_type, pattern in self.patterns.items():
            matches = pattern.findall(full_text)
            if matches:
                details[detail_type] = matches[0] if isinstance(matches[0], str) else matches[0][0]

        # Extract from custom_details if available
        if incident.custom_details:
            details.update(self._extract_from_custom_details(incident.custom_details))

        return details

    def _extract_from_custom_details(self, custom_details: dict[str, Any]) -> dict[str, Any]:
        """Extract structured data from PagerDuty custom_details."""
        extracted = {}

        # Common custom detail keys
        key_mappings = {
            'error_rate': ['error_rate', 'errorRate', 'errors_per_minute'],
            'response_time': ['response_time', 'responseTime', 'latency'],
            'availability': ['availability', 'uptime', 'success_rate'],
            'affected_users': ['affected_users', 'affectedUsers', 'user_count'],
            'region': ['region', 'datacenter', 'zone'],
            'stack_trace': ['stack_trace', 'stackTrace', 'exception'],
        }

        for target_key, possible_keys in key_mappings.items():
            for key in possible_keys:
                if key in custom_details:
                    extracted[target_key] = custom_details[key]
                    break

        return extracted

    def _map_urgency_to_severity(self, urgency: str) -> str:
        """Map PagerDuty urgency to oncall agent severity."""
        mapping = {
            'high': 'critical',
            'low': 'warning',
            'medium': 'error',
        }
        return mapping.get(urgency.lower(), 'error')

    def _calculate_confidence(self, technical_context: dict[str, Any]) -> float:
        """Calculate confidence score based on extracted context."""
        if not technical_context:
            return 0.0

        # Base score on amount of extracted data
        field_count = len(technical_context)
        base_score = min(field_count * 0.15, 0.6)

        # Bonus for specific high-value fields
        high_value_fields = ['error_code', 'stack_trace', 'pod_name', 'ip_address']
        bonus = sum(0.1 for field in high_value_fields if field in technical_context)

        return min(base_score + bonus, 1.0)

    def _get_time_context(self, created_at: datetime) -> dict[str, str]:
        """Get time-based context for the incident."""
        hour = created_at.hour
        day_of_week = created_at.strftime('%A')

        # Determine time period
        if 0 <= hour < 6:
            time_period = "early morning"
            business_hours = False
        elif 6 <= hour < 12:
            time_period = "morning"
            business_hours = hour >= 9
        elif 12 <= hour < 18:
            time_period = "afternoon"
            business_hours = hour < 17
        else:
            time_period = "evening"
            business_hours = False

        return {
            "time_period": time_period,
            "day_of_week": day_of_week,
            "business_hours": "yes" if business_hours else "no",
            "timestamp": created_at.isoformat(),
        }

    def _generate_prompt(self, alert_type: str, technical_details: dict[str, Any],
                        incident: PagerDutyIncidentData) -> str:
        """Generate a context-aware prompt for the oncall agent."""
        prompts = {
            'database': f"""Database incident detected: {incident.title}
Technical context: {technical_details}
Focus on: query performance, connection issues, data integrity, and replication status.""",

            'server': f"""Server incident detected: {incident.title}
Technical context: {technical_details}
Focus on: resource utilization, process health, system load, and potential OOM conditions.""",

            'security': f"""Security incident detected: {incident.title}
Technical context: {technical_details}
Focus on: threat assessment, affected systems, data exposure risk, and immediate containment steps.""",

            'network': f"""Network incident detected: {incident.title}
Technical context: {technical_details}
Focus on: connectivity issues, latency problems, packet loss, and affected services.""",

            'kubernetes': f"""Kubernetes incident detected: {incident.title}
Technical context: {technical_details}
Focus on: pod health, deployment status, resource constraints, and cluster state.""",

            'general': f"""Incident detected: {incident.title}
Technical context: {technical_details}
Analyze the issue and provide comprehensive recommendations."""
        }

        return prompts.get(alert_type, prompts['general'])
