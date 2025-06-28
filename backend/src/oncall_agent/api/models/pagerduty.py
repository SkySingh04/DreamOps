"""PagerDuty webhook payload models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PagerDutyService(BaseModel):
    """PagerDuty service information."""
    id: str
    name: str
    html_url: str | None = None
    summary: str | None = None


class PagerDutyIncidentData(BaseModel):
    """PagerDuty incident details."""
    id: str
    incident_number: int
    title: str
    description: str | None = None
    created_at: datetime
    status: str
    incident_key: str | None = None
    service: PagerDutyService | None = None
    urgency: str = "high"
    priority: dict[str, Any] | None = None
    custom_details: dict[str, Any] | None = None
    html_url: str


class PagerDutyLogEntry(BaseModel):
    """PagerDuty webhook log entry."""
    id: str
    type: str
    summary: str
    created_at: datetime
    html_url: str | None = None


class PagerDutyMessage(BaseModel):
    """PagerDuty webhook message."""
    id: str
    incident: PagerDutyIncidentData
    log_entries: list[PagerDutyLogEntry] | None = None


# V3 Webhook Models
class PagerDutyV3Agent(BaseModel):
    """PagerDuty V3 agent information."""
    id: str
    type: str
    summary: str | None = None
    self: str | None = None
    html_url: str | None = None


class PagerDutyV3Event(BaseModel):
    """PagerDuty V3 webhook event."""
    id: str
    event_type: str
    occurred_at: datetime
    agent: PagerDutyV3Agent | None = None
    client: dict[str, Any] | None = None
    data: dict[str, Any]


class PagerDutyV3WebhookPayload(BaseModel):
    """PagerDuty V3 webhook payload."""
    event: PagerDutyV3Event


# Legacy V2 format for backward compatibility
class PagerDutyWebhookPayload(BaseModel):
    """PagerDuty webhook payload (supports both V2 and V3)."""
    messages: list[PagerDutyMessage] | None = None
    event: PagerDutyV3Event | str | None = None