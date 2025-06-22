"""API schemas and models for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any

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




class AIMode(str, Enum):
    """AI operation modes."""
    YOLO = "yolo"
    PLAN = "plan"
    APPROVAL = "approval"


class RiskLevel(str, Enum):
    """Risk levels for actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Base Models
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None


# Dashboard Models
class MetricValue(BaseModel):
    """Individual metric value."""
    value: float
    timestamp: datetime
    label: str | None = None


class DashboardMetric(BaseModel):
    """Dashboard metric data."""
    name: str
    current_value: float
    change_percentage: float | None = None
    trend: list[MetricValue] = []
    unit: str | None = None


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    incidents_total: int
    incidents_active: int
    incidents_resolved_today: int
    avg_resolution_time_minutes: float
    automation_success_rate: float
    integrations_healthy: int
    integrations_total: int
    last_incident_time: datetime | None = None


# Incident Models
class IncidentCreate(BaseModel):
    """Create incident request."""
    title: str
    description: str
    severity: Severity
    service_name: str
    alert_source: str = "manual"
    metadata: dict[str, Any] = {}


class IncidentUpdate(BaseModel):
    """Update incident request."""
    status: IncidentStatus | None = None
    assignee: str | None = None
    notes: str | None = None
    resolution: str | None = None


class IncidentAction(BaseModel):
    """Action taken on an incident."""
    action_type: ActionType
    parameters: dict[str, Any] = {}
    automated: bool = True
    user: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    result: dict[str, Any] | None = None


class AIAnalysis(BaseModel):
    """AI agent analysis result."""
    summary: str
    root_cause: str | None = None
    impact_assessment: str
    recommended_actions: list[dict[str, Any]] = []
    confidence_score: float = Field(ge=0, le=1)
    related_incidents: list[str] = []
    knowledge_base_references: list[str] = []


class Incident(TimestampMixin):
    """Complete incident model."""
    id: str
    title: str
    description: str
    severity: Severity
    status: IncidentStatus
    service_name: str
    alert_source: str
    assignee: str | None = None
    ai_analysis: AIAnalysis | None = None
    actions_taken: list[IncidentAction] = []
    resolution: str | None = None
    resolved_at: datetime | None = None
    metadata: dict[str, Any] = {}
    timeline: list[dict[str, Any]] = []


class IncidentList(BaseModel):
    """Paginated incident list."""
    incidents: list[Incident]
    total: int
    page: int
    page_size: int
    has_next: bool


# AI Agent Models
class AgentTriggerRequest(BaseModel):
    """Manual agent trigger request."""
    incident_id: str
    force_reanalyze: bool = False
    context: dict[str, Any] = {}


class AgentResponse(BaseModel):
    """Agent analysis response."""
    incident_id: str
    analysis: AIAnalysis
    automated_actions: list[IncidentAction] = []
    execution_time_ms: float
    tokens_used: int | None = None


class AgentStatus(BaseModel):
    """Agent system status."""
    status: str = "healthy"
    version: str
    uptime_seconds: float
    incidents_processed_today: int
    average_response_time_ms: float
    queue_size: int
    active_integrations: list[str]
    last_error: str | None = None


class NotificationPreferences(BaseModel):
    """Notification preferences for AI agent."""
    slack_enabled: bool = True
    email_enabled: bool = False
    channels: list[str] = []


class AIAgentConfig(BaseModel):
    """AI Agent configuration."""
    mode: AIMode = AIMode.APPROVAL
    confidence_threshold: int = Field(70, ge=0, le=100)
    risk_matrix: dict[str, list[str]] = {}
    auto_execute_enabled: bool = True
    approval_required_for: list[RiskLevel] = [RiskLevel.MEDIUM, RiskLevel.HIGH]
    notification_preferences: NotificationPreferences = NotificationPreferences()


class AIAgentConfigUpdate(BaseModel):
    """AI Agent configuration update request."""
    mode: AIMode | None = None
    confidence_threshold: int | None = Field(None, ge=0, le=100)
    risk_matrix: dict[str, list[str]] | None = None
    auto_execute_enabled: bool | None = None
    approval_required_for: list[RiskLevel] | None = None
    notification_preferences: NotificationPreferences | None = None


# Safety and Risk Management Models
class ConfidenceFactors(BaseModel):
    """Breakdown of confidence scoring factors."""
    pattern_recognition: float = Field(ge=0, le=1)
    historical_success: float = Field(ge=0, le=1)
    context_quality: float = Field(ge=0, le=1)
    resource_availability: float = Field(ge=0, le=1)
    time_sensitivity: float = Field(ge=0, le=1)


class ConfidenceScore(BaseModel):
    """Confidence scoring result."""
    overall_confidence: float = Field(ge=0, le=1)
    factor_breakdown: ConfidenceFactors
    recommendation: str
    threshold_met: bool


class ActionRiskAssessment(BaseModel):
    """Risk assessment for a specific action."""
    action_type: str
    risk_level: RiskLevel
    risk_factors: list[str]
    auto_execute_allowed: bool
    requires_approval: bool


class DryRunResult(BaseModel):
    """Result of a dry run execution."""
    action_id: str
    action_type: str
    would_execute: bool
    expected_outcome: str
    potential_risks: list[str]
    rollback_plan: str
    estimated_duration: int  # seconds
    resource_impact: dict[str, Any]


class ApprovalRequest(BaseModel):
    """Human approval request."""
    id: str
    incident_id: str
    action_plan: list[dict[str, Any]]
    confidence_score: ConfidenceScore
    risk_assessments: list[ActionRiskAssessment]
    requested_at: datetime
    timeout_at: datetime
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED
    comments: str = ""


