'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  RefreshCw, 
  Settings, 
  Trash2, 
  Plus,
  Activity,
  Clock,
  Loader2,
  ExternalLink
} from 'lucide-react';
import { IntegrationSetupModal } from '@/components/integrations/integration-setup-modal';
import { NotionActivityWidget } from '@/components/notion-activity/NotionActivityWidget';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';

interface UserIntegration {
  id: string;
  integration_type: string;
  is_enabled: boolean;
  is_required: boolean;
  last_test_at?: string;
  last_test_status?: 'success' | 'failed' | 'pending';
  last_test_error?: string;
  created_at: string;
  updated_at: string;
  config?: any;
}

interface IntegrationMetadata {
  type: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  documentation_url?: string;
  status?: 'available' | 'coming_soon';
}

const INTEGRATION_METADATA: Record<string, IntegrationMetadata> = {
  pagerduty: {
    type: 'pagerduty',
    name: 'PagerDuty',
    description: 'Receives alerts and triggers AI incident response',
    icon: '🚨',
    category: 'incident_management',
    documentation_url: '/docs/integrations/pagerduty'
  },
  kubernetes: {
    type: 'kubernetes',
    name: 'Kubernetes',
    description: 'Monitors pods, deployments, and enables automated fixes',
    icon: '☸️',
    category: 'infrastructure',
    documentation_url: '/docs/integrations/kubernetes'
  },
  github: {
    type: 'github',
    name: 'GitHub',
    description: 'Provides codebase context for incident analysis',
    icon: '🐙',
    category: 'source_control',
    documentation_url: '/docs/integrations/github'
  },
  notion: {
    type: 'notion',
    name: 'Notion',
    description: 'Accesses internal runbooks and documentation',
    icon: '📝',
    category: 'documentation',
    documentation_url: '/docs/integrations/notion'
  },
  grafana: {
    type: 'grafana',
    name: 'Grafana',
    description: 'Fetches metrics and dashboard data during incidents',
    icon: '📊',
    category: 'monitoring',
    documentation_url: '/docs/integrations/grafana'
  },
  datadog: {
    type: 'datadog',
    name: 'Datadog',
    description: 'Alternative monitoring and APM integration',
    icon: '🐕',
    category: 'monitoring',
    status: 'coming_soon',
    documentation_url: '/docs/integrations/datadog'
  }
};

