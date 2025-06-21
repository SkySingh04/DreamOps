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
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { 
  Bot, 
  Shield, 
  Zap, 
  AlertTriangle, 
  CheckCircle,
  XCircle,
  Settings,
  Activity,
  Brain,
  Lock,
  Unlock,
  Info,
  StopCircle,
  PlayCircle,
  RefreshCw,
  Terminal,
  Gauge,
  FileText,
  Bell
} from 'lucide-react';
import { toast } from 'sonner';
import { apiClient, queryKeys } from '@/lib/api-client';
import { AIAgentConfig, AIMode, RiskLevel } from '@/lib/types';

const AI_MODES = [
  {
    value: 'yolo' as AIMode,
    label: 'YOLO Mode',
    description: 'Fully autonomous - AI executes all actions without approval',
    icon: Zap,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
  },
  {
    value: 'plan' as AIMode,
    label: 'Plan Mode',
    description: 'AI creates action plans but waits for review before execution',
    icon: FileText,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-300',
  },
  {
    value: 'approval' as AIMode,
    label: 'Approval Mode',
    description: 'AI requires explicit approval for medium and high-risk actions',
    icon: Lock,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-300',
  },
];

const RISK_ACTIONS = {
  low: [
    'Read metrics and logs',
    'Query monitoring systems',
    'Generate reports',
    'Send notifications',
    'Update incident status',
  ],
  medium: [
    'Restart services',
    'Scale deployments',
    'Clear caches',
    'Rotate credentials',
    'Update configurations',
  ],
  high: [
    'Delete resources',
    'Modify production data',
    'Change security settings',
    'Perform database operations',
    'Execute custom scripts',
  ],
};

