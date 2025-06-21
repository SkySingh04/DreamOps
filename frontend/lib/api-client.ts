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
    return this.request<DashboardMetrics>('/api/dashboard/metrics');
  }

  // Incident endpoints
  async getIncidents(params?: {
    status?: string;
    severity?: string;
    limit?: number;
    offset?: number;
  }): Promise<APIResponse<Incident[]>> {
    const queryParams = new URLSearchParams(params as any).toString();
    return this.request<Incident[]>(`/api/incidents${queryParams ? `?${queryParams}` : ''}`);
  }

  async getIncident(id: string): Promise<APIResponse<Incident>> {
    return this.request<Incident>(`/api/incidents/${id}`);
  }

  async acknowledgeIncident(id: string): Promise<APIResponse<Incident>> {
    return this.request<Incident>(`/api/incidents/${id}/acknowledge`, {
      method: 'POST',
    });
  }

  async resolveIncident(id: string): Promise<APIResponse<Incident>> {
    return this.request<Incident>(`/api/incidents/${id}/resolve`, {
      method: 'POST',
    });
  }

  async triggerMockIncident(type: string): Promise<APIResponse<Incident>> {
    return this.request<Incident>('/api/incidents/mock', {
      method: 'POST',
      body: JSON.stringify({ type }),
    });
  }

  // AI Agent endpoints
  async getAIConfig(): Promise<APIResponse<AIAgentConfig>> {
    return this.request<AIAgentConfig>('/api/ai-agent/config');
  }

  async updateAIConfig(config: Partial<AIAgentConfig>): Promise<APIResponse<AIAgentConfig>> {
    return this.request<AIAgentConfig>('/api/ai-agent/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async executeAIAction(
    incidentId: string,
    actionId: string,
    approved: boolean
  ): Promise<APIResponse<AIAction>> {
    return this.request<AIAction>(`/api/incidents/${incidentId}/actions/${actionId}`, {
      method: 'POST',
      body: JSON.stringify({ approved }),
    });
  }

  async rollbackAction(
    incidentId: string,
    actionId: string
  ): Promise<APIResponse<AIAction>> {
    return this.request<AIAction>(`/api/incidents/${incidentId}/actions/${actionId}/rollback`, {
      method: 'POST',
    });
  }

  async emergencyStop(): Promise<APIResponse<void>> {
    return this.request<void>('/api/ai-agent/emergency-stop', {
      method: 'POST',
    });
  }

  // Integration endpoints
  async getIntegrations(): Promise<APIResponse<Integration[]>> {
    return this.request<Integration[]>('/api/integrations');
  }

  async getIntegration(id: string): Promise<APIResponse<Integration>> {
    return this.request<Integration>(`/api/integrations/${id}`);
  }

  async testIntegration(id: string): Promise<APIResponse<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(`/api/integrations/${id}/test`, {
      method: 'POST',
    });
  }

  async updateIntegrationConfig(
    id: string,
    config: Record<string, any>
  ): Promise<APIResponse<Integration>> {
    return this.request<Integration>(`/api/integrations/${id}/config`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async toggleIntegration(id: string, enabled: boolean): Promise<APIResponse<Integration>> {
    return this.request<Integration>(`/api/integrations/${id}/toggle`, {
      method: 'POST',
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
    return this.request<AnalyticsData>(`/api/analytics${queryParams ? `?${queryParams}` : ''}`);
  }

  async exportReport(format: 'csv' | 'pdf', params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<Blob> {
    const queryParams = new URLSearchParams(params as any).toString();
    const response = await fetch(
      `${this.baseURL}/api/analytics/export/${format}${queryParams ? `?${queryParams}` : ''}`,
      {
        headers: this.headers,
      }
    );

    if (!response.ok) {
      throw new Error('Export failed');
    }

    return response.blob();
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
  incidents: (params?: any) => ['incidents', params],
  incident: (id: string) => ['incident', id],
  integrations: ['integrations'],
  integration: (id: string) => ['integration', id],
  aiConfig: ['ai-agent', 'config'],
  analytics: (params?: any) => ['analytics', params],
} as const;