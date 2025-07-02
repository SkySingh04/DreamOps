'use client';

import React, { useEffect } from 'react';
import { useDemo } from '@/lib/demo/DemoContext';
import { MOCK_INTEGRATIONS } from '@/lib/demo/mockData';

interface DemoIntegrationsDataProps {
  children: React.ReactNode;
}

// Hook to provide demo data during demo mode
export function useDemoIntegrations(originalData: any) {
  const { state } = useDemo();
  
  if (!state.isActive) {
    return originalData;
  }

  // Convert mock integrations to the format expected by the integrations page
  const mockIntegrationsArray = Object.values(MOCK_INTEGRATIONS).map((integration) => ({
    id: integration.name,
    name: integration.displayName,
    description: integration.description,
    type: integration.type,
    status: integration.enabled ? 'connected' : 'not_configured',
    enabled: integration.enabled,
    capabilities: getCapabilitiesForIntegration(integration.type),
    last_sync: new Date().toISOString(),
    configured: true,
    connected: integration.enabled,
  }));

  return {
    ...originalData,
    data: mockIntegrationsArray,
  };
}

function getCapabilitiesForIntegration(type: string): string[] {
  const capabilities: Record<string, string[]> = {
    pagerduty: ['incident-management', 'alerting', 'escalation', 'on-call-scheduling'],
    kubernetes: ['pod-management', 'deployment-monitoring', 'resource-scaling', 'health-checks'],
    github: ['repository-access', 'commit-tracking', 'pr-monitoring', 'deployment-integration'],
    notion: ['documentation', 'runbook-management', 'knowledge-base', 'incident-reports'],
    grafana: ['metrics-visualization', 'dashboards', 'alerting', 'monitoring'],
  };
  
  return capabilities[type] || ['basic-integration'];
}

// Hook to provide demo metrics during demo mode
export function useDemoMetrics(originalMetrics: any) {
  const { state } = useDemo();
  
  if (!state.isActive) {
    return originalMetrics;
  }

  const enabledCount = Object.values(state.integrations).filter(i => i.enabled).length;
  const totalCount = Object.keys(state.integrations).length;
  
  return {
    activeIncidents: state.incidentTriggered ? 1 : 0,
    resolvedToday: state.incidentTriggered ? 4 : 5,
    avgResponseTime: '2.3 min',
    healthScore: state.incidentTriggered ? 89 : (enabledCount === totalCount ? 98 : 96),
    aiAgentStatus: 'online' as const,
  };
}

// Hook to provide demo incidents during demo mode
export function useDemoIncidents(originalIncidents: any) {
  const { state } = useDemo();
  
  if (!state.isActive) {
    return originalIncidents;
  }

  if (!state.incidentTriggered) {
    return [];
  }

  return [
    {
      id: 1,
      title: 'Payment Service - Multiple Pod Failures',
      severity: 'critical',
      status: state.isResolving || state.completedAt ? 'resolved' : 'active',
      createdAt: new Date().toISOString(),
    }
  ];
}

// Hook to provide demo AI actions during demo mode
export function useDemoAiActions(originalActions: any) {
  const { state } = useDemo();
  
  if (!state.isActive) {
    return originalActions;
  }

  if (!state.incidentTriggered) {
    return [];
  }

  const actions = [
    {
      id: 1,
      action: 'analyze_incident',
      description: '🤖 Analyzing incident: Payment Service - Multiple Pod Failures',
      createdAt: new Date().toISOString()
    }
  ];

  if (state.isAnalyzing || state.isResolving || state.completedAt) {
    actions.push(
      {
        id: 2,
        action: 'fetch_kubernetes_status',
        description: '📊 Fetching Kubernetes pod status from production namespace',
        createdAt: new Date(Date.now() - 5000).toISOString()
      },
      {
        id: 3,
        action: 'check_grafana_metrics',
        description: '📈 Checking Grafana metrics for memory and CPU usage',
        createdAt: new Date(Date.now() - 10000).toISOString()
      }
    );
  }

  if (state.isResolving || state.completedAt) {
    actions.push(
      {
        id: 4,
        action: 'restart_pods',
        description: '✅ Restarting failed pods in payment-service deployment',
        createdAt: new Date(Date.now() - 15000).toISOString()
      },
      {
        id: 5,
        action: 'increase_memory_limits',
        description: '✅ Increasing memory limits from 512Mi to 1Gi',
        createdAt: new Date(Date.now() - 20000).toISOString()
      }
    );
  }

  if (state.completedAt) {
    actions.push({
      id: 6,
      action: 'incident_resolved',
      description: '✅ Incident resolved and PagerDuty updated',
      createdAt: new Date(Date.now() - 25000).toISOString()
    });
  }

  return actions;
}

export function DemoIntegrationsData({ children }: DemoIntegrationsDataProps) {
  return <>{children}</>;
}