export default function AIControlPage() {
  const [isEmergencyStopActive, setIsEmergencyStopActive] = useState(false);
  const queryClient = useQueryClient();

  // Fetch AI config
  const { data: configData, isLoading } = useQuery({
    queryKey: queryKeys.aiConfig,
    queryFn: () => apiClient.getAIConfig(),
  });

  const config = configData?.data || {
    mode: 'approval' as AIMode,
    confidence_threshold: 70,
    risk_matrix: RISK_ACTIONS,
    auto_execute_enabled: true,
    approval_required_for: ['medium', 'high'] as RiskLevel[],
    notification_preferences: {
      slack_enabled: true,
      email_enabled: false,
      channels: [],
    },
  };

  // Mutations
  const updateConfigMutation = useMutation({
    mutationFn: (updates: Partial<AIAgentConfig>) => apiClient.updateAIConfig(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.aiConfig });
      toast.success('AI agent configuration updated');
    },
  });

  const emergencyStopMutation = useMutation({
    mutationFn: () => apiClient.emergencyStop(),
    onSuccess: () => {
      setIsEmergencyStopActive(true);
      toast.error('Emergency stop activated', {
        description: 'All AI actions have been halted',
      });
    },
  });

  const handleModeChange = (mode: AIMode) => {
    let approvalRequired: RiskLevel[] = [];
    
    switch (mode) {
      case 'yolo':
        approvalRequired = [];
        break;
      case 'plan':
        approvalRequired = ['low', 'medium', 'high'];
        break;
      case 'approval':
        approvalRequired = ['medium', 'high'];
        break;
    }

    updateConfigMutation.mutate({
      mode,
      approval_required_for: approvalRequired,
    });
  };

  const handleConfidenceChange = (value: number[]) => {
    updateConfigMutation.mutate({
      confidence_threshold: value[0],
    });
  };

  const handleAutoExecuteToggle = (enabled: boolean) => {
    updateConfigMutation.mutate({
      auto_execute_enabled: enabled,
    });
  };

  const handleNotificationToggle = (type: 'slack' | 'email', enabled: boolean) => {
    updateConfigMutation.mutate({
      notification_preferences: {
        ...config.notification_preferences,
        [`${type}_enabled`]: enabled,
      },
    });
  };

  const getRiskLevelStats = () => {
    const stats = {
      low: { allowed: 0, restricted: 0 },
      medium: { allowed: 0, restricted: 0 },
      high: { allowed: 0, restricted: 0 },
    };

    Object.entries(RISK_ACTIONS).forEach(([level, actions]) => {
      const isRestricted = config.approval_required_for.includes(level as RiskLevel);
      stats[level as RiskLevel] = {
        allowed: isRestricted ? 0 : actions.length,
        restricted: isRestricted ? actions.length : 0,
      };
    });

    return stats;
  };

  if (isLoading) {
    return (
      <div className="flex-1 p-4 lg:p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const riskStats = getRiskLevelStats();

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Agent Control Panel</h1>
          <p className="text-muted-foreground mt-1">
            Configure AI behavior, risk thresholds, and automation settings
          </p>
        </div>
        <Button
          variant={isEmergencyStopActive ? 'outline' : 'destructive'}
          size="lg"
          onClick={() => {
            if (isEmergencyStopActive) {
              setIsEmergencyStopActive(false);
              toast.success('AI agent resumed');
            } else {
              emergencyStopMutation.mutate();
            }
          }}
          disabled={emergencyStopMutation.isPending}
        >
          {isEmergencyStopActive ? (
            <>
              <PlayCircle className="h-5 w-5 mr-2" />
              Resume AI Agent
            </>
          ) : (
            <>
              <StopCircle className="h-5 w-5 mr-2" />
              Emergency Stop
            </>
          )}
        </Button>
      </div>

      {isEmergencyStopActive && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Emergency Stop Active</AlertTitle>
          <AlertDescription>
            All AI actions are currently halted. Click "Resume AI Agent" to restore normal operation.
          </AlertDescription>
        </Alert>
      )}

      {/* AI Mode Selection */}
      <Card>
        <CardHeader>
          <CardTitle>AI Operation Mode</CardTitle>
          <CardDescription>
            Select how autonomous the AI agent should be when responding to incidents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={config.mode}
            onValueChange={(value) => handleModeChange(value as AIMode)}
          >
            <div className="grid gap-4">
              {AI_MODES.map((mode) => {
                const Icon = mode.icon;
                const isSelected = config.mode === mode.value;
                
                return (
                  <div
                    key={mode.value}
                    className={`relative rounded-lg border-2 p-4 cursor-pointer transition-all ${
                      isSelected 
                        ? `${mode.borderColor} ${mode.bgColor}` 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => handleModeChange(mode.value)}
                  >
                    <div className="flex items-start gap-4">
                      <RadioGroupItem
                        value={mode.value}
                        id={mode.value}
                        className="mt-1"
                      />
                      <div className={`p-2 rounded-lg ${mode.bgColor}`}>
                        <Icon className={`h-5 w-5 ${mode.color}`} />
                      </div>
                      <div className="flex-1">
                        <Label
                          htmlFor={mode.value}
                          className="text-base font-semibold cursor-pointer"
                        >
                          {mode.label}
                        </Label>
                        <p className="text-sm text-muted-foreground mt-1">
                          {mode.description}
                        </p>
                      </div>
                      {isSelected && (
                        <Badge variant="secondary">Active</Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {/* Confidence and Risk Settings */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Confidence Threshold */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-5 w-5" />
              Confidence Threshold
            </CardTitle>
            <CardDescription>
              Only execute actions above this confidence score
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-2xl font-bold">
                    {config.confidence_threshold}%
                  </span>
                  <Badge
                    variant={config.confidence_threshold >= 80 ? 'default' :
                             config.confidence_threshold >= 60 ? 'secondary' :
                             'destructive'}
                  >
                    {config.confidence_threshold >= 80 ? 'Conservative' :
                     config.confidence_threshold >= 60 ? 'Balanced' :
                     'Aggressive'}
                  </Badge>
                </div>
                <Slider
                  value={[config.confidence_threshold]}
                  onValueChange={handleConfidenceChange}
                  max={100}
                  min={0}
                  step={5}
                  className="w-full"
                />
                <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                  <span>0% (Execute all)</span>
                  <span>100% (Very certain)</span>
                </div>
              </div>
              
              <Separator />
              
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Confidence Guidelines</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-600"></div>
                    <span>80-100%: High confidence, minimal risk</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-yellow-600"></div>
                    <span>60-79%: Moderate confidence, some uncertainty</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-red-600"></div>
                    <span>Below 60%: Low confidence, high uncertainty</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Risk Matrix Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Risk Matrix Overview
            </CardTitle>
            <CardDescription>
              Current restrictions based on your selected mode
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(riskStats).map(([level, stats]) => (
                <div key={level} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={
                          level === 'high' ? 'text-red-700 border-red-300' :
                          level === 'medium' ? 'text-yellow-700 border-yellow-300' :
                          'text-green-700 border-green-300'
                        }
                      >
                        {level} risk
                      </Badge>
                      <span className="text-sm font-medium capitalize">
                        {RISK_ACTIONS[level as RiskLevel].length} actions
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      {stats.allowed > 0 && (
                        <span className="flex items-center gap-1 text-green-600">
                          <CheckCircle className="h-3 w-3" />
                          {stats.allowed} auto
                        </span>
                      )}
                      {stats.restricted > 0 && (
                        <span className="flex items-center gap-1 text-yellow-600">
                          <Lock className="h-3 w-3" />
                          {stats.restricted} approval
                        </span>
                      )}
                    </div>
                  </div>
                  <Progress
                    value={(stats.allowed / (stats.allowed + stats.restricted)) * 100}
                    className="h-2"
                  />
                </div>
              ))}
            </div>

            <Alert className="mt-6">
              <Info className="h-4 w-4" />
              <AlertDescription>
                In <strong>{config.mode}</strong> mode, {
                  config.mode === 'yolo' 
                    ? 'all actions execute automatically' 
                    : config.mode === 'plan'
                    ? 'all actions require review'
                    : 'medium and high-risk actions require approval'
                }
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>

      {/* Advanced Settings */}
      <Tabs defaultValue="automation" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="automation">Automation</TabsTrigger>
          <TabsTrigger value="risk-config">Risk Configuration</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="automation">
          <Card>
            <CardHeader>
              <CardTitle>Automation Settings</CardTitle>
              <CardDescription>
                Configure automatic execution and behavior settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="auto-execute" className="text-base">
                    Auto-execute approved actions
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically execute actions that meet confidence threshold
                  </p>
                </div>
                <Switch
                  id="auto-execute"
                  checked={config.auto_execute_enabled}
                  onCheckedChange={handleAutoExecuteToggle}
                />
              </div>

              <Separator />

              <div className="space-y-4">
                <h4 className="text-sm font-medium">Execution Preferences</h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="batch-actions" className="text-sm">
                      Batch similar actions
                    </Label>
                    <Switch id="batch-actions" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="parallel-exec" className="text-sm">
                      Allow parallel execution
                    </Label>
                    <Switch id="parallel-exec" defaultChecked />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="dry-run" className="text-sm">
                      Enable dry-run for high-risk actions
                    </Label>
                    <Switch id="dry-run" defaultChecked />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="risk-config">
          <Card>
            <CardHeader>
              <CardTitle>Risk Configuration</CardTitle>
              <CardDescription>
                Define what actions fall into each risk category
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {Object.entries(RISK_ACTIONS).map(([level, actions]) => (
                  <div key={level} className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={
                          level === 'high' ? 'text-red-700 border-red-300' :
                          level === 'medium' ? 'text-yellow-700 border-yellow-300' :
                          'text-green-700 border-green-300'
                        }
                      >
                        {level} risk
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {config.approval_required_for.includes(level as RiskLevel) 
                          ? 'Requires approval' 
                          : 'Auto-execute allowed'}
                      </span>
                    </div>
                    <div className="pl-4 space-y-1">
                      {actions.map((action, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <div className="w-1.5 h-1.5 rounded-full bg-gray-400"></div>
                          <span>{action}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex justify-end">
                <Button variant="outline">
                  <Settings className="h-4 w-4 mr-2" />
                  Customize Risk Matrix
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notification Preferences</CardTitle>
              <CardDescription>
                Configure how you want to be notified about AI actions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <svg className="h-5 w-5 text-purple-600" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M14.82 4.26a10.14 10.14 0 0 0-.53 1.1 14.66 14.66 0 0 0-4.58 0 10.14 10.14 0 0 0-.53-1.1 16 16 0 0 0-4.13 1.3 17.33 17.33 0 0 0-3 11.59 16.6 16.6 0 0 0 5.07 2.59A12.89 12.89 0 0 0 8.23 18a9.65 9.65 0 0 1-1.71-.83 3.39 3.39 0 0 0 .42-.33 11.66 11.66 0 0 0 10.12 0q.21.18.42.33a10.84 10.84 0 0 1-1.71.84 12.41 12.41 0 0 0 1.08 1.78 16.44 16.44 0 0 0 5.06-2.59 17.22 17.22 0 0 0-3-11.59 16.09 16.09 0 0 0-4.09-1.35zM8.68 14.81a1.94 1.94 0 0 1-1.8-2 1.93 1.93 0 0 1 1.8-2 1.93 1.93 0 0 1 1.8 2 1.93 1.93 0 0 1-1.8 2zm6.64 0a1.94 1.94 0 0 1-1.8-2 1.93 1.93 0 0 1 1.8-2 1.92 1.92 0 0 1 1.8 2 1.92 1.92 0 0 1-1.8 2z"/>
                      </svg>
                    </div>
                    <div>
                      <Label htmlFor="slack-notifications" className="text-base">
                        Slack Notifications
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Send alerts to configured Slack channels
                      </p>
                    </div>
                  </div>
                  <Switch
                    id="slack-notifications"
                    checked={config.notification_preferences.slack_enabled}
                    onCheckedChange={(checked) => handleNotificationToggle('slack', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Bell className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <Label htmlFor="email-notifications" className="text-base">
                        Email Notifications
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Send alerts to team email addresses
                      </p>
                    </div>
                  </div>
                  <Switch
                    id="email-notifications"
                    checked={config.notification_preferences.email_enabled}
                    onCheckedChange={(checked) => handleNotificationToggle('email', checked)}
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h4 className="text-sm font-medium">Notification Events</h4>
                <div className="space-y-3">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded" />
                    <span className="text-sm">High-risk actions requiring approval</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded" />
                    <span className="text-sm">Actions that fail or encounter errors</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded" />
                    <span className="text-sm">Critical severity incidents</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" className="rounded" />
                    <span className="text-sm">All AI agent activities</span>
                  </label>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Recent Configuration Changes */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Configuration Changes</CardTitle>
          <CardDescription>
            Audit trail of AI agent configuration modifications
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-start gap-3 text-sm">
              <RefreshCw className="h-4 w-4 text-blue-600 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">Mode changed to {config.mode}</p>
                <p className="text-muted-foreground">By current user • Just now</p>
              </div>
            </div>
            <div className="flex items-start gap-3 text-sm">
              <Settings className="h-4 w-4 text-gray-600 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">Confidence threshold updated to {config.confidence_threshold}%</p>
                <p className="text-muted-foreground">By current user • 2 minutes ago</p>
              </div>
            </div>
            <div className="flex items-start gap-3 text-sm">
              <Bell className="h-4 w-4 text-purple-600 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">Slack notifications enabled</p>
                <p className="text-muted-foreground">By admin • 1 hour ago</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}