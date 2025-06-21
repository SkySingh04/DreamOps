'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
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
  Settings,
  RefreshCw,
  TestTube,
  Link,
  Unlink,
  Activity,
  Clock,
  Zap,
  Shield,
  Key,
  Globe,
  Terminal,
  Loader2,
  Info,
  MessageSquare
} from 'lucide-react';
import { toast } from 'sonner';
import { apiClient, queryKeys } from '@/lib/api-client';
import { Integration } from '@/lib/types';
import { format } from 'date-fns';

const INTEGRATION_CONFIGS = {
  kubernetes: {
    icon: Cloud,
    color: 'blue',
    fields: [
      { key: 'cluster_endpoint', label: 'Cluster Endpoint', type: 'text', required: true },
      { key: 'namespace', label: 'Default Namespace', type: 'text', default: 'default' },
      { key: 'auth_method', label: 'Authentication Method', type: 'select', options: ['kubeconfig', 'service-account', 'oidc'] },
      { key: 'enable_destructive', label: 'Enable Destructive Operations', type: 'boolean', default: false },
    ],
  },
  pagerduty: {
    icon: Bell,
    color: 'red',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', required: true },
      { key: 'webhook_secret', label: 'Webhook Secret', type: 'password' },
      { key: 'routing_key', label: 'Default Routing Key', type: 'text' },
      { key: 'auto_acknowledge', label: 'Auto-acknowledge incidents', type: 'boolean', default: false },
    ],
  },
  github: {
    icon: GitBranch,
    color: 'purple',
    fields: [
      { key: 'token', label: 'Personal Access Token', type: 'password', required: true },
      { key: 'organization', label: 'Organization', type: 'text' },
      { key: 'repository_filter', label: 'Repository Filter (regex)', type: 'text' },
      { key: 'enable_issue_creation', label: 'Enable Issue Creation', type: 'boolean', default: true },
    ],
  },
  grafana: {
    icon: BarChart3,
    color: 'green',
    fields: [
      { key: 'url', label: 'Grafana URL', type: 'text', required: true },
      { key: 'api_key', label: 'API Key', type: 'password', required: true },
      { key: 'default_dashboard', label: 'Default Dashboard UID', type: 'text' },
      { key: 'alert_notification_channel', label: 'Alert Notification Channel', type: 'text' },
    ],
  },
  datadog: {
    icon: Database,
    color: 'purple',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', required: true },
      { key: 'app_key', label: 'Application Key', type: 'password', required: true },
      { key: 'site', label: 'Datadog Site', type: 'select', options: ['datadoghq.com', 'datadoghq.eu', 'ddog-gov.com'] },
      { key: 'log_index', label: 'Log Index', type: 'text', default: 'main' },
    ],
  },
  notion: {
    icon: FileText,
    color: 'gray',
    fields: [
      { key: 'token', label: 'Integration Token', type: 'password', required: true },
      { key: 'database_id', label: 'Incident Database ID', type: 'text' },
      { key: 'page_template_id', label: 'Page Template ID', type: 'text' },
      { key: 'auto_document', label: 'Auto-document incidents', type: 'boolean', default: true },
    ],
  },
  slack: {
    icon: MessageSquare,
    color: 'pink',
    fields: [
      { key: 'bot_token', label: 'Bot User OAuth Token', type: 'password', required: true },
      { key: 'channel_id', label: 'Default Channel ID', type: 'text', required: true },
      { key: 'webhook_url', label: 'Incoming Webhook URL', type: 'text' },
      { key: 'notification_level', label: 'Notification Level', type: 'select', options: ['all', 'critical', 'high', 'custom'] },
    ],
  },
};

