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
import { CopyIcon, CheckCircle2, AlertCircle, Loader2, ExternalLink, Info } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { useDevAutofill } from '@/lib/hooks/use-dev-autofill';

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
  
  const { isDevMode, getDevConfig, autofillForm } = useDevAutofill(integration?.type);

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
      
      // Initialize config with template or dev config
      if (isDevMode) {
        const devConfig = getDevConfig(integration.type);
        if (devConfig) {
          setConfig(devConfig);
        } else {
          setConfig(templateResponse.data.templates[integration.type] || {});
        }
      } else {
        setConfig(templateResponse.data.templates[integration.type] || {});
      }
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
    toast.success('Copied to clipboard');
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);

    console.log('Testing integration with config:', config);

    try {
      const response = await apiClient.post(
        `/api/v1/integrations/test/${integration.type}`,
        { integration_type: integration.type, config }
      );

      setTestResult(response.data);
      
      if (response.data.success) {
        toast.success('Connection test passed! You can now save this integration.');
      } else {
        toast.error(response.data.error || 'Connection test failed');
      }
    } catch (error: any) {
      setTestResult({
        success: false,
        error: error.response?.data?.detail || 'Failed to test connection'
      });
      
      toast.error('Failed to test connection');
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    console.log('Save button clicked', { integration, config });
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
          <DialogTitle className="flex items-center justify-between">
            <span>Setup {integration.name} Integration</span>
            {isDevMode && (
              <Badge variant="outline" className="ml-2 bg-yellow-50 border-yellow-300 text-yellow-800">
                DEV MODE
              </Badge>
            )}
          </DialogTitle>
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
          {integration.type !== 'pagerduty' && (
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
          )}
          <Button 
            onClick={handleSave}
            disabled={integration.type !== 'pagerduty' && !testResult?.success}
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
      <Alert className="border-blue-200 bg-blue-50">
        <AlertCircle className="h-4 w-4 text-blue-600" />
        <AlertDescription className="text-blue-800">
          <strong>Setup Instructions:</strong>
          <ol className="mt-2 space-y-1 text-sm">
            <li>1. Go to your PagerDuty account settings</li>
            <li>2. Navigate to API Access → API Access Keys</li>
            <li>3. Create a new API key with full access</li>
            <li>4. Copy the API key below</li>
          </ol>
        </AlertDescription>
      </Alert>

      <div>
        <Label htmlFor="api_key">API Key *</Label>
        <Input
          id="api_key"
          type="password"
          placeholder="u+wtxR9ysxHtPM9xPL8Q..."
          value={config.api_key || ''}
          onChange={(e) => onChange('api_key', e.target.value)}
          className="font-mono text-sm"
        />
        <p className="text-sm text-muted-foreground mt-1">
          Your PagerDuty API key for accessing incidents and services
        </p>
      </div>

      <div>
        <Label htmlFor="user_email">User Email *</Label>
        <Input
          id="user_email"
          type="email"
          placeholder="your-email@company.com"
          value={config.user_email || ''}
          onChange={(e) => onChange('user_email', e.target.value)}
        />
        <p className="text-sm text-muted-foreground mt-1">
          The email address associated with your PagerDuty account
        </p>
      </div>

      <div>
        <Label htmlFor="webhook_secret">Webhook Secret *</Label>
        <Input
          id="webhook_secret"
          type="password"
          placeholder="Enter a strong secret for webhook verification"
          value={config.webhook_secret || ''}
          onChange={(e) => onChange('webhook_secret', e.target.value)}
        />
        <p className="text-sm text-muted-foreground mt-1">
          A secret key for verifying PagerDuty webhook signatures
        </p>
      </div>

      <Alert>
        <AlertDescription>
          <strong>Note:</strong> After saving, you'll need to configure a webhook in PagerDuty 
          to send incidents to: <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
            {process.env.NEXT_PUBLIC_API_URL}/webhook/pagerduty
          </code>
        </AlertDescription>
      </Alert>

      <Alert className="border-green-200 bg-green-50">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <AlertDescription className="text-green-800">
          <strong>No test required:</strong> PagerDuty configuration will be validated when you receive your first webhook.
        </AlertDescription>
      </Alert>
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
      const contextObjects = response.data.contexts || [];
      // Extract just the context names
      const contextNames = contextObjects.map((ctx: any) => ctx.name);
      setContexts(contextNames);
      
      // Initialize config with discovered contexts only if no contexts are selected yet
      if (contextNames.length > 0 && (!config.contexts || config.contexts.length === 0)) {
        const selectedContexts = contextNames.slice(0, 1); // Select first by default
        const namespaces: any = {};
        selectedContexts.forEach((ctx: string) => {
          namespaces[ctx] = 'default';
        });
        
        onChange('contexts', selectedContexts);
        onChange('namespaces', namespaces);
      } else if (config.contexts && config.contexts.length > 0) {
        // Preserve existing namespace selections
        const existingNamespaces = config.namespaces || {};
        config.contexts.forEach((ctx: string) => {
          if (!existingNamespaces[ctx]) {
            existingNamespaces[ctx] = 'default';
          }
        });
        onChange('namespaces', existingNamespaces);
      }
      
      toast.success(`Found ${contextNames.length} Kubernetes context${contextNames.length !== 1 ? 's' : ''}`);
    } catch (error) {
      console.error('Failed to discover contexts:', error);
      toast.error('Failed to discover Kubernetes contexts');
    } finally {
      setIsDiscovering(false);
    }
  };

  return (
    <div className="space-y-4">
      <Alert className="border-blue-200 bg-blue-50">
        <AlertCircle className="h-4 w-4 text-blue-600" />
        <AlertDescription className="text-blue-800">
          <strong>Setup Instructions:</strong>
          <ol className="mt-2 space-y-1 text-sm">
            <li>1. Ensure kubectl is installed and configured</li>
            <li>2. Run: <code className="bg-gray-100 px-1 rounded">kubectl config get-contexts</code></li>
            <li>3. Click "Auto-discover" to find available clusters</li>
            <li>4. Select the clusters you want to monitor</li>
            <li>5. Ensure your kubectl has the following permissions:</li>
            <li className="ml-4">• <code>get, list, watch</code> on pods, deployments, services</li>
            <li className="ml-4">• <code>delete</code> on pods (for restart operations)</li>
          </ol>
        </AlertDescription>
      </Alert>

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
                      id={`context-${context}`}
                      checked={config.contexts?.includes(context) || false}
                      onChange={(e) => {
                        const isChecked = e.target.checked;
                        const currentContexts = config.contexts || [];
                        
                        // Create new contexts array
                        const newContexts = isChecked
                          ? [...currentContexts, context]
                          : currentContexts.filter((c: string) => c !== context);
                        
                        // Update contexts
                        onChange('contexts', newContexts);
                        
                        // Update namespaces
                        const newNamespaces = { ...(config.namespaces || {}) };
                        if (isChecked) {
                          // Only set to default if not already set
                          if (!newNamespaces[context]) {
                            newNamespaces[context] = 'default';
                          }
                        } else {
                          delete newNamespaces[context];
                        }
                        onChange('namespaces', newNamespaces);
                        
                        console.log('Context selection changed:', {
                          context,
                          isChecked,
                          newContexts,
                          newNamespaces
                        });
                      }}
                      className="rounded cursor-pointer"
                    />
                    <Label htmlFor={`context-${context}`} className="font-medium cursor-pointer">
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
                          console.log('Namespace changed:', {
                            context,
                            namespace: e.target.value,
                            allNamespaces: newNamespaces
                          });
                        }}
                        placeholder="default"
                        className="h-8 w-40"
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

      {config.contexts && config.contexts.length > 0 && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>Selected for testing:</strong> Context "{config.contexts[0]}" with namespace "{config.namespaces?.[config.contexts[0]] || 'default'}"
          </AlertDescription>
        </Alert>
      )}

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

      <div className="space-y-2">
        <Label>Upload Kubeconfig File (Optional)</Label>
        <div className="border-2 border-dashed rounded-lg p-4">
          <input
            type="file"
            accept=".yaml,.yml,.conf,text/*"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (file) {
                const content = await file.text();
                // Base64 encode the content
                const encodedContent = btoa(content);
                onChange('kubeconfig_content', encodedContent);
                toast.success('Kubeconfig file uploaded successfully');
              }
            }}
            className="w-full"
          />
          <p className="text-sm text-muted-foreground mt-2">
            Upload a kubeconfig file to connect to remote clusters
          </p>
        </div>
      </div>
    </div>
  );
}

