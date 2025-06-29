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
  MessageSquare,
  Plus,
  ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';
import { apiClient, queryKeys } from '@/lib/api-client';
import { Integration, IntegrationStatus } from '@/lib/types';
import { format } from 'date-fns';
import { useDemoIntegrations } from '@/components/demo/DemoIntegrationsData';

// Extended Integration interface for the integrations page
interface ExtendedIntegration extends Integration {
  type: string;
  capabilities: string[];
}

// Integration type definitions
interface MCPIntegration {
  name: string;
  display_name?: string;
  description?: string;
  capabilities: Record<string, any> | string[];
  connected: boolean;
  configured?: boolean;
}

interface IntegrationHealth {
  name: string;
  status: IntegrationStatus;
  last_check: string;
  metrics?: Record<string, any>;
}

interface AvailableIntegration {
  type: string;
  name: string;
  description: string;
  category: string;
  required: boolean;
  setup_difficulty: 'easy' | 'medium' | 'hard';
  documentation_url: string;
  status?: 'available' | 'coming_soon';
}

const INTEGRATION_ICONS: Record<string, React.ComponentType<any>> = {
  kubernetes: Cloud,
  github: GitBranch,
  pagerduty: Bell,
  datadog: Database,
  grafana: BarChart3,
  notion: FileText,
  slack: MessageSquare,
  prometheus: Activity,
  jira: FileText,
  opsgenie: Bell,
  aws: Cloud,
};

const INTEGRATION_COLORS: Record<string, string> = {
  kubernetes: 'blue',
  github: 'purple',
  pagerduty: 'red',
  datadog: 'purple',
  grafana: 'green',
  notion: 'gray',
  slack: 'pink',
  prometheus: 'orange',
  jira: 'blue',
  opsgenie: 'red',
  aws: 'orange',
};

