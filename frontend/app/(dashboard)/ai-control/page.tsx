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
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
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
  Bell,
  Plus,
  Trash2,
  Edit2,
  ChevronUp,
  ChevronDown
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

// Risk Matrix Editor Component
interface RiskMatrixEditorProps {
  isOpen: boolean;
  onClose: () => void;
  riskMatrix: Record<string, string[]>;
  onSave: (newMatrix: Record<string, string[]>) => void;
}

function RiskMatrixEditor({ isOpen, onClose, riskMatrix, onSave }: RiskMatrixEditorProps) {
  const [editedMatrix, setEditedMatrix] = useState<Record<string, string[]>>(riskMatrix);
  const [newActionInput, setNewActionInput] = useState<Record<string, string>>({
    low: '',
    medium: '',
    high: ''
  });

  // Reset when dialog opens
  useEffect(() => {
    if (isOpen) {
      setEditedMatrix(JSON.parse(JSON.stringify(riskMatrix)));
    }
  }, [isOpen, riskMatrix]);

  const handleAddAction = (level: string) => {
    const newAction = newActionInput[level]?.trim();
    if (!newAction) return;

    setEditedMatrix(prev => ({
      ...prev,
      [level]: [...(prev[level] || []), newAction]
    }));
    setNewActionInput(prev => ({ ...prev, [level]: '' }));
  };

  const handleRemoveAction = (level: string, index: number) => {
    setEditedMatrix(prev => ({
      ...prev,
      [level]: prev[level].filter((_, i) => i !== index)
    }));
  };

  const handleMoveAction = (fromLevel: string, toLevel: string, index: number) => {
    const action = editedMatrix[fromLevel][index];
    setEditedMatrix(prev => ({
      ...prev,
      [fromLevel]: prev[fromLevel].filter((_, i) => i !== index),
      [toLevel]: [...prev[toLevel], action]
    }));
  };

  const handleSave = () => {
    onSave(editedMatrix);
    onClose();
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'text-red-600 border-red-300 bg-red-50';
      case 'medium':
        return 'text-yellow-600 border-yellow-300 bg-yellow-50';
      case 'low':
        return 'text-green-600 border-green-300 bg-green-50';
      default:
        return '';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Customize Risk Matrix</DialogTitle>
          <DialogDescription>
            Define which actions fall into each risk category. Drag actions between categories or add new ones.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[500px] pr-4">
          <div className="space-y-6">
            {['low', 'medium', 'high'].map((level) => (
              <div key={level} className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={getLevelColor(level)}
                  >
                    {level} risk
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {editedMatrix[level]?.length || 0} actions
                  </span>
                </div>

                <div className={`border-2 rounded-lg p-4 ${getLevelColor(level)}`}>
                  <div className="space-y-2">
                    {editedMatrix[level]?.map((action, index) => (
                      <div
                        key={`${level}-${index}`}
                        className="flex items-center justify-between bg-white rounded-md p-2 shadow-sm"
                      >
                        <span className="text-sm">{action}</span>
                        <div className="flex items-center gap-1">
                          {level !== 'low' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                const targetLevel = level === 'high' ? 'medium' : 'low';
                                handleMoveAction(level, targetLevel, index);
                              }}
                              title={`Move to ${level === 'high' ? 'medium' : 'low'} risk`}
                            >
                              <ChevronDown className="h-4 w-4" />
                            </Button>
                          )}
                          {level !== 'high' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                const targetLevel = level === 'low' ? 'medium' : 'high';
                                handleMoveAction(level, targetLevel, index);
                              }}
                              title={`Move to ${level === 'low' ? 'medium' : 'high'} risk`}
                            >
                              <ChevronUp className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleRemoveAction(level, index)}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-3 flex gap-2">
                    <Input
                      placeholder={`Add new ${level} risk action...`}
                      value={newActionInput[level]}
                      onChange={(e) => setNewActionInput(prev => ({ ...prev, [level]: e.target.value }))}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          handleAddAction(level);
                        }
                      }}
                      className="flex-1"
                    />
                    <Button
                      size="sm"
                      onClick={() => handleAddAction(level)}
                      disabled={!newActionInput[level]?.trim()}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function AIControlPage() {
  const [isEmergencyStopActive, setIsEmergencyStopActive] = useState(false);
  const [isRiskMatrixEditorOpen, setIsRiskMatrixEditorOpen] = useState(false);
  const queryClient = useQueryClient();

  // Fetch AI config
  const { data: configData, isLoading } = useQuery({
    queryKey: queryKeys.aiConfig,
    queryFn: () => apiClient.getAIConfig(),
  });

  // Fetch safety config
  const { data: safetyConfigData } = useQuery({
    queryKey: queryKeys.safetyConfig,
    queryFn: () => apiClient.getSafetyConfig(),
  });

  // Fetch pending approvals
  const { data: pendingApprovalsData } = useQuery({
    queryKey: queryKeys.pendingApprovals,
    queryFn: () => apiClient.getPendingApprovals(),
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch action history
  const { data: actionHistoryData } = useQuery({
    queryKey: queryKeys.actionHistory,
    queryFn: () => apiClient.getActionHistory(),
  });

  // Fetch confidence history
  const { data: confidenceHistoryData } = useQuery({
    queryKey: queryKeys.confidenceHistory,
    queryFn: () => apiClient.getConfidenceHistory(),
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

  const updateSafetyConfigMutation = useMutation({
    mutationFn: (updates: any) => apiClient.updateSafetyConfig(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.safetyConfig });
      toast.success('Safety configuration updated');
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

  const dryRunMutation = useMutation({
    mutationFn: (actionPlan: any[]) => apiClient.executeDryRun(actionPlan),
    onSuccess: (result) => {
      toast.success('Dry run completed', {
        description: `Simulated ${result.data?.length || 0} actions`,
      });
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: (actionId: string) => apiClient.rollbackAgentAction(actionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.actionHistory });
      toast.success('Action rolled back successfully');
    },
  });

  const approvalMutation = useMutation({
    mutationFn: ({ approvalId, action, comments }: { approvalId: string; action: 'approve' | 'reject'; comments?: string }) => 
      action === 'approve' 
        ? apiClient.approveAction(approvalId, comments)
        : apiClient.rejectAction(approvalId, comments),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.pendingApprovals });
      toast.success('Approval processed');
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

  // Safety configuration data
  const safetyConfig = safetyConfigData?.data || {
    dry_run_mode: false,
    confidence_threshold: 0.8,
    risk_tolerance: 'medium',
    auto_execute_permissions: {},
    emergency_stop_active: false,
  };

  const pendingApprovals = pendingApprovalsData?.data || [];
  const actionHistory = actionHistoryData?.data || [];
  const confidenceHistory = confidenceHistoryData?.data || [];

  // Safety handlers
  const handleSafetyConfigChange = (updates: any) => {
    updateSafetyConfigMutation.mutate(updates);
  };

  const handleDryRunTest = () => {
    const testActions = [
      { type: 'restart_pod', target: 'test-service' },
      { type: 'scale_deployment', replicas: 3 }
    ];
    dryRunMutation.mutate(testActions);
  };

  const handleApproval = (approvalId: string, action: 'approve' | 'reject', comments?: string) => {
    approvalMutation.mutate({ approvalId, action, comments });
  };

  const handleRollback = (actionId: string) => {
    rollbackMutation.mutate(actionId);
  };

  const handleSaveRiskMatrix = (newMatrix: Record<string, string[]>) => {
    updateConfigMutation.mutate({
      risk_matrix: newMatrix as {
        low: string[];
        medium: string[];
        high: string[];
      }
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
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="automation">Safety & Automation</TabsTrigger>
          <TabsTrigger value="risk-config">Risk Configuration</TabsTrigger>
          <TabsTrigger value="approvals">Approvals & History</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="automation">
          <Card>
            <CardHeader>
              <CardTitle>Safety & Automation Settings</CardTitle>
              <CardDescription>
                Configure safety controls, confidence thresholds, and execution behavior
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Dry Run Mode */}
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label htmlFor="dry-run-mode" className="text-base">
                    Dry Run Mode
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Simulate all actions without executing them
                  </p>
                </div>
                <Switch
                  id="dry-run-mode"
                  checked={safetyConfig.dry_run_mode}
                  onCheckedChange={(checked) => handleSafetyConfigChange({ dry_run_mode: checked })}
                />
              </div>

              <Separator />

              {/* Confidence Threshold */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-base">Safety Confidence Threshold</Label>
                  <Badge variant={safetyConfig.confidence_threshold >= 0.8 ? 'default' : 'destructive'}>
                    {Math.round(safetyConfig.confidence_threshold * 100)}%
                  </Badge>
                </div>
                <Slider
                  value={[safetyConfig.confidence_threshold * 100]}
                  onValueChange={(value) => handleSafetyConfigChange({ confidence_threshold: value[0] / 100 })}
                  max={100}
                  min={0}
                  step={5}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0% (Execute all)</span>
                  <span>100% (Only high confidence)</span>
                </div>
              </div>

              <Separator />

              {/* Auto-execute Settings */}
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

              {/* Safety Testing */}
              <div className="space-y-4">
                <h4 className="text-sm font-medium">Safety Testing</h4>
                <div className="space-y-3">
                  <Button
                    variant="outline"
                    onClick={handleDryRunTest}
                    disabled={dryRunMutation.isPending}
                    className="w-full"
                  >
                    <Terminal className="h-4 w-4 mr-2" />
                    Test Dry Run Simulation
                  </Button>
                  
                  {/* Show confidence score if available */}
                  {confidenceHistory.length > 0 && (
                    <div className="p-3 bg-blue-50 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <Brain className="h-4 w-4 text-blue-600" />
                        <span className="text-sm font-medium">Latest Confidence Score</span>
                      </div>
                      <div className="text-2xl font-bold text-blue-600">
                        {Math.round(confidenceHistory[confidenceHistory.length - 1]?.confidence * 100 || 0)}%
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <Separator />

              {/* Execution Preferences */}
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
                <Button 
                  variant="outline"
                  onClick={() => setIsRiskMatrixEditorOpen(true)}
                >
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

        <TabsContent value="approvals">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Pending Approvals */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  Pending Approvals
                  {pendingApprovals.length > 0 && (
                    <Badge variant="destructive">{pendingApprovals.length}</Badge>
                  )}
                </CardTitle>
                <CardDescription>
                  Actions awaiting human approval
                </CardDescription>
              </CardHeader>
              <CardContent>
                {pendingApprovals.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-600" />
                    <p>No pending approvals</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {pendingApprovals.slice(0, 3).map((approval: any) => (
                      <div key={approval.id} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <Badge variant="outline">{approval.incident_id}</Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(approval.requested_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="space-y-2">
                          <p className="text-sm font-medium">
                            Confidence: {Math.round(approval.confidence_score?.overall_confidence * 100 || 0)}%
                          </p>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              onClick={() => handleApproval(approval.id, 'approve')}
                              disabled={approvalMutation.isPending}
                            >
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleApproval(approval.id, 'reject')}
                              disabled={approvalMutation.isPending}
                            >
                              <XCircle className="h-3 w-3 mr-1" />
                              Reject
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Action History & Rollbacks */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <RefreshCw className="h-5 w-5" />
                  Action History
                </CardTitle>
                <CardDescription>
                  Recent AI actions with rollback capability
                </CardDescription>
              </CardHeader>
              <CardContent>
                {actionHistory.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Activity className="h-12 w-12 mx-auto mb-4" />
                    <p>No actions executed yet</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {actionHistory.slice(0, 5).map((action: any) => (
                      <div key={action.id} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary">{action.action_type}</Badge>
                            {action.rollback_executed && (
                              <Badge variant="outline">Rolled Back</Badge>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {new Date(action.executed_at).toLocaleTimeString()}
                          </span>
                        </div>
                        {action.rollback_available && !action.rollback_executed && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleRollback(action.id)}
                            disabled={rollbackMutation.isPending}
                          >
                            <RefreshCw className="h-3 w-3 mr-1" />
                            Rollback
                          </Button>
                        )}
                      </div>
                    ))}
                    
                    {/* Rollback Last Action Button */}
                    <div className="pt-4 border-t">
                      <Button
                        variant="destructive"
                        onClick={() => rollbackMutation.mutate('last')}
                        disabled={rollbackMutation.isPending || actionHistory.filter((a: any) => a.rollback_available && !a.rollback_executed).length === 0}
                        className="w-full"
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Emergency Rollback Last Action
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
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

      {/* Risk Matrix Editor Dialog */}
      <RiskMatrixEditor
        isOpen={isRiskMatrixEditorOpen}
        onClose={() => setIsRiskMatrixEditorOpen(false)}
        riskMatrix={config.risk_matrix}
        onSave={handleSaveRiskMatrix}
      />
    </section>
  );
}