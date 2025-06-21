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

  return (
    <section className="flex-1 p-4 lg:p-8">
      <div className="mb-6">
        <h1 className="text-lg lg:text-2xl font-medium mb-2">Integrations</h1>
        <p className="text-muted-foreground">
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
      <div>
        <h1 className="text-2xl font-bold">Integrations</h1>
        <p className="text-muted-foreground mt-1">
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
                      {Icon && <Icon size={24} />}
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
      {/* Integration Health Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Total Integrations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{allIntegrations.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Connected</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {allIntegrations.filter(i => i.status === 'connected').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Errors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {allIntegrations.filter(i => i.status === 'error').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">API Calls (24h)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12.5k</div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All Integrations</TabsTrigger>
          <TabsTrigger value="monitoring">Monitoring</TabsTrigger>
          <TabsTrigger value="incident">Incident Management</TabsTrigger>
          <TabsTrigger value="communication">Communication</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {allIntegrations.map((integration) => {
              const config = getIntegrationConfig(integration.id);
              const Icon = config?.icon || Globe;
              const isLoading = testingIntegration === integration.id;
              
              return (
                <Card key={integration.id} className="relative overflow-hidden">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 bg-${config?.color || 'gray'}-100 rounded-lg`}>
                          {Icon && <Icon size={24} />}
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
                        onCheckedChange={(checked) => 
                          toggleIntegrationMutation.mutate({ 
                            id: integration.id, 
                            enabled: checked 
                          })
                        }
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
                        {integration.last_sync && (
                          <span className="text-sm text-muted-foreground">
                            {format(new Date(integration.last_sync), 'MMM d, HH:mm')}
                          </span>
                        )}
                      </div>

                      {integration.error && (
                        <Alert variant="destructive">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription className="text-xs">
                            {integration.error}
                          </AlertDescription>
                        </Alert>
                      )}

                      {integration.health_data && (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Latency</span>
                            <span className="font-medium">{integration.health_data.latency_ms}ms</span>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Success Rate</span>
                            <span className="font-medium">{integration.health_data.success_rate}%</span>
                          </div>
                          <Progress value={integration.health_data.success_rate} className="h-2" />
                        </div>
                      )}

                      {integration.status === 'connected' && integration.metrics && Object.keys(integration.metrics).length > 0 && (
                        <div className="grid grid-cols-3 gap-2 pt-2 border-t">
                          {Object.entries(integration.metrics).slice(0, 3).map(([key, value]) => (
                            <div key={key} className="text-center">
                              <p className="text-2xl font-semibold">{value}</p>
                              <p className="text-xs text-muted-foreground capitalize">{key}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="flex gap-2">
                        <Button 
                          className="flex-1" 
                          variant={integration.status === 'connected' ? 'outline' : 'default'}
                          onClick={() => handleConfigure(integration)}
                        >
                          <Settings className="h-4 w-4 mr-2" />
                          Configure
                        </Button>
                        {integration.status === 'connected' && (
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => handleTest(integration.id)}
                            disabled={isLoading}
                          >
                            {isLoading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <TestTube className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="monitoring">
          <div className="text-center py-12 text-muted-foreground">
            <Activity className="h-12 w-12 mx-auto mb-4" />
            <p>Monitoring integrations would be shown here</p>
          </div>
        </TabsContent>

        <TabsContent value="incident">
          <div className="text-center py-12 text-muted-foreground">
            <AlertCircle className="h-12 w-12 mx-auto mb-4" />
            <p>Incident management integrations would be shown here</p>
          </div>
        </TabsContent>

        <TabsContent value="communication">
          <div className="text-center py-12 text-muted-foreground">
            <MessageSquare className="h-12 w-12 mx-auto mb-4" />
            <p>Communication integrations would be shown here</p>
          </div>
        </TabsContent>
      </Tabs>

      {/* Configuration Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Configure {selectedIntegration?.name}</DialogTitle>
            <DialogDescription>
              Update the configuration settings for this integration
            </DialogDescription>
          </DialogHeader>
          {selectedIntegration && (
            <div className="space-y-4 py-4">
              {getIntegrationConfig(selectedIntegration.id)?.fields.map((field) => (
                <div key={field.key} className="space-y-2">
                  <Label htmlFor={field.key}>
                    {field.label}
                    {field.required && <span className="text-red-500 ml-1">*</span>}
                  </Label>
                  {field.type === 'text' || field.type === 'password' ? (
                    <Input
                      id={field.key}
                      type={field.type}
                      value={configValues[field.key] || field.default || ''}
                      onChange={(e) => setConfigValues({
                        ...configValues,
                        [field.key]: e.target.value,
                      })}
                      placeholder={field.label}
                    />
                  ) : field.type === 'boolean' ? (
                    <Switch
                      id={field.key}
                      checked={configValues[field.key] ?? field.default ?? false}
                      onCheckedChange={(checked) => setConfigValues({
                        ...configValues,
                        [field.key]: checked,
                      })}
                    />
                  ) : field.type === 'select' ? (
                    <Select
                      value={configValues[field.key] || field.default || ''}
                      onValueChange={(value) => setConfigValues({
                        ...configValues,
                        [field.key]: value,
                      })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={`Select ${field.label}`} />
                      </SelectTrigger>
                      <SelectContent>
                        {field.options?.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : null}
                </div>
              ))}
              
              {selectedIntegration.status === 'connected' && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    This integration is currently connected. Changes will take effect immediately.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveConfig} disabled={updateConfigMutation.isPending}>
              {updateConfigMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Configuration'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}