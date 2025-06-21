"""API schemas and models for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# Enums
class IncidentStatus(str, Enum):
    """Incident status enumeration."""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Severity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IntegrationStatus(str, Enum):
    """Integration connection status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


class ActionType(str, Enum):
    """Types of actions that can be taken."""
    RESTART_POD = "restart_pod"
    SCALE_DEPLOYMENT = "scale_deployment"
    ROLLBACK = "rollback"
    RUN_DIAGNOSTICS = "run_diagnostics"
    CREATE_TICKET = "create_ticket"
    NOTIFY_TEAM = "notify_team"
    CUSTOM = "custom"


# Base Models
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


# Dashboard Models
class MetricValue(BaseModel):
    """Individual metric value."""
    value: float
    timestamp: datetime
    label: Optional[str] = None


class DashboardMetric(BaseModel):
    """Dashboard metric data."""
    name: str
    current_value: float
    change_percentage: Optional[float] = None
    trend: List[MetricValue] = []
    unit: Optional[str] = None


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    incidents_total: int
    incidents_active: int
    incidents_resolved_today: int
    avg_resolution_time_minutes: float
    automation_success_rate: float
    integrations_healthy: int
    integrations_total: int
    last_incident_time: Optional[datetime] = None


# Incident Models
class IncidentCreate(BaseModel):
    """Create incident request."""
    title: str
    description: str
    severity: Severity
    service_name: str
    alert_source: str = "manual"
    metadata: Dict[str, Any] = {}


class IncidentUpdate(BaseModel):
    """Update incident request."""
    status: Optional[IncidentStatus] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None
    resolution: Optional[str] = None


class IncidentAction(BaseModel):
    """Action taken on an incident."""
    action_type: ActionType
    parameters: Dict[str, Any] = {}
    automated: bool = True
    user: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    result: Optional[Dict[str, Any]] = None


class AIAnalysis(BaseModel):
    """AI agent analysis result."""
    summary: str
    root_cause: Optional[str] = None
    impact_assessment: str
    recommended_actions: List[Dict[str, Any]] = []
    confidence_score: float = Field(ge=0, le=1)
    related_incidents: List[str] = []
    knowledge_base_references: List[str] = []


class Incident(TimestampMixin):
    """Complete incident model."""
    id: str
    title: str
    description: str
    severity: Severity
    status: IncidentStatus
    service_name: str
    alert_source: str
    assignee: Optional[str] = None
    ai_analysis: Optional[AIAnalysis] = None
    actions_taken: List[IncidentAction] = []
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    timeline: List[Dict[str, Any]] = []


class IncidentList(BaseModel):
    """Paginated incident list."""
    incidents: List[Incident]
    total: int
    page: int
    page_size: int
    has_next: bool


# AI Agent Models
class AgentTriggerRequest(BaseModel):
    """Manual agent trigger request."""
    incident_id: str
    force_reanalyze: bool = False
    context: Dict[str, Any] = {}


class AgentResponse(BaseModel):
    """Agent analysis response."""
    incident_id: str
    analysis: AIAnalysis
    automated_actions: List[IncidentAction] = []
    execution_time_ms: float
    tokens_used: Optional[int] = None


class AgentStatus(BaseModel):
    """Agent system status."""
    status: str = "healthy"
    version: str
    uptime_seconds: float
    incidents_processed_today: int
    average_response_time_ms: float
    queue_size: int
    active_integrations: List[str]
    last_error: Optional[str] = None


# Integration Models
class IntegrationConfig(BaseModel):
    """Integration configuration."""
    enabled: bool
    config: Dict[str, Any] = {}


class IntegrationHealth(BaseModel):
    """Integration health check result."""
    name: str
    status: IntegrationStatus
    last_check: datetime
    error: Optional[str] = None
    metrics: Dict[str, Any] = {}


class Integration(BaseModel):
    """Integration details."""
    name: str
    type: str
    status: IntegrationStatus
    capabilities: List[str]
    config: IntegrationConfig
    health: Optional[IntegrationHealth] = None


# Analytics Models
class TimeRange(BaseModel):
    """Time range for analytics queries."""
    start: datetime
    end: datetime


class AnalyticsQuery(BaseModel):
    """Analytics query parameters."""
    time_range: TimeRange
    group_by: Optional[str] = None
    filters: Dict[str, Any] = {}


class IncidentAnalytics(BaseModel):
    """Incident analytics data."""
    total_incidents: int
    by_severity: Dict[str, int]
    by_service: Dict[str, int]
    by_status: Dict[str, int]
    mttr_by_severity: Dict[str, float]  # Mean Time To Resolution
    automation_rate: float
    trend_data: List[Dict[str, Any]]


class ServiceHealth(BaseModel):
    """Service health metrics."""
    service_name: str
    incident_count: int
    availability_percentage: float
    mttr_minutes: float
    last_incident: Optional[datetime] = None
    health_score: float = Field(ge=0, le=100)


# Security/Audit Models
class AuditAction(str, Enum):
    """Types of auditable actions."""
    INCIDENT_CREATED = "incident_created"
    INCIDENT_UPDATED = "incident_updated"
    INCIDENT_RESOLVED = "incident_resolved"
    ACTION_EXECUTED = "action_executed"
    INTEGRATION_CONFIGURED = "integration_configured"
    SETTINGS_CHANGED = "settings_changed"
    USER_LOGIN = "user_login"


class AuditLogEntry(TimestampMixin):
    """Audit log entry."""
    id: str
    action: AuditAction
    user: Optional[str] = None
    resource_type: str
    resource_id: str
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogList(BaseModel):
    """Paginated audit log list."""
    entries: List[AuditLogEntry]
    total: int
    page: int
    page_size: int


# Live Monitoring Models
class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEntry(BaseModel):
    """System log entry."""
    timestamp: datetime
    level: LogLevel
    source: str
    message: str
    context: Dict[str, Any] = {}


class MonitoringMetric(BaseModel):
    """Real-time monitoring metric."""
    name: str
    value: Union[float, int, str]
    unit: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = {}


class SystemStatus(BaseModel):
    """Overall system status."""
    status: str
    components: Dict[str, str]
    metrics: List[MonitoringMetric]
    alerts: List[Dict[str, Any]] = []


# Settings Models
class NotificationSettings(BaseModel):
    """Notification preferences."""
    email_enabled: bool = True
    slack_enabled: bool = False
    slack_channel: Optional[str] = None
    severity_threshold: Severity = Severity.MEDIUM
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None


class AutomationSettings(BaseModel):
    """Automation configuration."""
    auto_acknowledge: bool = True
    auto_resolve: bool = False
    require_approval_for_actions: bool = True
    max_automated_actions: int = 5
    allowed_action_types: List[ActionType] = []


class GlobalSettings(BaseModel):
    """Global system settings."""
    organization_name: str
    timezone: str = "UTC"
    retention_days: int = 90
    notifications: NotificationSettings
    automation: AutomationSettings
    integrations: Dict[str, IntegrationConfig] = {}


# WebSocket Models
class WSMessage(BaseModel):
    """WebSocket message format."""
    type: str
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSSubscription(BaseModel):
    """WebSocket subscription request."""
    channels: List[str]
    filters: Dict[str, Any] = {}


# Response Models
class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None