export default function IntegrationsPage() {
  const [selectedIntegration, setSelectedIntegration] = useState<Integration | null>(null);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [testingIntegration, setTestingIntegration] = useState<string | null>(null);
  const [configValues, setConfigValues] = useState<Record<string, any>>({});
  const queryClient = useQueryClient();

  // Fetch integrations
  const { data: integrationsData, isLoading } = useQuery({
    queryKey: queryKeys.integrations,
    queryFn: () => apiClient.getIntegrations(),
  });

  // Mutations
  const testIntegrationMutation = useMutation({
    mutationFn: (id: string) => apiClient.testIntegration(id),
    onSuccess: (data, id) => {
      if (data.data?.success) {
        toast.success(`${id} connection test successful`);
      } else {
        toast.error(`${id} connection test failed: ${data.data?.message}`);
      }
      setTestingIntegration(null);
    },
    onError: () => {
      toast.error('Connection test failed');
      setTestingIntegration(null);
    },
  });

  const updateConfigMutation = useMutation({
    mutationFn: ({ id, config }: { id: string; config: Record<string, any> }) =>
      apiClient.updateIntegrationConfig(id, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations });
      toast.success('Integration configuration updated');
      setShowConfigDialog(false);
    },
  });

  const toggleIntegrationMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      apiClient.toggleIntegration(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations });
    },
  });

  const integrations = integrationsData?.data || [];

  // Add mock data for integrations not returned by API
  const allIntegrations: Integration[] = [
    ...integrations,
    ...Object.entries(INTEGRATION_CONFIGS)
      .filter(([id]) => !integrations.find(i => i.id === id))
      .map(([id, config]) => ({
        id,
        name: id.charAt(0).toUpperCase() + id.slice(1),
        description: `Connect to ${id.charAt(0).toUpperCase() + id.slice(1)} for enhanced monitoring`,
        status: 'pending' as const,
        enabled: false,
      })),
  ];

  const getIntegrationConfig = (id: string) => INTEGRATION_CONFIGS[id as keyof typeof INTEGRATION_CONFIGS];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'bg-green-100 text-green-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      case 'pending':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      case 'disconnected':
        return <Unlink className="h-5 w-5 text-gray-600" />;
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
      case 'disconnected':
        return <Badge className="bg-gray-100 text-gray-800">Disconnected</Badge>;
      default:
        return null;
    }
  };

  const handleConfigure = (integration: Integration) => {
    setSelectedIntegration(integration);
    setConfigValues(integration.config || {});
    setShowConfigDialog(true);
  };

  const handleTest = (integrationId: string) => {
    setTestingIntegration(integrationId);
    testIntegrationMutation.mutate(integrationId);
  };

  const handleSaveConfig = () => {
    if (selectedIntegration) {
      updateConfigMutation.mutate({
        id: selectedIntegration.id,
        config: configValues,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 p-4 lg:p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-64 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Integrations</h1>
          <p className="text-gray-600 mt-1">
            Connect external services to enhance monitoring and incident response
          </p>
        </div>
        <Button onClick={() => setShowConfigDialog(true)}>
          <Settings className="h-4 w-4 mr-2" />
          Add Integration
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {integrations.map((integration) => {
          const config = getIntegrationConfig(integration.id);
          const Icon = config?.icon;
          return (
            <Card key={integration.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 rounded-lg">
                      {Icon && <Icon size={24} />}
                    </div>
                    <div>
                      <CardTitle className="text-lg">{integration.name}</CardTitle>
                      <p className="text-sm text-gray-500 mt-1">{integration.description}</p>
                    </div>
                  </div>
                  {getStatusIcon(integration.status)}
                </div>
              </CardHeader>

              <CardContent>
                <div className="space-y-4">
                  {/* Status and Last Sync */}
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className={getStatusColor(integration.status)}>
                      {integration.status}
                    </Badge>
                    <span className="text-xs text-gray-500">
                      Last sync: {integration.last_sync}
                    </span>
                  </div>

                  {/* Error Message */}
                  {integration.error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription className="text-sm">
                        {integration.error}
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Metrics */}
                  {integration.metrics && Object.keys(integration.metrics).length > 0 && (
                    <div className="grid grid-cols-3 gap-2 text-center">
                      {Object.entries(integration.metrics).map(([key, value]) => (
                        <div key={key} className="p-2 bg-gray-50 rounded">
                          <div className="text-lg font-semibold">{value as number}</div>
                          <div className="text-xs text-gray-500 capitalize">{key}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTest(integration.id)}
                      disabled={testingIntegration === integration.id}
                      className="flex-1"
                    >
                      {testingIntegration === integration.id ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <TestTube className="h-4 w-4 mr-2" />
                      )}
                      Test
                    </Button>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleConfigure(integration)}
                      className="flex-1"
                    >
                      <Settings className="h-4 w-4 mr-2" />
                      Configure
                    </Button>
                  </div>

                  {/* Enable/Disable Toggle */}
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Enable Integration</span>
                    <Switch
                      checked={integration.enabled}
                      onCheckedChange={(checked) => toggleIntegrationMutation.mutate({
                        id: integration.id,
                        enabled: checked
                      })}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Integration Health Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Integration Health</CardTitle>
          <CardDescription>Overview of all integration statuses</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                {integrations.filter(i => i.status === 'connected').length}
              </div>
              <div className="text-sm text-green-700">Connected</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <div className="text-2xl font-bold text-red-600">
                {integrations.filter(i => i.status === 'error').length}
              </div>
              <div className="text-sm text-red-700">Errors</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">
                {integrations.filter(i => i.status === 'pending').length}
              </div>
              <div className="text-sm text-yellow-700">Pending</div>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {integrations.filter(i => i.enabled).length}
              </div>
              <div className="text-sm text-blue-700">Enabled</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Integration</DialogTitle>
            <DialogDescription>
              Choose an integration to connect to your infrastructure
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-3">
            <Button variant="outline" onClick={() => toast.info('Slack integration setup')}>
              <MessageSquare className="h-4 w-4 mr-2" />
              Slack
            </Button>
            <Button variant="outline" onClick={() => toast.info('Prometheus integration setup')}>
              <Activity className="h-4 w-4 mr-2" />
              Prometheus
            </Button>
            <Button variant="outline" onClick={() => toast.info('AWS integration setup')}>
              <Cloud className="h-4 w-4 mr-2" />
              AWS CloudWatch
            </Button>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}