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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Save, Key, Bell, Brain, Shield, CheckCircle, XCircle, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient, queryKeys } from '@/lib/api-client';

interface AISettings {
  model: string;
  additional_context: string;
  auto_analyze: boolean;
  confidence_threshold: number;
  max_tokens: number;
  temperature: number;
}

interface AlertSettings {
  priority_threshold: string;
  auto_acknowledge: boolean;
  deduplication_enabled: boolean;
  deduplication_window_minutes: number;
  escalation_delay_minutes: number;
}

interface SecuritySettings {
  audit_logs_enabled: boolean;
  data_retention_days: number;
  require_2fa: boolean;
  session_timeout_minutes: number;
  ip_whitelist: string[];
}

interface APIKeySettings {
  anthropic_api_key: string;
  webhook_url: string;
  webhook_secret: string;
}

interface IntegrationConfig {
  enabled: boolean;
  config: Record<string, any>;
}

interface GlobalSettings {
  organization_name: string;
  timezone: string;
  retention_days: number;
  ai: AISettings;
  alerts: AlertSettings;
  security: SecuritySettings;
  api_keys: APIKeySettings;
  integrations: Record<string, IntegrationConfig>;
}

// Utility function to safely handle number values for inputs
const safeNumberValue = (value: number | undefined | null): string | number => {
  if (value == null || isNaN(value)) return '';
  return value;
};

