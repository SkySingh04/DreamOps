'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CopyIcon, CheckCircle2, AlertCircle, Loader2, ExternalLink } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from '@/components/ui/use-toast';

interface IntegrationSetupModalProps {
  integration: {
    type: string;
    name: string;
    description: string;
  };
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: any) => void;
}

interface SetupStep {
  title: string;
  description: string;
  image?: string;
}

export function IntegrationSetupModal({
  integration,
  isOpen,
  onClose,
  onSave
}: IntegrationSetupModalProps) {
  const [config, setConfig] = useState<any>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [requirements, setRequirements] = useState<any>(null);
  const [template, setTemplate] = useState<any>(null);

  useEffect(() => {
    if (isOpen && integration) {
      fetchIntegrationDetails();
    }
  }, [isOpen, integration]);

  const fetchIntegrationDetails = async () => {
    try {
      // Fetch requirements and template
      const [reqResponse, templateResponse] = await Promise.all([
        apiClient.get(`/api/v1/integrations/${integration.type}/requirements`),
        apiClient.get('/api/v1/integrations/templates')
      ]);

      setRequirements(reqResponse.data);
      setTemplate(templateResponse.data.templates[integration.type] || {});
      
      // Initialize config with template
      setConfig(templateResponse.data.templates[integration.type] || {});
    } catch (error) {
      console.error('Failed to fetch integration details:', error);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setConfig((prev: any) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied to clipboard',
      description: 'The text has been copied to your clipboard'
    });
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);

    try {
      const response = await apiClient.post(
        `/api/v1/integrations/test/${integration.type}`,
        { integration_type: integration.type, config }
      );

      setTestResult(response.data);
      
      if (response.data.success) {
        toast({
          title: 'Test Successful',
          description: 'Connection test passed! You can now save this integration.'
        });
      } else {
        toast({
          title: 'Test Failed',
          description: response.data.error || 'Connection test failed',
          variant: 'destructive'
        });
      }
    } catch (error: any) {
      setTestResult({
        success: false,
        error: error.response?.data?.detail || 'Failed to test connection'
      });
      
      toast({
        title: 'Test Failed',
        description: 'Failed to test connection',
        variant: 'destructive'
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    onSave(config);
  };

  const renderConfigForm = () => {
    switch (integration.type) {
      case 'pagerduty':
        return <PagerDutyConfig config={config} onChange={handleInputChange} requirements={requirements} />;
      case 'kubernetes':
        return <KubernetesConfig config={config} onChange={handleInputChange} requirements={requirements} />;
      case 'github':
        return <GitHubConfig config={config} onChange={handleInputChange} requirements={requirements} />;
      case 'notion':
        return <NotionConfig config={config} onChange={handleInputChange} requirements={requirements} />;
      case 'grafana':
        return <GrafanaConfig config={config} onChange={handleInputChange} requirements={requirements} />;
      default:
        return <div>Configuration not available for this integration</div>;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Setup {integration.name} Integration</DialogTitle>
          <DialogDescription>
            {integration.description}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="config" className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="config">Configuration</TabsTrigger>
            <TabsTrigger value="instructions">Setup Instructions</TabsTrigger>
          </TabsList>

          <TabsContent value="config" className="space-y-4">
            {renderConfigForm()}

            {testResult && (
              <Alert className={testResult.success ? 'border-green-200' : 'border-red-200'}>
                <div className="flex items-start gap-2">
                  {testResult.success ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <AlertDescription>
                      {testResult.success ? 'Connection test passed!' : testResult.error}
                    </AlertDescription>
                    {testResult.details && (
                      <div className="mt-2 space-y-1">
                        {Object.entries(testResult.details).map(([key, value]) => (
                          <div key={key} className="text-sm">
                            <span className="font-medium">{key}:</span> {String(value)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </Alert>
            )}
          </TabsContent>

          <TabsContent value="instructions" className="space-y-4">
            <SetupInstructions 
              integration={integration} 
              requirements={requirements} 
              onCopy={handleCopy}
            />
          </TabsContent>
        </Tabs>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            variant="outline" 
            onClick={handleTest}
            disabled={isTesting}
          >
            {isTesting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              'Test Connection'
            )}
          </Button>
          <Button 
            onClick={handleSave}
            disabled={!testResult?.success}
          >
            Save Integration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// PagerDuty Configuration Component
function PagerDutyConfig({ config, onChange, requirements }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="integration_url">Integration URL *</Label>
        <Input
          id="integration_url"
          type="url"
          placeholder="https://events.pagerduty.com/integration/..."
          value={config.integration_url || ''}
          onChange={(e) => onChange('integration_url', e.target.value)}
          className="font-mono text-sm"
        />
        <p className="text-sm text-muted-foreground mt-1">
          The webhook URL from your PagerDuty service integration
        </p>
      </div>

      <div>
        <Label htmlFor="webhook_secret">Webhook Secret (Optional)</Label>
        <Input
          id="webhook_secret"
          type="password"
          placeholder="Enter webhook secret for signature verification"
          value={config.webhook_secret || ''}
          onChange={(e) => onChange('webhook_secret', e.target.value)}
        />
        <p className="text-sm text-muted-foreground mt-1">
          Optional: Used to verify webhook signatures for added security
        </p>
      </div>
    </div>
  );
}

// Kubernetes Configuration Component
function KubernetesConfig({ config, onChange, requirements }: any) {
  const [contexts, setContexts] = useState<string[]>([]);
  const [isDiscovering, setIsDiscovering] = useState(false);

  const discoverContexts = async () => {
    setIsDiscovering(true);
    try {
      const response = await apiClient.get('/api/v1/integrations/kubernetes/discover');
      setContexts(response.data.contexts || []);
      
      // Initialize config with discovered contexts
      if (response.data.contexts?.length > 0) {
        const selectedContexts = response.data.contexts.slice(0, 1); // Select first by default
        const namespaces: any = {};
        selectedContexts.forEach((ctx: string) => {
          namespaces[ctx] = 'default';
        });
        
        onChange('contexts', selectedContexts);
        onChange('namespaces', namespaces);
      }
    } catch (error) {
      toast({
        title: 'Discovery Failed',
        description: 'Failed to discover Kubernetes contexts',
        variant: 'destructive'
      });
    } finally {
      setIsDiscovering(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <div className="flex justify-between items-center mb-2">
          <Label>Kubernetes Contexts</Label>
          <Button 
            size="sm" 
            variant="outline"
            onClick={discoverContexts}
            disabled={isDiscovering}
          >
            {isDiscovering ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Discovering...
              </>
            ) : (
              'Auto-discover'
            )}
          </Button>
        </div>
        
        {contexts.length > 0 ? (
          <div className="space-y-2">
            {contexts.map((context) => (
              <Card key={context} className="p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={config.contexts?.includes(context) || false}
                      onChange={(e) => {
                        const newContexts = e.target.checked
                          ? [...(config.contexts || []), context]
                          : (config.contexts || []).filter((c: string) => c !== context);
                        onChange('contexts', newContexts);
                        
                        // Update namespaces
                        const newNamespaces = { ...(config.namespaces || {}) };
                        if (e.target.checked) {
                          newNamespaces[context] = 'default';
                        } else {
                          delete newNamespaces[context];
                        }
                        onChange('namespaces', newNamespaces);
                      }}
                      className="rounded"
                    />
                    <Label className="font-medium cursor-pointer">
                      {context}
                    </Label>
                  </div>
                  
                  {config.contexts?.includes(context) && (
                    <div className="flex items-center gap-2">
                      <Label className="text-sm">Namespace:</Label>
                      <Input
                        type="text"
                        value={config.namespaces?.[context] || 'default'}
                        onChange={(e) => {
                          const newNamespaces = {
                            ...(config.namespaces || {}),
                            [context]: e.target.value
                          };
                          onChange('namespaces', newNamespaces);
                        }}
                        className="h-8 w-32"
                      />
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div className="border rounded-md p-4 text-center text-muted-foreground">
            Click "Auto-discover" to find available Kubernetes contexts
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <Label htmlFor="enable_destructive">Enable Destructive Operations (YOLO Mode)</Label>
          <p className="text-sm text-muted-foreground">
            Allow the agent to restart pods and modify deployments
          </p>
        </div>
        <Switch
          id="enable_destructive"
          checked={config.enable_destructive_operations || false}
          onCheckedChange={(checked) => onChange('enable_destructive_operations', checked)}
        />
      </div>

      <div>
        <Label htmlFor="kubeconfig_path">Kubeconfig Path (Optional)</Label>
        <Input
          id="kubeconfig_path"
          type="text"
          placeholder="~/.kube/config"
          value={config.kubeconfig_path || ''}
          onChange={(e) => onChange('kubeconfig_path', e.target.value)}
        />
      </div>
    </div>
  );
}

// GitHub Configuration Component
function GitHubConfig({ config, onChange, requirements }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="token">Personal Access Token *</Label>
        <Input
          id="token"
          type="password"
          placeholder="ghp_..."
          value={config.token || ''}
          onChange={(e) => onChange('token', e.target.value)}
          className="font-mono"
        />
        <p className="text-sm text-muted-foreground mt-1">
          Token with repo and read:org permissions
        </p>
      </div>

      <div>
        <Label htmlFor="organization">Organization (Optional)</Label>
        <Input
          id="organization"
          type="text"
          placeholder="your-org"
          value={config.organization || ''}
          onChange={(e) => onChange('organization', e.target.value)}
        />
      </div>

      <div>
        <Label htmlFor="repositories">Repositories (Optional)</Label>
        <Textarea
          id="repositories"
          placeholder="repo1&#10;repo2&#10;repo3"
          value={(config.repositories || []).join('\n')}
          onChange={(e) => onChange('repositories', e.target.value.split('\n').filter(Boolean))}
          rows={3}
        />
        <p className="text-sm text-muted-foreground mt-1">
          One repository per line. Leave empty to access all repositories.
        </p>
      </div>
    </div>
  );
}

// Notion Configuration Component
function NotionConfig({ config, onChange, requirements }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="token">Integration Token *</Label>
        <Input
          id="token"
          type="password"
          placeholder="secret_..."
          value={config.token || ''}
          onChange={(e) => onChange('token', e.target.value)}
          className="font-mono"
        />
        <p className="text-sm text-muted-foreground mt-1">
          Your Notion integration token
        </p>
      </div>

      <div>
        <Label htmlFor="workspace_id">Workspace ID (Optional)</Label>
        <Input
          id="workspace_id"
          type="text"
          placeholder="12345678-90ab-cdef-1234-567890abcdef"
          value={config.workspace_id || ''}
          onChange={(e) => onChange('workspace_id', e.target.value)}
        />
        <p className="text-sm text-muted-foreground mt-1">
          Optional: Specific workspace to access
        </p>
      </div>
    </div>
  );
}

// Grafana Configuration Component
function GrafanaConfig({ config, onChange, requirements }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="url">Grafana URL *</Label>
        <Input
          id="url"
          type="url"
          placeholder="https://your-grafana.com"
          value={config.url || ''}
          onChange={(e) => onChange('url', e.target.value)}
        />
        <p className="text-sm text-muted-foreground mt-1">
          Your Grafana instance URL
        </p>
      </div>

      <div>
        <Label htmlFor="api_key">API Key *</Label>
        <Input
          id="api_key"
          type="password"
          placeholder="Enter your Grafana API key"
          value={config.api_key || ''}
          onChange={(e) => onChange('api_key', e.target.value)}
        />
        <p className="text-sm text-muted-foreground mt-1">
          API key with viewer permissions
        </p>
      </div>
    </div>
  );
}

// Setup Instructions Component
function SetupInstructions({ integration, requirements, onCopy }: any) {
  if (!requirements) return null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Required Permissions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {requirements.permissions?.map((perm: string) => (
              <Badge key={perm} variant="secondary">
                {perm}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Setup Steps</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="space-y-3">
            {requirements.setup_steps?.map((step: string, index: number) => (
              <li key={index} className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-medium">
                  {index + 1}
                </span>
                <span className="text-sm">{step}</span>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {integration.type === 'pagerduty' && (
        <Alert>
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-medium">Quick tip:</p>
              <p className="text-sm">
                You can find your Integration URL in PagerDuty under Services → 
                Your Service → Integrations → Add Integration → Amazon CloudWatch
              </p>
              <Button
                variant="link"
                size="sm"
                className="p-0 h-auto"
                onClick={() => window.open('https://support.pagerduty.com/docs/services-and-integrations', '_blank')}
              >
                View PagerDuty Documentation
                <ExternalLink className="h-3 w-3 ml-1" />
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}