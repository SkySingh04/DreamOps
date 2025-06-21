'use client';

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { 
  Cloud, 
  Database, 
  GitBranch, 
  BarChart3, 
  Bell, 
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Settings
} from 'lucide-react';

export default function IntegrationsPage() {
  // Mock integration data
  const integrations = [
    {
      id: 'kubernetes',
      name: 'Kubernetes',
      description: 'Monitor and manage Kubernetes clusters',
      icon: Cloud,
      status: 'connected',
      enabled: true,
      lastSync: '2 minutes ago',
      metrics: {
        pods: 42,
        nodes: 5,
        namespaces: 8
      }
    },
    {
      id: 'grafana',
      name: 'Grafana',
      description: 'Visualize metrics and create dashboards',
      icon: BarChart3,
      status: 'connected',
      enabled: true,
      lastSync: '5 minutes ago',
      metrics: {
        dashboards: 15,
        alerts: 23,
        datasources: 4
      }
    },
    {
      id: 'datadog',
      name: 'Datadog',
      description: 'Monitor application performance and logs',
      icon: Database,
      status: 'pending',
      enabled: false,
      lastSync: 'Never',
      metrics: {}
    },
    {
      id: 'github',
      name: 'GitHub',
      description: 'Track deployments and code changes',
      icon: GitBranch,
      status: 'error',
      enabled: true,
      lastSync: '1 hour ago',
      error: 'Invalid authentication token'
    },
    {
      id: 'pagerduty',
      name: 'PagerDuty',
      description: 'Incident management and alerting',
      icon: Bell,
      status: 'connected',
      enabled: true,
      lastSync: '30 seconds ago',
      metrics: {
        incidents: 3,
        escalations: 1,
        services: 12
      }
    },
    {
      id: 'notion',
      name: 'Notion',
      description: 'Document incidents and runbooks',
      icon: FileText,
      status: 'pending',
      enabled: false,
      lastSync: 'Never',
      metrics: {}
    }
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'pending':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'connected':
        return <Badge className="bg-green-100 text-green-800">Connected</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-800">Error</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">Not Connected</Badge>;
      default:
        return null;
    }
  };

  return (
    <section className="flex-1 p-4 lg:p-8">
      <div className="mb-6">
        <h1 className="text-lg lg:text-2xl font-medium mb-2">Integrations</h1>
        <p className="text-muted-foreground">
          Connect your tools to enable AI-powered incident response
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {integrations.map((integration) => {
          const Icon = integration.icon;
          return (
            <Card key={integration.id} className="relative">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 rounded-lg">
                      <Icon className="h-6 w-6" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{integration.name}</CardTitle>
                      <CardDescription className="text-sm mt-1">
                        {integration.description}
                      </CardDescription>
                    </div>
                  </div>
                  <Switch 
                    checked={integration.enabled}
                    disabled={integration.status === 'pending'}
                  />
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(integration.status)}
                      {getStatusBadge(integration.status)}
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {integration.lastSync}
                    </span>
                  </div>

                  {integration.error && (
                    <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                      {integration.error}
                    </div>
                  )}

                  {integration.status === 'connected' && Object.keys(integration.metrics).length > 0 && (
                    <div className="grid grid-cols-3 gap-2 pt-2 border-t">
                      {Object.entries(integration.metrics).map(([key, value]) => (
                        <div key={key} className="text-center">
                          <p className="text-2xl font-semibold">{value}</p>
                          <p className="text-xs text-muted-foreground capitalize">{key}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  <Button 
                    className="w-full" 
                    variant={integration.status === 'connected' ? 'outline' : 'default'}
                  >
                    {integration.status === 'connected' ? (
                      <>
                        <Settings className="h-4 w-4 mr-2" />
                        Configure
                      </>
                    ) : (
                      'Connect'
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}