export default function SettingsPage() {
  const [showAPIKeys, setShowAPIKeys] = useState(false);
  const [localAISettings, setLocalAISettings] = useState<AISettings | null>(null);
  const [localAlertSettings, setLocalAlertSettings] = useState<AlertSettings | null>(null);
  const [localSecuritySettings, setLocalSecuritySettings] = useState<SecuritySettings | null>(null);
  const [localAPIKeySettings, setLocalAPIKeySettings] = useState<APIKeySettings | null>(null);
  const queryClient = useQueryClient();

  // Fetch all settings
  const { data: settingsData, isLoading: settingsLoading, error: settingsError } = useQuery({
    queryKey: queryKeys.settings,
    queryFn: () => apiClient.getSettings(),
    staleTime: 300000, // 5 minutes
  });

  const settings = settingsData?.data as GlobalSettings | undefined;

  // Fetch integrations
  const { data: integrationsData, isLoading: integrationsLoading } = useQuery({
    queryKey: queryKeys.integrations,
    queryFn: () => apiClient.getIntegrations(),
  });

  const integrations = integrationsData?.data || [];

  // Update mutations
  const updateAIMutation = useMutation({
    mutationFn: (data: AISettings) => apiClient.updateAISettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
      toast.success('AI settings updated successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to update AI settings', {
        description: error.message,
      });
    },
  });

  const updateAlertMutation = useMutation({
    mutationFn: (data: AlertSettings) => apiClient.updateAlertSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
      toast.success('Alert settings updated successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to update alert settings', {
        description: error.message,
      });
    },
  });

  const updateSecurityMutation = useMutation({
    mutationFn: (data: SecuritySettings) => apiClient.updateSecuritySettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
      toast.success('Security settings updated successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to update security settings', {
        description: error.message,
      });
    },
  });

  const updateAPIKeyMutation = useMutation({
    mutationFn: (data: APIKeySettings) => apiClient.updateAPIKeySettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
      toast.success('API keys updated successfully');
    },
    onError: (error: any) => {
      toast.error('Failed to update API keys', {
        description: error.message,
      });
    },
  });


  // Initialize local state when settings load
  useEffect(() => {
    if (settings) {
      setLocalAISettings(settings.ai);
      setLocalAlertSettings(settings.alerts);
      setLocalSecuritySettings(settings.security);
      setLocalAPIKeySettings(settings.api_keys);
    }
  }, [settings]);

  const handleSaveAISettings = () => {
    if (localAISettings) {
      updateAIMutation.mutate(localAISettings);
    }
  };

  const handleSaveAlertSettings = () => {
    if (localAlertSettings) {
      updateAlertMutation.mutate(localAlertSettings);
    }
  };

  const handleSaveSecuritySettings = () => {
    if (localSecuritySettings) {
      updateSecurityMutation.mutate(localSecuritySettings);
    }
  };

  const handleSaveAPIKeys = () => {
    if (localAPIKeySettings) {
      updateAPIKeyMutation.mutate(localAPIKeySettings);
    }
  };


  const getIntegrationStatus = (name: string) => {
    const integration = integrations.find((i: any) => i.name === name);
    if (!integration) return 'unknown';
    return integration.status || 'unknown';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'disconnected':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'error':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  if (settingsLoading) {
    return (
      <section className="flex-1 p-4 lg:p-8">
        <div className="mb-6">
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="space-y-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-80" />
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-6 w-24" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    );
  }

  if (settingsError) {
    return (
      <section className="flex-1 p-4 lg:p-8">
        <Alert className="border-red-200 bg-red-50">
          <AlertDescription className="text-red-800">
            Failed to load settings. Please try refreshing the page.
          </AlertDescription>
        </Alert>
      </section>
    );
  }

  if (!settings || !localAISettings || !localAlertSettings || !localSecuritySettings || !localAPIKeySettings) {
    return (
      <section className="flex-1 p-4 lg:p-8">
        <div className="mb-6">
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="space-y-6">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-80" />
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-6 w-24" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="flex-1 p-4 lg:p-8">
      <div className="mb-6">
        <h1 className="text-lg lg:text-2xl font-medium mb-2">Agent Settings</h1>
        <p className="text-muted-foreground">
          Configure your AI agent and incident response preferences
        </p>
      </div>

      <div className="space-y-6">
        {/* AI Configuration */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              <CardTitle>AI Configuration</CardTitle>
            </div>
            <CardDescription>
              Configure Claude AI settings for incident analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="model">Claude Model</Label>
              <Select 
                value={localAISettings.model} 
                onValueChange={(value) => setLocalAISettings({...localAISettings, model: value})}
              >
                <SelectTrigger id="model" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="claude-3-5-sonnet">Claude 3.5 Sonnet</SelectItem>
                  <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                  <SelectItem value="claude-3-haiku">Claude 3 Haiku</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="context">Additional Context</Label>
              <Textarea
                id="context"
                value={localAISettings.additional_context}
                onChange={(e) => setLocalAISettings({...localAISettings, additional_context: e.target.value})}
                placeholder="Add any specific context or instructions for the AI agent..."
                className="mt-2 min-h-[100px]"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="confidence">Confidence Threshold</Label>
                <Input
                  id="confidence"
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={safeNumberValue(localAISettings?.confidence_threshold)}
                  onChange={(e) => setLocalAISettings({...localAISettings, confidence_threshold: parseFloat(e.target.value) || 0})}
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="temperature">Temperature</Label>
                <Input
                  id="temperature"
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  value={safeNumberValue(localAISettings?.temperature)}
                  onChange={(e) => setLocalAISettings({...localAISettings, temperature: parseFloat(e.target.value) || 0})}
                  className="mt-2"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="auto-analyze">Auto-analyze incidents</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically analyze new incidents as they arrive
                </p>
              </div>
              <Switch 
                id="auto-analyze" 
                checked={localAISettings.auto_analyze}
                onCheckedChange={(checked) => setLocalAISettings({...localAISettings, auto_analyze: checked})}
              />
            </div>

            <div className="flex justify-end pt-4 border-t">
              <Button 
                onClick={handleSaveAISettings}
                disabled={updateAIMutation.isPending}
                className="min-w-[120px]"
              >
                {updateAIMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Alert Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              <CardTitle>Alert Settings</CardTitle>
            </div>
            <CardDescription>
              Configure how alerts are processed and prioritized
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="priority">Priority Threshold</Label>
              <Select 
                value={localAlertSettings.priority_threshold} 
                onValueChange={(value) => setLocalAlertSettings({...localAlertSettings, priority_threshold: value})}
              >
                <SelectTrigger id="priority" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical Only</SelectItem>
                  <SelectItem value="high">High and Above</SelectItem>
                  <SelectItem value="medium">Medium and Above</SelectItem>
                  <SelectItem value="low">All Alerts</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="dedup-window">Deduplication Window (minutes)</Label>
                <Input
                  id="dedup-window"
                  type="number"
                  min="1"
                  value={safeNumberValue(localAlertSettings?.deduplication_window_minutes)}
                  onChange={(e) => setLocalAlertSettings({...localAlertSettings, deduplication_window_minutes: parseInt(e.target.value) || 1})}
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="escalation-delay">Escalation Delay (minutes)</Label>
                <Input
                  id="escalation-delay"
                  type="number"
                  min="1"
                  value={safeNumberValue(localAlertSettings?.escalation_delay_minutes)}
                  onChange={(e) => setLocalAlertSettings({...localAlertSettings, escalation_delay_minutes: parseInt(e.target.value) || 1})}
                  className="mt-2"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="auto-ack">Auto-acknowledge</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically acknowledge alerts when AI starts analysis
                </p>
              </div>
              <Switch 
                id="auto-ack" 
                checked={localAlertSettings.auto_acknowledge}
                onCheckedChange={(checked) => setLocalAlertSettings({...localAlertSettings, auto_acknowledge: checked})}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="dedup">De-duplication</Label>
                <p className="text-sm text-muted-foreground">
                  Group similar alerts together
                </p>
              </div>
              <Switch 
                id="dedup" 
                checked={localAlertSettings.deduplication_enabled}
                onCheckedChange={(checked) => setLocalAlertSettings({...localAlertSettings, deduplication_enabled: checked})}
              />
            </div>

            <div className="flex justify-end pt-4 border-t">
              <Button 
                onClick={handleSaveAlertSettings}
                disabled={updateAlertMutation.isPending}
                className="min-w-[120px]"
              >
                {updateAlertMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* API Keys */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              <CardTitle>API Keys</CardTitle>
            </div>
            <CardDescription>
              Manage your API keys and authentication
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="anthropic-key">Anthropic API Key</Label>
              <div className="flex gap-2 mt-2">
                <div className="relative flex-1">
                  <Input
                    id="anthropic-key"
                    type={showAPIKeys ? "text" : "password"}
                    value={localAPIKeySettings.anthropic_api_key}
                    onChange={(e) => setLocalAPIKeySettings({...localAPIKeySettings, anthropic_api_key: e.target.value})}
                    placeholder="sk-ant-api03-..."
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-2 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                    onClick={() => setShowAPIKeys(!showAPIKeys)}
                  >
                    {showAPIKeys ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            </div>

            <div>
              <Label htmlFor="webhook-url">Webhook URL</Label>
              <div className="flex gap-2 mt-2">
                <Input
                  id="webhook-url"
                  value={localAPIKeySettings.webhook_url}
                  onChange={(e) => setLocalAPIKeySettings({...localAPIKeySettings, webhook_url: e.target.value})}
                  placeholder="https://your-domain.com/api/alerts"
                />
                <Button 
                  variant="outline"
                  onClick={() => {
                    navigator.clipboard.writeText(localAPIKeySettings.webhook_url);
                    toast.success('Webhook URL copied to clipboard');
                  }}
                >
                  Copy
                </Button>
              </div>
            </div>

            <div>
              <Label htmlFor="webhook-secret">Webhook Secret</Label>
              <Input
                id="webhook-secret"
                type={showAPIKeys ? "text" : "password"}
                value={localAPIKeySettings.webhook_secret}
                onChange={(e) => setLocalAPIKeySettings({...localAPIKeySettings, webhook_secret: e.target.value})}
                placeholder="webhook secret..."
                className="mt-2"
              />
            </div>

            <div className="flex justify-end pt-4 border-t">
              <Button 
                onClick={handleSaveAPIKeys}
                disabled={updateAPIKeyMutation.isPending}
                className="min-w-[120px]"
              >
                {updateAPIKeyMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Integrations */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              <CardTitle>Integrations</CardTitle>
            </div>
            <CardDescription>
              Manage connections to external services
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {settings.integrations && Object.entries(settings.integrations).map(([name, config]) => (
              <div key={name} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="capitalize font-medium">{name}</div>
                  <Badge className={getStatusColor(getIntegrationStatus(name))}>
                    {getIntegrationStatus(name) === 'connected' ? (
                      <CheckCircle className="h-3 w-3 mr-1" />
                    ) : (
                      <XCircle className="h-3 w-3 mr-1" />
                    )}
                    {getIntegrationStatus(name)}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={config.enabled} disabled />
                </div>
              </div>
            ))}
            {integrationsLoading && (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Security */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              <CardTitle>Security</CardTitle>
            </div>
            <CardDescription>
              Security and compliance settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="retention">Data Retention (days)</Label>
              <Input
                id="retention"
                type="number"
                min="1"
                max="365"
                value={safeNumberValue(localSecuritySettings?.data_retention_days)}
                onChange={(e) => setLocalSecuritySettings({...localSecuritySettings, data_retention_days: parseInt(e.target.value) || 1})}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="session-timeout">Session Timeout (minutes)</Label>
              <Input
                id="session-timeout"
                type="number"
                min="15"
                max="1440"
                value={safeNumberValue(localSecuritySettings?.session_timeout_minutes)}
                onChange={(e) => setLocalSecuritySettings({...localSecuritySettings, session_timeout_minutes: parseInt(e.target.value) || 15})}
                className="mt-2"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="audit-logs">Audit Logs</Label>
                <p className="text-sm text-muted-foreground">
                  Keep detailed logs of all agent actions
                </p>
              </div>
              <Switch 
                id="audit-logs" 
                checked={localSecuritySettings.audit_logs_enabled}
                onCheckedChange={(checked) => setLocalSecuritySettings({...localSecuritySettings, audit_logs_enabled: checked})}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="require-2fa">Require 2FA</Label>
                <p className="text-sm text-muted-foreground">
                  Require two-factor authentication for all users
                </p>
              </div>
              <Switch 
                id="require-2fa" 
                checked={localSecuritySettings.require_2fa}
                onCheckedChange={(checked) => setLocalSecuritySettings({...localSecuritySettings, require_2fa: checked})}
              />
            </div>

            <div className="flex justify-end pt-4 border-t">
              <Button 
                onClick={handleSaveSecuritySettings}
                disabled={updateSecurityMutation.isPending}
                className="min-w-[120px]"
              >
                {updateSecurityMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}