// GitHub Configuration Component
function GitHubConfig({ config, onChange, requirements }: any) {
  return (
    <div className="space-y-4">
      <Alert className="border-blue-200 bg-blue-50">
        <AlertCircle className="h-4 w-4 text-blue-600" />
        <AlertDescription className="text-blue-800">
          <strong>Setup Instructions:</strong>
          <ol className="mt-2 space-y-1 text-sm">
            <li>1. Go to GitHub → Settings → Developer settings</li>
            <li>2. Click "Personal access tokens" → "Tokens (classic)"</li>
            <li>3. Click "Generate new token (classic)"</li>
            <li>4. Select scopes: <code className="bg-gray-100 px-1 rounded">repo</code>, <code className="bg-gray-100 px-1 rounded">read:org</code></li>
            <li>5. Generate token and copy it below</li>
          </ol>
        </AlertDescription>
      </Alert>

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
      <Alert className="border-blue-200 bg-blue-50">
        <AlertCircle className="h-4 w-4 text-blue-600" />
        <AlertDescription className="text-blue-800">
          <strong>Setup Instructions:</strong>
          <ol className="mt-2 space-y-1 text-sm">
            <li>1. Go to <a href="https://www.notion.so/my-integrations" target="_blank" className="underline">notion.so/my-integrations</a></li>
            <li>2. Click "New integration"</li>
            <li>3. Give it a name (e.g., "DreamOps")</li>
            <li>4. Select the workspace to integrate</li>
            <li>5. Copy the "Internal Integration Token"</li>
            <li>6. Share your runbook pages with the integration</li>
          </ol>
        </AlertDescription>
      </Alert>

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
      <Alert className="border-blue-200 bg-blue-50">
        <AlertCircle className="h-4 w-4 text-blue-600" />
        <AlertDescription className="text-blue-800">
          <strong>Setup Instructions:</strong>
          <ol className="mt-2 space-y-1 text-sm">
            <li>1. Log in to your Grafana instance</li>
            <li>2. Go to Configuration → API Keys (or Administration → API Keys in newer versions)</li>
            <li>3. Click "Add API key"</li>
            <li>4. Name it "DreamOps" with "Viewer" role or higher</li>
            <li>5. Copy the generated API key immediately (it won't be shown again)</li>
            <li>6. Note your Grafana URL (e.g., https://mycompany.grafana.net)</li>
            <li className="text-amber-700 font-medium">⚠️ Important: API keys expire! Check expiration settings.</li>
          </ol>
        </AlertDescription>
      </Alert>

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