export default function IntegrationsPage() {
  const [selectedIntegration, setSelectedIntegration] = useState<ExtendedIntegration | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [testingIntegration, setTestingIntegration] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const queryClient = useQueryClient();

  // Fetch MCP integrations (real-time status)
  const { data: mcpIntegrations = [], isLoading: mcpLoading } = useQuery({
    queryKey: queryKeys.mcpIntegrations,
    queryFn: async () => {
      try {
        const response = await apiClient.get('/integrations');
        return response.data?.integrations || [];
      } catch (error) {
        console.error('Failed to fetch MCP integrations:', error);
        return [];
      }
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch team integrations
  const { data: teamIntegrationsData, isLoading: teamLoading } = useQuery({
    queryKey: queryKeys.integrations,
    queryFn: () => apiClient.getIntegrations(),
  });

  // Use demo data when demo mode is active
  const demoMcpIntegrations = useDemoIntegrations(mcpIntegrations);

  // Fetch available integrations
  const { data: availableIntegrations = [] } = useQuery({
    queryKey: queryKeys.availableIntegrations,
    queryFn: async () => {
      try {
        const response = await apiClient.get('/api/v1/integrations/available');
        return response.data?.integrations || [];
      } catch (error) {
        console.error('Failed to fetch available integrations:', error);
        return [];
      }
    },
  });

  // Combine MCP and team integrations
  const allIntegrations: ExtendedIntegration[] = [
    // Add MCP integrations only - these are the main integrations we want to show
    // Team integrations are hidden to avoid duplicates since MCP integrations provide the same functionality
    ...(demoMcpIntegrations?.data || demoMcpIntegrations || []).map((mcp: MCPIntegration): ExtendedIntegration => ({
      id: mcp.name || 'unknown',
      name: mcp.display_name || (mcp.name ? (mcp.name.charAt(0).toUpperCase() + mcp.name.slice(1)) : 'Unknown Integration'),
      description: mcp.description || (mcp.name ? `${mcp.name.charAt(0).toUpperCase() + mcp.name.slice(1)} Integration` : 'Unknown Integration'),
      type: mcp.name || 'unknown',
      status: mcp.connected ? 'connected' : (mcp.configured === false ? 'not_configured' : 'disconnected'),
      enabled: mcp.connected,
      capabilities: Array.isArray(mcp.capabilities) ? mcp.capabilities : Object.keys(mcp.capabilities || {}),
      last_sync: new Date().toISOString(),
    })),
    // Temporarily hide team integrations to avoid duplicates
    // ...(teamIntegrationsData?.data || [])
    //   .filter((integration: Integration) => {
    //     // Create a mapping of MCP integration names to their base names
    //     const mcpNameMapping: Record<string, string> = {};
    //     mcpIntegrations.forEach((mcp: MCPIntegration) => {
    //       const baseName = mcp.name.replace('_mcp', ''); // Remove _mcp suffix
    //       mcpNameMapping[mcp.name] = baseName;
    //       mcpNameMapping[baseName] = baseName;
    //     });
        
    //     // Check if this team integration has an MCP equivalent
    //     const teamIntegrationName = integration.id;
    //     const hasMcpEquivalent = Object.values(mcpNameMapping).includes(teamIntegrationName) ||
    //                             Object.keys(mcpNameMapping).includes(teamIntegrationName);
        
    //     // Debug logging
    //     console.log(`Team integration: ${teamIntegrationName}, Has MCP equivalent: ${hasMcpEquivalent}`);
        
    //     return !hasMcpEquivalent;
    //   })
    //   .map((integration: Integration): ExtendedIntegration => ({
    //     ...integration,
    //     type: integration.id, // Use id as type for team integrations
    //     capabilities: [], // Default empty capabilities for team integrations
    //   })),
  ];

  // Calculate dynamic metrics
  const connectedCount = allIntegrations.filter(i => i.status === 'connected').length;
  const errorCount = allIntegrations.filter(i => i.status === 'error').length;
  const pendingCount = allIntegrations.filter(i => i.status === 'pending').length;
  const notConfiguredCount = allIntegrations.filter(i => i.status === 'not_configured').length;
  const enabledCount = allIntegrations.filter(i => i.enabled).length;
  const totalCount = allIntegrations.length;

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
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations });
    },
    onError: () => {
      toast.error('Connection test failed');
      setTestingIntegration(null);
    },
  });

  const toggleIntegrationMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      apiClient.toggleIntegration(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations });
      toast.success('Integration status updated');
    },
  });

  const refreshIntegrations = async () => {
    setRefreshing(true);
    try {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.integrations }),
        queryClient.invalidateQueries({ queryKey: queryKeys.mcpIntegrations }),
      ]);
      toast.success('Integrations refreshed');
    } catch (error) {
      toast.error('Failed to refresh integrations');
    } finally {
      setRefreshing(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'disconnected':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'not_configured':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
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
      case 'not_configured':
        return <Settings className="h-5 w-5 text-orange-600" />;
      default:
        return <Unlink className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'connected':
        return <Badge className="bg-green-100 text-green-800">Connected</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-800">Error</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">Pending</Badge>;
      case 'disconnected':
        return <Badge className="bg-gray-100 text-gray-800">Disconnected</Badge>;
      case 'not_configured':
        return <Badge className="bg-orange-100 text-orange-800">Not Configured</Badge>;
      default:
        return <Badge className="bg-gray-100 text-gray-800">Unknown</Badge>;
    }
  };

  const handleTest = (integrationId: string) => {
    setTestingIntegration(integrationId);
    testIntegrationMutation.mutate(integrationId);
  };

  const handleConfigure = (integration: ExtendedIntegration) => {
    if (integration.type === 'kubernetes') {
      window.location.href = '/integrations/kubernetes';
    } else {
      toast.info(`${integration.name} configuration coming soon`);
    }
  };

  const isLoading = mcpLoading || teamLoading;

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
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={refreshIntegrations}
            disabled={refreshing}
          >
            {refreshing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Refresh
          </Button>
          <Button onClick={() => setShowAddDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Integration
          </Button>
        </div>
      </div>

      {/* Integration Health Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Integration Health</CardTitle>
          <CardDescription>Overview of all integration statuses</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="text-center p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="text-2xl font-bold text-green-600">
                {connectedCount}
              </div>
              <div className="text-sm text-green-700">Connected</div>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg border border-red-200">
              <div className="text-2xl font-bold text-red-600">
                {errorCount}
              </div>
              <div className="text-sm text-red-700">Errors</div>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <div className="text-2xl font-bold text-yellow-600">
                {pendingCount}
              </div>
              <div className="text-sm text-yellow-700">Pending</div>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded-lg border border-orange-200">
              <div className="text-2xl font-bold text-orange-600">
                {notConfiguredCount}
              </div>
              <div className="text-sm text-orange-700">Not Configured</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Integrations Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {allIntegrations.map((integration) => {
          const IconComponent = INTEGRATION_ICONS[integration.type] || Settings;
          const color = INTEGRATION_COLORS[integration.type] || 'gray';
          
          return (
            <Card key={integration.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 bg-${color}-100 rounded-lg`}>
                      <IconComponent className={`h-6 w-6 text-${color}-600`} />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{integration.name}</CardTitle>
                      <p className="text-sm text-gray-500 mt-1">
                        {integration.type ? (integration.type.charAt(0).toUpperCase() + integration.type.slice(1)) : 'Unknown'} Integration
                      </p>
                    </div>
                  </div>
                  {getStatusIcon(integration.status)}
                </div>
              </CardHeader>

              <CardContent>
                <div className="space-y-4">
                  {/* Status and Last Sync */}
                  <div className="flex items-center justify-between">
                    {getStatusBadge(integration.status)}
                    <span className="text-xs text-gray-500">
                      {integration.last_sync ? 
                        `Last sync: ${format(new Date(integration.last_sync), 'MMM dd, HH:mm')}` : 
                        'Never synced'
                      }
                    </span>
                  </div>

                  {/* Capabilities */}
                  {integration.capabilities && integration.capabilities.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-xs font-medium text-gray-700">Capabilities:</Label>
                      <div className="flex flex-wrap gap-1">
                        {integration.capabilities.slice(0, 3).map((capability, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {capability}
                          </Badge>
                        ))}
                        {integration.capabilities.length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{integration.capabilities.length - 3} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}

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
                      {Object.entries(integration.metrics).slice(0, 3).map(([key, value]) => (
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

      {/* Add Integration Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add New Integration</DialogTitle>
            <DialogDescription>
              Choose an integration to connect to your infrastructure
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-3 max-h-96 overflow-y-auto">
            {availableIntegrations.map((integration: AvailableIntegration) => {
              const IconComponent = INTEGRATION_ICONS[integration.type] || Settings;
              return (
                <div
                  key={integration.type}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-gray-100 rounded-lg">
                      <IconComponent className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="font-medium">{integration.name}</div>
                      <div className="text-sm text-gray-500">{integration.description}</div>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {integration.category}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {integration.setup_difficulty}
                        </Badge>
                        {integration.required && (
                          <Badge className="text-xs bg-red-100 text-red-800">Required</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {integration.status === 'coming_soon' && (
                      <Badge variant="outline" className="text-xs">
                        Coming Soon
                      </Badge>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        toast.info(`${integration.name} setup coming soon`);
                        setShowAddDialog(false);
                      }}
                      disabled={integration.status === 'coming_soon'}
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Setup
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}