"""PagerDuty webhook payload models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PagerDutyService(BaseModel):
    """PagerDuty service information."""
    id: str
    name: str
    html_url: Optional[str] = None
    summary: Optional[str] = None


class PagerDutyIncidentData(BaseModel):
    """PagerDuty incident details."""
    id: str
    incident_number: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    status: str
    incident_key: Optional[str] = None
    service: Optional[PagerDutyService] = None
    urgency: str = "high"
    priority: Optional[Dict[str, Any]] = None
    custom_details: Optional[Dict[str, Any]] = None
    html_url: str


class PagerDutyLogEntry(BaseModel):
    """PagerDuty webhook log entry."""
    id: str
    type: str
    summary: str
    created_at: datetime
    html_url: Optional[str] = None


class PagerDutyMessage(BaseModel):
    """PagerDuty webhook message."""
    id: str
    incident: PagerDutyIncidentData
    log_entries: Optional[List[PagerDutyLogEntry]] = None


class PagerDutyWebhookPayload(BaseModel):
    """PagerDuty webhook payload."""
    messages: List[PagerDutyMessage]
    event: Optional[str] = Field(None, description="Event type like 'incident.triggered'")