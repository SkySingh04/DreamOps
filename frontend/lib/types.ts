// Type definitions for the Oncall AI Agent dashboard

export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type IncidentStatus = 'active' | 'resolved' | 'monitoring' | 'acknowledged';
export type IntegrationStatus = 'connected' | 'error' | 'pending' | 'disconnected' | 'not_configured';
export type AIMode = 'yolo' | 'plan' | 'approval';
export type RiskLevel = 'low' | 'medium' | 'high';

export interface Incident {
  id: string;
  incident_number: number;
  title: string;
  description: string;
  service: {
    id: string;
    name: string;
    html_url: string;
    summary?: string;
  };
  severity: Severity;
  status: IncidentStatus;
  created_at: string;
  resolved_at?: string;
  acknowledged_at?: string;
  assignee?: string;
  custom_details?: Record<string, any>;
  ai_analysis?: AIAnalysis;
  actions?: AIAction[];
  timeline?: TimelineEvent[];
}

export interface AIAnalysis {
  severity: Severity;
  confidence_score: number;
  root_cause_analysis: {
    likely_cause: string;
    evidence: string[];
    confidence: number;
  };
  impact_assessment: {
    scope: string;
    business_impact: string;
    affected_components: string[];
    estimated_users_affected?: number;
  };
  recommended_actions: {
    immediate: string[];
    follow_up: string[];
  };
  monitoring_suggestions: string[];
  context?: Record<string, any>;
}

export interface AIAction {
  id: string;
  timestamp: string;
  type: 'diagnosis' | 'remediation' | 'monitoring' | 'notification';
  description: string;
  confidence_score: number;
  risk_level: RiskLevel;
  status: 'pending' | 'approved' | 'executing' | 'completed' | 'failed' | 'rolled_back';
  integration_used?: string;
  result?: {
    success: boolean;
    message: string;
    data?: any;
  };
  can_rollback?: boolean;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  type: 'alert' | 'action' | 'comment' | 'status_change';
  title: string;
  description?: string;
  user?: string;
  metadata?: Record<string, any>;
}

export interface Integration {
  id: string;
  name: string;
  description: string;
  icon?: string;
  status: IntegrationStatus;
  enabled: boolean;
  last_sync?: string;
  error?: string;
  config?: Record<string, any>;
  health_data?: {
    latency_ms: number;
    success_rate: number;
    last_error?: string;
  };
  metrics?: Record<string, number>;
}

export interface DashboardMetrics {
  total_incidents: number;
  active_incidents: number;
  resolved_today: number;
  avg_resolution_time: string;
  success_rate: number;
  time_saved_hours: number;
  ai_agent_status: 'online' | 'offline' | 'degraded';
  ai_mode: AIMode;
  integrations_health: {
    total: number;
    connected: number;
    errors: number;
  };
}

export interface AIAgentConfig {
  mode: AIMode;
  confidence_threshold: number;
  risk_matrix: {
    low: string[];
    medium: string[];
    high: string[];
  };
  auto_execute_enabled: boolean;
  approval_required_for: RiskLevel[];
  notification_preferences: {
    slack_enabled: boolean;
    email_enabled: boolean;
    channels: string[];
  };
}

export interface AnalyticsData {
  incidents_over_time: Array<{
    date: string;
    critical: number;
    high: number;
    medium: number;
    low: number;
  }>;
  resolution_time_trend: Array<{
    date: string;
    avg_minutes: number;
  }>;
  success_rate_trend: Array<{
    date: string;
    rate: number;
  }>;
  incident_by_service: Array<{
    service: string;
    count: number;
  }>;
  cost_savings: {
    total_saved: number;
    breakdown: Array<{
      month: string;
      amount: number;
    }>;
  };
}

export interface WebSocketMessage {
  type: 'incident_update' | 'integration_status' | 'ai_action' | 'metric_update';
  data: any;
  timestamp: string;
}

export interface APIResponse<T> {
  status: 'success' | 'error';
  data?: T;
  error?: {
    message: string;
    code?: string;
  };
  metadata?: {
    timestamp: string;
    request_id: string;
  };
}