class ActionHistory(BaseModel):
    """Historical record of executed actions."""
    id: str
    incident_id: str
    action_type: str
    action_details: dict[str, Any]
    executed_at: datetime
    original_state: dict[str, Any]
    rollback_available: bool
    rollback_executed: bool = False
    rollback_at: datetime | None = None


class SafetyConfig(BaseModel):
    """Safety configuration settings."""
    dry_run_mode: bool = False
    confidence_threshold: float = Field(0.8, ge=0, le=1)
    risk_tolerance: RiskLevel = RiskLevel.MEDIUM
    auto_execute_permissions: dict[str, bool] = {}
    mandatory_approval_actions: list[str] = []
    emergency_stop_active: bool = False


# Integration Models
class IntegrationConfig(BaseModel):
    """Integration configuration."""
    enabled: bool
    config: dict[str, Any] = {}


class IntegrationHealth(BaseModel):
    """Integration health check result."""
    name: str
    status: IntegrationStatus
    last_check: datetime
    error: str | None = None
    metrics: dict[str, Any] = {}


class Integration(BaseModel):
    """Integration details."""
    name: str
    type: str
    status: IntegrationStatus
    capabilities: list[str]
    config: IntegrationConfig
    health: IntegrationHealth | None = None


# Analytics Models
class TimeRange(BaseModel):
    """Time range for analytics queries."""
    start: datetime
    end: datetime


class AnalyticsQuery(BaseModel):
    """Analytics query parameters."""
    time_range: TimeRange
    group_by: str | None = None
    filters: dict[str, Any] = {}


class IncidentAnalytics(BaseModel):
    """Incident analytics data."""
    total_incidents: int
    by_severity: dict[str, int]
    by_service: dict[str, int]
    by_status: dict[str, int]
    mttr_by_severity: dict[str, float]  # Mean Time To Resolution
    automation_rate: float
    trend_data: list[dict[str, Any]]


class ServiceHealth(BaseModel):
    """Service health metrics."""
    service_name: str
    incident_count: int
    availability_percentage: float
    mttr_minutes: float
    last_incident: datetime | None = None
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
    user: str | None = None
    resource_type: str
    resource_id: str
    details: dict[str, Any] = {}
    ip_address: str | None = None
    user_agent: str | None = None


class AuditLogList(BaseModel):
    """Paginated audit log list."""
    entries: list[AuditLogEntry]
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
    context: dict[str, Any] = {}


class MonitoringMetric(BaseModel):
    """Real-time monitoring metric."""
    name: str
    value: float | int | str
    unit: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: dict[str, str] = {}


class SystemStatus(BaseModel):
    """Overall system status."""
    status: str
    components: dict[str, str]
    metrics: list[MonitoringMetric]
    alerts: list[dict[str, Any]] = []


# Settings Models
class AISettings(BaseModel):
    """AI configuration settings."""
    model: str = "claude-3-5-sonnet"
    additional_context: str = ""
    auto_analyze: bool = True
    confidence_threshold: float = 0.8
    max_tokens: int = 4000
    temperature: float = 0.3

class AlertSettings(BaseModel):
    """Alert processing settings."""
    priority_threshold: Severity = Severity.HIGH
    auto_acknowledge: bool = False
    deduplication_enabled: bool = True
    deduplication_window_minutes: int = 15
    escalation_delay_minutes: int = 30

class SecuritySettings(BaseModel):
    """Security and compliance settings."""
    audit_logs_enabled: bool = True
    data_retention_days: int = 90
    require_2fa: bool = False
    session_timeout_minutes: int = 480
    ip_whitelist: list[str] = []

class APIKeySettings(BaseModel):
    """API keys and authentication."""
    anthropic_api_key: str = ""
    webhook_url: str = ""
    webhook_secret: str = ""

class NotificationSettings(BaseModel):
    """Notification preferences."""
    email_enabled: bool = True
    slack_enabled: bool = False
    slack_channel: str | None = None
    severity_threshold: Severity = Severity.MEDIUM
    quiet_hours_enabled: bool = False
    quiet_hours_start: str | None = None  # HH:MM format
    quiet_hours_end: str | None = None


class AutomationSettings(BaseModel):
    """Automation configuration."""
    auto_acknowledge: bool = True
    auto_resolve: bool = False
    require_approval_for_actions: bool = True
    max_automated_actions: int = 5
    allowed_action_types: list[ActionType] = []


class GlobalSettings(BaseModel):
    """Global system settings."""
    organization_name: str
    timezone: str = "UTC"
    retention_days: int = 90
    ai: AISettings = AISettings()
    alerts: AlertSettings = AlertSettings()
    security: SecuritySettings = SecuritySettings()
    api_keys: APIKeySettings = APIKeySettings()
    notifications: NotificationSettings
    automation: AutomationSettings
    integrations: dict[str, IntegrationConfig] = {}

class IntegrationTestResult(BaseModel):
    """Result of integration connection test."""
    success: bool
    message: str
    details: dict[str, Any] = {}
    latency_ms: float | None = None


# WebSocket Models
class WSMessage(BaseModel):
    """WebSocket message format."""
    type: str
    data: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSSubscription(BaseModel):
    """WebSocket subscription request."""
    channels: list[str]
    filters: dict[str, Any] = {}


# Response Models
class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str
    data: Any | None = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    details: dict[str, Any] | None = None
    request_id: str | None = None
