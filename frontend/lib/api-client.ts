// API client for interacting with the Oncall Agent backend

import { 
  Incident, 
  Integration, 
  DashboardMetrics, 
  AIAgentConfig, 
  AnalyticsData,
  APIResponse,
  AIAction
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  private baseURL: string;
  private headers: HeadersInit;

  constructor() {
    this.baseURL = API_BASE_URL;
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers: {
          ...this.headers,
          ...options.headers,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || 'API request failed');
      }

      return {
        status: 'success',
        data: data,
      };
    } catch (error) {
      return {
        status: 'error',
        error: {
          message: error instanceof Error ? error.message : 'Unknown error',
        },
      };
    }
  }

  // Dashboard endpoints
  async getDashboardMetrics(): Promise<APIResponse<DashboardMetrics>> {
    return this.request<DashboardMetrics>('/api/v1/dashboard/metrics');
  }

  async getDashboardStats(): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/dashboard/stats');
  }

  async getActivityFeed(limit: number = 10): Promise<APIResponse<any>> {
    return this.request<any>(`/api/v1/dashboard/activity?limit=${limit}`);
  }

  // Incident endpoints
  async getIncidents(params?: {
    status?: string;
    severity?: string;
    limit?: number;
    offset?: number;
  }): Promise<APIResponse<{ incidents: Incident[]; total: number }>> {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request<{ incidents: Incident[]; total: number }>(`/api/v1/incidents${queryParams ? `?${queryParams}` : ''}`);
  }

  async getIncident(id: string): Promise<APIResponse<Incident>> {
    return this.request<Incident>(`/api/v1/incidents/${id}`);
  }

  async acknowledgeIncident(id: string): Promise<APIResponse<Incident>> {
    return this.request<Incident>(`/api/v1/incidents/${id}/acknowledge`, {
      method: 'POST',
    });
  }

  async resolveIncident(id: string): Promise<APIResponse<Incident>> {
    return this.request<Incident>(`/api/v1/incidents/${id}/resolve`, {
      method: 'POST',
    });
  }

  async triggerMockIncident(type: string): Promise<APIResponse<Incident>> {
    return this.request<Incident>('/api/v1/incidents/mock', {
      method: 'POST',
      body: JSON.stringify({ incident_type: type }),
    });
  }

  async getIncidentTimeline(id: string): Promise<APIResponse<any[]>> {
    return this.request<any[]>(`/api/v1/incidents/${id}/timeline`);
  }

  async executeIncidentAction(
    incidentId: string,
    actionId: string
  ): Promise<APIResponse<any>> {
    return this.request<any>(`/api/v1/incidents/${incidentId}/actions/${actionId}/execute`, {
      method: 'POST',
    });
  }

  // AI Agent endpoints
  async getAIConfig(): Promise<APIResponse<AIAgentConfig>> {
    return this.request<AIAgentConfig>('/api/v1/agent/config');
  }

  async updateAIConfig(config: Partial<AIAgentConfig>): Promise<APIResponse<AIAgentConfig>> {
    return this.request<AIAgentConfig>('/api/v1/agent/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async getAgentStatus(): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/agent/status');
  }

  async triggerAnalysis(incidentId: string): Promise<APIResponse<any>> {
    return this.request<any>(`/api/v1/agent/analyze/${incidentId}`, {
      method: 'POST',
    });
  }

  async executeAIAction(
    incidentId: string,
    actionId: string,
    approved: boolean
  ): Promise<APIResponse<AIAction>> {
    return this.request<AIAction>(`/api/v1/incidents/${incidentId}/actions/${actionId}/execute`, {
      method: 'POST',
      body: JSON.stringify({ approved }),
    });
  }

  async rollbackAction(
    incidentId: string,
    actionId: string
  ): Promise<APIResponse<AIAction>> {
    return this.request<AIAction>(`/api/v1/incidents/${incidentId}/actions/${actionId}/rollback`, {
      method: 'POST',
    });
  }

  async emergencyStop(): Promise<APIResponse<void>> {
    return this.request<void>('/api/v1/agent/emergency-stop', {
      method: 'POST',
    });
  }

  // Integration endpoints
  async getIntegrations(): Promise<APIResponse<Integration[]>> {
    return this.request<Integration[]>('/integrations');
  }

  async getMCPIntegrations(): Promise<APIResponse<{ integrations: Array<{ name: string; capabilities: string[]; connected: boolean }> }>> {
    // Call the correct backend endpoint for real MCP integrations
    const response = await this.request<Array<{ name: string; capabilities: string[]; status: string }>>('/api/v1/integrations/');
    console.log('MCP Integrations Response:', response); // Debug log
    
    // Transform the response to match the expected format
    if (response.status === 'success' && response.data) {
      const transformedData = {
        integrations: response.data.map((integration: any) => ({
          name: integration.name,
          capabilities: integration.capabilities || [],
          connected: integration.status === 'connected'
        }))
      };
      return {
        status: 'success',
        data: transformedData
      };
    }
    
    return response as any;
  }

  async getIntegration(id: string): Promise<APIResponse<Integration>> {
    return this.request<Integration>(`/api/v1/integrations/${id}`);
  }

  async testIntegration(id: string): Promise<APIResponse<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(`/api/v1/integrations/${id}/test`, {
      method: 'POST',
    });
  }

  async updateIntegrationConfig(
    id: string,
    config: Record<string, any>
  ): Promise<APIResponse<Integration>> {
    return this.request<Integration>(`/api/v1/integrations/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ config }),
    });
  }

  async toggleIntegration(id: string, enabled: boolean): Promise<APIResponse<Integration>> {
    return this.request<Integration>(`/api/v1/integrations/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ enabled }),
    });
  }

  // Analytics endpoints
  async getAnalytics(params?: {
    start_date?: string;
    end_date?: string;
    granularity?: 'hour' | 'day' | 'week' | 'month';
  }): Promise<APIResponse<AnalyticsData>> {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request<AnalyticsData>(`/api/v1/analytics${queryParams ? `?${queryParams}` : ''}`);
  }

  async getServiceHealth(service?: string): Promise<APIResponse<any>> {
    const endpoint = service ? `/api/v1/analytics/services/${service}` : '/api/v1/analytics/services';
    return this.request<any>(endpoint);
  }

  async getPatterns(): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/analytics/patterns');
  }

  async exportReport(format: 'csv' | 'pdf', params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<Blob> {
    const queryParams = new URLSearchParams(params as any).toString();
    const response = await fetch(
      `${this.baseURL}/api/v1/analytics/export?format=${format}${queryParams ? `&${queryParams}` : ''}`,
      {
        headers: this.headers,
      }
    );

    if (!response.ok) {
      throw new Error('Export failed');
    }

    return response.blob();
  }

  // Security endpoints
  async getAuditLogs(params?: {
    start_date?: string;
    end_date?: string;
    user_id?: string;
    action_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<APIResponse<any>> {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request<any>(`/api/v1/security/audit${queryParams ? `?${queryParams}` : ''}`);
  }

  async getPermissions(): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/security/permissions');
  }

  async updatePermissions(userId: string, permissions: string[]): Promise<APIResponse<any>> {
    return this.request<any>(`/api/v1/security/permissions/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({ permissions }),
    });
  }

  async rotateAPIKey(keyId: string): Promise<APIResponse<any>> {
    return this.request<any>(`/api/v1/security/api-keys/${keyId}/rotate`, {
      method: 'POST',
    });
  }

  // Monitoring endpoints
  async getLogs(params?: {
    level?: string;
    source?: string;
    search?: string;
    limit?: number;
  }): Promise<APIResponse<any>> {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request<any>(`/api/v1/monitoring/logs${queryParams ? `?${queryParams}` : ''}`);
  }

  async getMetrics(): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/monitoring/metrics');
  }

  async getAlerts(): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/monitoring/alerts');
  }

  // Settings endpoints
  async getSettings(): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/settings');
  }

  async updateSettings(settings: any): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }

  async getNotificationPreferences(): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/settings/notifications');
  }

  async updateNotificationPreferences(preferences: any): Promise<APIResponse<any>> {
    return this.request<any>('/api/v1/settings/notifications', {
      method: 'PUT',
      body: JSON.stringify(preferences),
    });
  }

  // Health check
  async healthCheck(): Promise<APIResponse<{ status: string; checks: Record<string, any> }>> {
    return this.request<{ status: string; checks: Record<string, any> }>('/health');
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Export hooks for React Query
export const queryKeys = {
  dashboard: ['dashboard', 'metrics'],
  dashboardStats: ['dashboard', 'stats'],
  activityFeed: ['dashboard', 'activity'],
  incidents: (params?: any) => ['incidents', params],
  incident: (id: string) => ['incident', id],
  incidentTimeline: (id: string) => ['incident', id, 'timeline'],
  integrations: ['integrations'],
  integration: (id: string) => ['integration', id],
  aiConfig: ['ai-agent', 'config'],
  agentStatus: ['ai-agent', 'status'],
  analytics: (params?: any) => ['analytics', params],
  serviceHealth: (service?: string) => ['analytics', 'services', service],
  patterns: ['analytics', 'patterns'],
  auditLogs: (params?: any) => ['security', 'audit', params],
  permissions: ['security', 'permissions'],
  logs: (params?: any) => ['monitoring', 'logs', params],
  metrics: ['monitoring', 'metrics'],
  alerts: ['monitoring', 'alerts'],
  settings: ['settings'],
  notifications: ['settings', 'notifications'],
} as const;