export default function IntegrationsSettingsPage() {
  const [integrations, setIntegrations] = useState<UserIntegration[]>([]);
  const [availableIntegrations, setAvailableIntegrations] = useState<IntegrationMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedIntegration, setSelectedIntegration] = useState<IntegrationMetadata | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTestingAll, setIsTestingAll] = useState(false);
  const [activeTab, setActiveTab] = useState('connected');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      // Fetch user integrations
      const integrationsResponse = await apiClient.get('/api/v1/user/integrations');
      setIntegrations(integrationsResponse.data.integrations || []);

      // Determine available integrations
      const connectedTypes = integrationsResponse.data.integrations.map((i: UserIntegration) => i.integration_type);
      const available = Object.values(INTEGRATION_METADATA).filter(
        meta => !connectedTypes.includes(meta.type) && meta.status !== 'coming_soon'
      );
      setAvailableIntegrations(available);
    } catch (error) {
      console.error('Failed to fetch integrations:', error);
      toast.error('Failed to load integrations');
    } finally {
      setIsLoading(false);
    }
  };

  const getIntegrationMetadata = (type: string): IntegrationMetadata => {
    return INTEGRATION_METADATA[type] || {
      type,
      name: type ? (type.charAt(0).toUpperCase() + type.slice(1)) : 'Unknown',
      description: 'Integration',
      icon: '🔧',
      category: 'other'
    };
  };

  const getStatusIcon = (integration: UserIntegration) => {
    if (!integration.is_enabled) {
      return <XCircle className="h-5 w-5 text-gray-400" />;
    }
    
    switch (integration.last_test_status) {
      case 'success':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusText = (integration: UserIntegration) => {
    if (!integration.is_enabled) return 'Disabled';
    
    switch (integration.last_test_status) {
      case 'success':
        return 'Connected';
      case 'failed':
        return 'Connection Failed';
      default:
        return 'Not Tested';
    }
  };

  const handleTest = async (integration: UserIntegration) => {
    try {
      const response = await apiClient.post(
        `/api/v1/integrations/test/${integration.integration_type}`,
        { 
          integration_type: integration.integration_type,
          config: integration.config 
        }
      );

      // Update integration with test result
      await apiClient.put(`/api/v1/user/integrations/${integration.id}`, {
        last_test_status: response.data.success ? 'success' : 'failed',
        last_test_error: response.data.error
      });

      await fetchData();

      if (response.data.success) {
        toast.success(`${getIntegrationMetadata(integration.integration_type).name} connection is working`);
      } else {
        toast.error(response.data.error || 'Connection test failed');
      }
    } catch (error) {
      toast.error('Failed to test integration');
    }
  };

  const handleToggle = async (integration: UserIntegration) => {
    try {
      await apiClient.put(`/api/v1/user/integrations/${integration.id}`, {
        is_enabled: !integration.is_enabled
      });

      await fetchData();

      toast.success(`${getIntegrationMetadata(integration.integration_type).name} has been ${integration.is_enabled ? 'disabled' : 'enabled'}`);
    } catch (error) {
      toast.error('Failed to update integration');
    }
  };

  const handleRemove = async (integration: UserIntegration) => {
    if (integration.is_required) {
      toast.error('Required integrations cannot be removed');
      return;
    }

    if (!confirm(`Are you sure you want to remove ${getIntegrationMetadata(integration.integration_type).name}?`)) {
      return;
    }

    try {
      await apiClient.delete(`/api/v1/user/integrations/${integration.id}`);
      await fetchData();
      
      toast.success(`${getIntegrationMetadata(integration.integration_type).name} has been removed`);
    } catch (error) {
      toast.error('Failed to remove integration');
    }
  };

  const handleTestAll = async () => {
    setIsTestingAll(true);
    
    try {
      const response = await apiClient.post('/api/v1/integrations/test-all');
      await fetchData();
      
      toast.success(`${response.data.summary.successful} of ${response.data.summary.total} integrations connected successfully`);
    } catch (error) {
      toast.error('Failed to test integrations');
    } finally {
      setIsTestingAll(false);
    }
  };

  const handleAddIntegration = (metadata: IntegrationMetadata) => {
    setSelectedIntegration(metadata);
    setIsModalOpen(true);
  };

  const handleIntegrationSave = async (config: any) => {
    console.log('handleIntegrationSave called', { selectedIntegration, config });
    if (!selectedIntegration) {
      console.error('Missing selectedIntegration', { selectedIntegration });
      return;
    }

    try {
      console.log('Sending request to save integration', {
        url: '/api/v1/user/integrations',
        data: {
          integration_type: selectedIntegration.type,
          config,
          is_required: false
        }
      });
      await apiClient.post('/api/v1/user/integrations', {
        integration_type: selectedIntegration.type,
        config,
        is_required: false
      });

      await fetchData();
      
      toast.success('Integration Added', {
        description: `${selectedIntegration.name} has been connected successfully`
      });
    } catch (error: any) {
      toast.error('Error', {
        description: error.response?.data?.detail || 'Failed to add integration'
      });
    }

    setIsModalOpen(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Configure your AI agent and incident response preferences
        </p>
      </div>

      {/* Settings Navigation */}
      <div className="mb-6">
        <nav className="flex space-x-4 border-b">
          <Link
            href="/settings"
            className="pb-3 px-1 border-b-2 border-transparent text-sm text-muted-foreground hover:text-foreground hover:border-gray-300"
          >
            Agent Settings
          </Link>
          <Link
            href="/settings/integrations"
            className="pb-3 px-1 border-b-2 border-primary font-medium text-sm"
          >
            Integrations
          </Link>
        </nav>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex justify-between items-center mb-6">
          <TabsList>
            <TabsTrigger value="connected">
              Connected ({integrations.length})
            </TabsTrigger>
            <TabsTrigger value="available">
              Available ({availableIntegrations.length})
            </TabsTrigger>
          </TabsList>

          <Button
            variant="outline"
            onClick={handleTestAll}
            disabled={isTestingAll || integrations.length === 0}
          >
            {isTestingAll ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Test All
              </>
            )}
          </Button>
        </div>

        <TabsContent value="connected" className="space-y-4">
          {integrations.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <AlertCircle className="h-12 w-12 text-gray-400 mb-4" />
                <p className="text-lg font-medium text-gray-900 mb-2">No integrations connected</p>
                <p className="text-sm text-gray-600 mb-4">Add integrations to enhance your incident response</p>
                <Button onClick={() => setActiveTab('available')}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Integration
                </Button>
              </CardContent>
            </Card>
          ) : (
            integrations.map((integration) => {
              const metadata = getIntegrationMetadata(integration.integration_type);
              
              return (
                <Card key={integration.id}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4">
                        <span className="text-2xl">{metadata.icon}</span>
                        <div>
                          <CardTitle className="text-lg flex items-center gap-2">
                            {metadata.name}
                            {integration.is_required && (
                              <Badge variant="destructive" className="text-xs">REQUIRED</Badge>
                            )}
                          </CardTitle>
                          <CardDescription>{metadata.description}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(integration)}
                        <span className="text-sm font-medium">{getStatusText(integration)}</span>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {integration.last_test_at && (
                        <div className="text-sm text-muted-foreground">
                          Last tested {formatDistanceToNow(new Date(integration.last_test_at), { addSuffix: true })}
                        </div>
                      )}
                      
                      {integration.last_test_error && integration.last_test_status === 'failed' && (
                        <Alert className="border-red-200">
                          <AlertCircle className="h-4 w-4 text-red-600" />
                          <AlertDescription className="text-sm">
                            {integration.last_test_error}
                          </AlertDescription>
                        </Alert>
                      )}

                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleTest(integration)}
                        >
                          <Activity className="h-4 w-4 mr-2" />
                          Test Connection
                        </Button>
                        
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggle(integration)}
                        >
                          {integration.is_enabled ? 'Disable' : 'Enable'}
                        </Button>
                        
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const meta = getIntegrationMetadata(integration.integration_type);
                            setSelectedIntegration(meta);
                            setIsModalOpen(true);
                          }}
                        >
                          <Settings className="h-4 w-4 mr-2" />
                          Configure
                        </Button>
                        
                        {!integration.is_required && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemove(integration)}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}

                        {metadata.documentation_url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(metadata.documentation_url, '_blank')}
                          >
                            <ExternalLink className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
          
          {/* Show Notion Activity Widget if Notion is connected */}
          {integrations.some(i => i.integration_type === 'notion' && i.is_enabled) && (
            <div className="mt-6">
              <NotionActivityWidget />
            </div>
          )}
        </TabsContent>

        <TabsContent value="available" className="space-y-4">
          {availableIntegrations.map((metadata) => (
            <Card key={metadata.type}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4">
                    <span className="text-2xl">{metadata.icon}</span>
                    <div>
                      <CardTitle className="text-lg">{metadata.name}</CardTitle>
                      <CardDescription>{metadata.description}</CardDescription>
                    </div>
                  </div>
                  <Button
                    onClick={() => handleAddIntegration(metadata)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add
                  </Button>
                </div>
              </CardHeader>
            </Card>
          ))}

          {/* Coming Soon */}
          <Card className="border-dashed">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4">
                  <span className="text-2xl">{INTEGRATION_METADATA.datadog.icon}</span>
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      {INTEGRATION_METADATA.datadog.name}
                      <Badge variant="secondary" className="text-xs">COMING SOON</Badge>
                    </CardTitle>
                    <CardDescription>{INTEGRATION_METADATA.datadog.description}</CardDescription>
                  </div>
                </div>
                <Button disabled variant="outline">
                  Notify Me
                </Button>
              </div>
            </CardHeader>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Integration Setup Modal */}
      {selectedIntegration && (
        <IntegrationSetupModal
          integration={selectedIntegration}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSave={handleIntegrationSave}
        />
      )}
    </div>
  );
}