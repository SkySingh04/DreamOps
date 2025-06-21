'use client';

import { useState, useEffect } from 'react';
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

// MCP Integration interface
interface MCPIntegration {
  name: string;
  capabilities: string[];
  connected: boolean;
}

// MCP Integration configurations
const MCP_INTEGRATION_CONFIGS = {
  kubernetes: {
    icon: Cloud,
    color: 'blue',
    description: 'Connect to Kubernetes clusters for pod and service management',
  },
  github: {
    icon: GitBranch,
    color: 'purple',
    description: 'GitHub integration for repository monitoring and issue tracking',
  },
  notion: {
    icon: FileText,
    color: 'gray',
    description: 'Notion integration for incident documentation and knowledge management',
  },
  grafana: {
    icon: BarChart3,
    color: 'green',
    description: 'Grafana integration for metrics visualization and alerting',
  },
};

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
  const [isLiveMode, setIsLiveMode] = useState(true);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());
  const queryClient = useQueryClient();

  // Fetch integrations
  const { data: integrationsData, isLoading } = useQuery({
    queryKey: queryKeys.integrations,
    queryFn: () => apiClient.getIntegrations(),
  });

  // Fetch MCP integrations with real-time updates
  const { data: mcpIntegrationsData, isLoading: mcpLoading, refetch: refetchMCP, dataUpdatedAt, isFetching } = useQuery({
    queryKey: ['mcp-integrations'],
    queryFn: () => apiClient.getMCPIntegrations(),
    refetchInterval: isLiveMode ? 1500 : false, // Refresh every 1.5 seconds when live mode is on
    refetchIntervalInBackground: true, // Keep fetching even when tab is not active
    refetchOnWindowFocus: true, // Refetch when user comes back to tab
    refetchOnMount: true, // Refetch when component mounts
    staleTime: 0, // Always consider data stale to ensure fresh data
    refetchOnReconnect: true, // Refetch when network reconnects
  });

  // Track when data updates for live indicators
  useEffect(() => {
    if (dataUpdatedAt) {
      setLastUpdateTime(new Date(dataUpdatedAt));
    }
  }, [dataUpdatedAt]);

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
  const mcpIntegrations = mcpIntegrationsData?.data?.integrations || [];

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

  // MCP Integration Card Component with live indicators
  const MCPIntegrationCard = ({ integration }: { integration: MCPIntegration }) => {
    const config = MCP_INTEGRATION_CONFIGS[integration.name as keyof typeof MCP_INTEGRATION_CONFIGS];
    const Icon = config?.icon || Terminal;
    
    return (
      <Card className={`hover:shadow-md transition-all duration-300 ${integration.connected ? 'ring-1 ring-green-200' : 'ring-1 ring-red-200'}`}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg relative ${integration.connected ? 'bg-green-100' : 'bg-gray-100'}`}>
                <Icon size={24} className={integration.connected ? 'text-green-600' : 'text-gray-600'} />
                {/* Live indicator pulse */}
                {integration.connected && isLiveMode && (
                  <div className="absolute -top-1 -right-1 h-3 w-3 bg-green-500 rounded-full animate-pulse">
                    <div className="absolute inset-0 bg-green-500 rounded-full animate-ping opacity-75"></div>
                  </div>
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-lg capitalize">{integration.name}</CardTitle>
                  {isFetching && (
                    <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                  )}
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {config?.description || `${integration.name.charAt(0).toUpperCase() + integration.name.slice(1)} MCP integration`}
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-1">
              {integration.connected ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
              {/* Live status indicator */}
              <div className="flex items-center gap-1">
                <div className={`h-2 w-2 rounded-full ${integration.connected ? 'bg-green-500' : 'bg-red-500'} ${isLiveMode && integration.connected ? 'animate-pulse' : ''}`}></div>
                <span className="text-xs text-gray-400">LIVE</span>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <div className="space-y-4">
            {/* Status with live indicator */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge 
                  variant="outline" 
                  className={`${integration.connected ? 'bg-green-100 text-green-800 border-green-300' : 'bg-red-100 text-red-800 border-red-300'} transition-colors duration-300`}
                >
                  {integration.connected ? 'Connected' : 'Disconnected'}
                </Badge>
                {isLiveMode && (
                  <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-800">
                    LIVE
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetchMCP()}
                  className="h-7 px-2"
                  disabled={isFetching}
                >
                  <RefreshCw className={`h-3 w-3 ${isFetching ? 'animate-spin' : ''}`} />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsLiveMode(!isLiveMode)}
                  className={`h-7 px-2 ${isLiveMode ? 'bg-green-50 text-green-700' : 'bg-gray-50'}`}
                >
                  <Activity className="h-3 w-3" />
                </Button>
              </div>
            </div>

            {/* Capabilities */}
            {integration.capabilities && integration.capabilities.length > 0 && (
              <div>
                <div className="text-sm font-medium mb-2">Capabilities:</div>
                <div className="flex flex-wrap gap-1">
                  {integration.capabilities.slice(0, 3).map((capability, index) => (
                    <Badge key={index} variant="secondary" className="text-xs">
                      {capability}
                    </Badge>
                  ))}
                  {integration.capabilities.length > 3 && (
                    <Badge variant="secondary" className="text-xs">
                      +{integration.capabilities.length - 3} more
                    </Badge>
                  )}
                </div>
              </div>
            )}

            {/* Connection Details with live timestamps */}
            <div className="text-xs text-gray-500 space-y-1">
              <div className="flex items-center justify-between">
                <span>Status: {integration.connected ? 'Healthy' : 'Connection failed'}</span>
                {integration.connected && isLiveMode && (
                  <div className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-green-600">Live</span>
                  </div>
                )}
              </div>
              <div>Type: MCP Integration</div>
              <div>Total Capabilities: {integration.capabilities.length}</div>
              <div className="flex items-center justify-between">
                <span>Last Updated:</span>
                <span className="font-mono">{format(lastUpdateTime, 'HH:mm:ss')}</span>
              </div>
              {isFetching && (
                <div className="text-blue-500 flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Refreshing...</span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

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

  if (isLoading || mcpLoading) {
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
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">Integrations</h1>
            {isLiveMode && (
              <div className="flex items-center gap-2 px-2 py-1 bg-green-100 rounded-full">
                <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-medium text-green-700">LIVE</span>
              </div>
            )}
            {isFetching && (
              <div className="flex items-center gap-2 px-2 py-1 bg-blue-100 rounded-full">
                <Loader2 className="h-3 w-3 animate-spin text-blue-600" />
                <span className="text-xs font-medium text-blue-700">Updating...</span>
              </div>
            )}
          </div>
          <p className="text-gray-600 mt-1">
            Connect external services to enhance monitoring and incident response
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Last updated: {format(lastUpdateTime, 'MMM dd, HH:mm:ss')} • 
            Next update: {isLiveMode ? 'in 1.5s' : 'manual'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setIsLiveMode(!isLiveMode)}
            variant={isLiveMode ? "default" : "outline"}
            className={isLiveMode ? "bg-green-600 hover:bg-green-700" : ""}
          >
            <Activity className="h-4 w-4 mr-2" />
            {isLiveMode ? 'Live Mode ON' : 'Live Mode OFF'}
          </Button>
          <Button 
            onClick={() => refetchMCP()}
            disabled={isFetching}
            variant="outline"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <Tabs defaultValue="mcp" className="space-y-6">
        <TabsList>
          <TabsTrigger value="mcp">
            MCP Integrations ({mcpIntegrations.length})
          </TabsTrigger>
          <TabsTrigger value="standard">
            Standard Integrations ({integrations.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="mcp" className="space-y-6">
          {/* MCP Integration Health Summary */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    MCP Integration Status
                    {isLiveMode && (
                      <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                    )}
                  </CardTitle>
                  <CardDescription>
                    Model Context Protocol integrations for AI-powered incident response
                  </CardDescription>
                </div>
                {isFetching && (
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-4">
                <div className={`text-center p-4 rounded-lg transition-all duration-300 ${mcpIntegrations.filter(i => i.connected).length > 0 ? 'bg-green-50 ring-1 ring-green-200' : 'bg-green-50'}`}>
                  <div className={`text-2xl font-bold text-green-600 ${isFetching ? 'animate-pulse' : ''}`}>
                    {mcpIntegrations.filter(i => i.connected).length}
                  </div>
                  <div className="text-sm text-green-700 flex items-center justify-center gap-1">
                    Connected
                    {isLiveMode && mcpIntegrations.filter(i => i.connected).length > 0 && (
                      <div className="h-1 w-1 bg-green-500 rounded-full animate-pulse"></div>
                    )}
                  </div>
                </div>
                <div className={`text-center p-4 rounded-lg transition-all duration-300 ${mcpIntegrations.filter(i => !i.connected).length > 0 ? 'bg-red-50 ring-1 ring-red-200' : 'bg-red-50'}`}>
                  <div className={`text-2xl font-bold text-red-600 ${isFetching ? 'animate-pulse' : ''}`}>
                    {mcpIntegrations.filter(i => !i.connected).length}
                  </div>
                  <div className="text-sm text-red-700">Disconnected</div>
                </div>
                <div className={`text-center p-4 bg-blue-50 rounded-lg transition-all duration-300 ${isFetching ? 'ring-1 ring-blue-200' : ''}`}>
                  <div className={`text-2xl font-bold text-blue-600 ${isFetching ? 'animate-pulse' : ''}`}>
                    {mcpIntegrations.length}
                  </div>
                  <div className="text-sm text-blue-700">Total</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg transition-all duration-300">
                  <div className={`text-2xl font-bold text-purple-600 ${isFetching ? 'animate-pulse' : ''}`}>
                    {mcpIntegrations.reduce((acc, i) => acc + i.capabilities.length, 0)}
                  </div>
                  <div className="text-sm text-purple-700">Capabilities</div>
                </div>
              </div>
              {isLiveMode && (
                <div className="mt-4 text-center">
                  <p className="text-xs text-gray-500">
                    🔴 Live monitoring • Updates every 1.5 seconds • Last: {format(lastUpdateTime, 'HH:mm:ss')}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* MCP Integrations Grid */}
          {mcpIntegrations.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {mcpIntegrations.map((integration) => (
                <MCPIntegrationCard key={integration.name} integration={integration} />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Terminal className="h-12 w-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No MCP Integrations</h3>
                <p className="text-gray-500 text-center">
                  The backend agent is not running or no MCP integrations are configured.
                  <br />
                  Start the backend server to see available integrations.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="standard" className="space-y-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-medium">Standard Integrations</h3>
              <p className="text-sm text-gray-500">Traditional service integrations</p>
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

          {/* Standard Integration Health Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Standard Integration Health</CardTitle>
              <CardDescription>Overview of all standard integration statuses</CardDescription>
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
        </TabsContent>
      </Tabs>

      {/* Configuration Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Standard Integration</DialogTitle>
            <DialogDescription>
              Choose a standard integration to connect to your infrastructure.
              MCP integrations are automatically detected when the backend agent is running.
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
            <Button variant="outline" onClick={() => toast.info('PagerDuty integration setup')}>
              <Bell className="h-4 w-4 mr-2" />
              PagerDuty
            </Button>
          </div>

          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>MCP Integrations</AlertTitle>
            <AlertDescription>
              MCP (Model Context Protocol) integrations like Kubernetes, GitHub, Notion, and Grafana 
              are automatically detected when your backend agent is running with the proper configuration.
            </AlertDescription>
          </Alert>

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