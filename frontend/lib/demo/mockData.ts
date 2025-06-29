export interface MockIntegration {
  name: string;
  displayName: string;
  type: string;
  apiKey?: string;
  config?: string;
  token?: string;
  url?: string;
  webhookSecret?: string;
  namespace?: string;
  repo?: string;
  databaseId?: string;
  enabled: boolean;
  description: string;
}

export interface MockIncident {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  service: string;
  description: string;
  status: 'active' | 'resolved' | 'pending';
  createdAt: string;
  details: {
    error: string;
    cause: string;
    pods_affected: number;
    kubernetes_namespace?: string;
    memory_usage?: string;
    cpu_usage?: string;
  };
}

export interface MockMetrics {
  activeIncidents: number;
  resolvedToday: number;
  avgResponseTime: string;
  healthScore: number;
  aiAgentStatus: 'online' | 'offline';
}

export const MOCK_INTEGRATIONS: Record<string, MockIntegration> = {
  pagerduty: {
    name: 'pagerduty',
    displayName: 'PagerDuty',
    type: 'pagerduty',
    apiKey: 'pd_demo_u8Xm3Nk9VwQr7Hs2PmLz',
    webhookSecret: 'pd_webhook_secret_demo_xyz123',
    enabled: false,
    description: 'Incident management and on-call scheduling'
  },
  kubernetes: {
    name: 'kubernetes',
    displayName: 'Kubernetes',
    type: 'kubernetes',
    config: 'demo-production-cluster',
    namespace: 'production',
    enabled: false,
    description: 'Container orchestration and monitoring'
  },
  github: {
    name: 'github',
    displayName: 'GitHub',
    type: 'github',
    token: 'ghp_demo_kL8Hs9mVn3Qw2Xr7Bp4Tz6',
    repo: 'techcorp/payment-service',
    enabled: false,
    description: 'Source code management and CI/CD integration'
  },
  notion: {
    name: 'notion',
    displayName: 'Notion',
    type: 'notion',
    token: 'secret_demo_ntn8Xs4Vw9Qm2Hr7Kp3',
    databaseId: 'runbooks-database-demo-456',
    enabled: false,
    description: 'Knowledge base and runbook management'
  },
  grafana: {
    name: 'grafana',
    displayName: 'Grafana',
    type: 'grafana',
    url: 'https://demo-monitoring.grafana.local',
    apiKey: 'glsa_demo_8Hm2Nk9Vw7Qr3Xs4Bp5',
    enabled: false,
    description: 'Metrics visualization and monitoring dashboards'
  }
};

export const MOCK_INCIDENT: MockIncident = {
  id: 'INC-DEMO-001',
  title: 'Payment Service - Multiple Pod Failures',
  severity: 'critical',
  service: 'payment-service',
  description: 'Critical service disruption: Payment processing pods experiencing CrashLoopBackOff with OOM kills. Customer transactions failing.',
  status: 'active',
  createdAt: new Date().toISOString(),
  details: {
    error: 'CrashLoopBackOff',
    cause: 'OOMKilled - Memory limit exceeded (512Mi)',
    pods_affected: 3,
    kubernetes_namespace: 'production',
    memory_usage: '511Mi/512Mi (99.8%)',
    cpu_usage: '1.2/2.0 cores'
  }
};

export const MOCK_METRICS_INITIAL: MockMetrics = {
  activeIncidents: 0,
  resolvedToday: 4,
  avgResponseTime: '2.3 min',
  healthScore: 96,
  aiAgentStatus: 'online'
};

export const MOCK_METRICS_WITH_INCIDENT: MockMetrics = {
  activeIncidents: 1,
  resolvedToday: 4,
  avgResponseTime: '2.3 min',
  healthScore: 89,
  aiAgentStatus: 'online'
};

export const MOCK_METRICS_RESOLVED: MockMetrics = {
  activeIncidents: 0,
  resolvedToday: 5,
  avgResponseTime: '2.1 min',
  healthScore: 98,
  aiAgentStatus: 'online'
};

export const MOCK_AI_ACTIONS = [
  {
    id: 1,
    action: 'analyze_incident',
    description: '🤖 Analyzing incident: Payment Service - Multiple Pod Failures',
    createdAt: new Date().toISOString()
  },
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
  },
  {
    id: 4,
    action: 'review_github_commits',
    description: '🔍 Reviewing recent GitHub commits for potential causes',
    createdAt: new Date(Date.now() - 15000).toISOString()
  },
  {
    id: 5,
    action: 'search_notion_runbooks',
    description: '📚 Searching Notion runbooks for OOM kill remediation',
    createdAt: new Date(Date.now() - 20000).toISOString()
  },
  {
    id: 6,
    action: 'restart_pods',
    description: '✅ Restarting failed pods in payment-service deployment',
    createdAt: new Date(Date.now() - 25000).toISOString()
  },
  {
    id: 7,
    action: 'increase_memory_limits',
    description: '✅ Increasing memory limits from 512Mi to 1Gi',
    createdAt: new Date(Date.now() - 30000).toISOString()
  },
  {
    id: 8,
    action: 'create_incident_report',
    description: '✅ Creating incident report and updating PagerDuty',
    createdAt: new Date(Date.now() - 35000).toISOString()
  }
];

export const DEMO_ANALYSIS_STEPS = [
  '🤖 Analyzing alert details...',
  '📊 Fetching Kubernetes pod status...',
  '📈 Checking Grafana metrics...',
  '🔍 Reviewing recent GitHub commits...',
  '📚 Searching Notion runbooks...',
  '🔧 Identifying root cause...',
  '💡 Generating resolution plan...'
];

export const DEMO_RESOLUTION_ACTIONS = [
  {
    action: 'Restarting failed pods',
    description: 'Deleting pods to trigger restart',
    progress: 0
  },
  {
    action: 'Increasing memory limits',
    description: 'Updating deployment memory from 512Mi to 1Gi',
    progress: 0
  },
  {
    action: 'Rolling out configuration',
    description: 'Applying new configuration to cluster',
    progress: 0
  },
  {
    action: 'Verifying pod health',
    description: 'Checking pod status and readiness',
    progress: 0
  },
  {
    action: 'Updating incident status',
    description: 'Marking incident as resolved in PagerDuty',
    progress: 0
  }
];

export const DEMO_FINDINGS = {
  rootCause: 'Memory leak in payment processing service causing OOM kills',
  affectedComponents: ['payment-service pods', 'transaction processing'],
  impact: 'Customer payment failures and service degradation',
  solution: 'Restart pods and increase memory allocation to prevent future OOM kills'
};