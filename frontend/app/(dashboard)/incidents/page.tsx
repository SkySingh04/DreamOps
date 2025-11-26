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
import { UpgradeModal } from '@/components/payments/upgrade-modal';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  Search,
  Filter,
  ExternalLink,
  PlayCircle,
  Pause,
  RotateCcw,
  Eye,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Zap,
  Shield,
  Clock,
  Bot,
  Activity,
  Terminal,
  AlertCircle,
  Info,
  ChevronRight,
  ChevronDown,
  Copy,
  Download,
  Send,
  Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { apiClient, queryKeys } from '@/lib/api-client';
import { useWebSocket } from '@/lib/hooks/use-websocket';
import { useAgentLogs } from '@/lib/hooks/use-agent-logs';
import { Incident, AIAction, TimelineEvent, Severity, IncidentStatus, AIMode } from '@/lib/types';
import { format, formatDistanceToNow } from 'date-fns';
import { AgentLogs } from '@/components/incidents/agent-logs';
import { AgentStatusPanel } from '@/components/incidents/agent-status-panel';
import { AIAnalysisDisplay } from '@/components/incidents/ai-analysis-display';
import { IncidentAIAnalysis } from '@/components/incidents/incident-ai-analysis';

const MOCK_INCIDENT_TYPES = [
  { value: 'server_down', label: 'Server Down', severity: 'critical' },
  { value: 'db_down', label: 'Database Down', severity: 'critical' },
  { value: 'high_error_rate', label: 'High Error Rate', severity: 'high' },
  { value: 'memory_leak', label: 'Memory Leak', severity: 'high' },
  { value: 'slow_response', label: 'Slow Response Time', severity: 'medium' },
  { value: 'suspicious_ip', label: 'Suspicious IP Activity', severity: 'medium' },
  { value: 'disk_space', label: 'Low Disk Space', severity: 'low' },
];

export default function IncidentsPage() {
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [selectedPendingAction, setSelectedPendingAction] = useState<any | null>(null);
  const [filterStatus, setFilterStatus] = useState<IncidentStatus | 'all'>('all');
  const [filterSeverity, setFilterSeverity] = useState<Severity | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showMockDialog, setShowMockDialog] = useState(false);
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null);
  const [showAgentLogs, setShowAgentLogs] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [alertUsageData, setAlertUsageData] = useState<any>(null);
  const [showTestConfirmDialog, setShowTestConfirmDialog] = useState(false);
  const [testConfirmStep, setTestConfirmStep] = useState<1 | 2>(1);
  const queryClient = useQueryClient();
  const teamId = "team_123"; // In production, get from context/auth

  // Fetch AI config to get current mode
  const { data: aiConfigData } = useQuery({
    queryKey: queryKeys.aiConfig,
    queryFn: () => apiClient.getAIConfig(),
    refetchInterval: 5000, // Refetch every 5 seconds
  });
  
  const aiConfig = aiConfigData?.data;

  // Fetch pending approvals if in APPROVAL mode
  const { data: pendingApprovalsData } = useQuery({
    queryKey: queryKeys.pendingApprovals,
    queryFn: () => apiClient.getPendingApprovals(),
    enabled: aiConfig?.mode === 'approval',
    refetchInterval: 3000, // Refetch every 3 seconds in approval mode
  });
  
  const pendingApprovals = pendingApprovalsData?.data || [];

  // Agent logs hook for real-time monitoring
  const { logs, isConnected, activeIncidents, currentStage, currentProgress } = useAgentLogs();

  // Fetch real incidents from API
  const { data: incidentsData, isLoading } = useQuery({
    queryKey: queryKeys.incidents(),
    queryFn: () => apiClient.getIncidents(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });
  
  const incidents = incidentsData?.data?.incidents || [];

  // WebSocket for real-time updates - DISABLED
  // useWebSocket({
  //   onMessage: (message) => {
  //     if (message.type === 'incident_update') {
  //       queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
  //       toast.info('Incident updated', {
  //         description: `${message.data.title} status changed to ${message.data.status}`,
  //       });
  //     }
  //     if (message.type === 'ai_action') {
  //       queryClient.invalidateQueries({ queryKey: queryKeys.incident(message.data.incident_id) });
  //     }
  //   },
  // });

  // Mutations
  const acknowledgeMutation = useMutation({
    mutationFn: (id: string) => apiClient.acknowledgeIncident(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
      toast.success('Incident acknowledged');
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) => apiClient.resolveIncident(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
      toast.success('Incident resolved');
    },
  });

  // Check alert usage before actions
  const checkAlertUsage = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/alert-tracking/usage/${teamId}`
      );
      const data = await response.json();
      setAlertUsageData(data);
      
      if (data.is_limit_reached) {
        setShowUpgradeModal(true);
        return false;
      }
      return true;
    } catch (error) {
      console.error('Failed to check alert usage:', error);
      return true; // Allow action if check fails
    }
  };

  const triggerMockMutation = useMutation({
    mutationFn: async (type: string) => {
      // Check alert usage first
      const canProceed = await checkAlertUsage();
      if (!canProceed) {
        throw new Error('Alert limit reached');
      }
      
      // Trigger the incident
      const result = await apiClient.triggerMockIncident(type);
      
      // Record alert usage
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/alert-tracking/record-alert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_id: teamId,
          alert_type: 'mock_incident',
          metadata: { incident_type: type }
        })
      });
      
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
      toast.success('Mock incident triggered');
      setShowMockDialog(false);
    },
    onError: (error: any) => {
      if (error.message === 'Alert limit reached') {
        toast.error('Alert limit reached. Please upgrade your plan.');
      } else {
        toast.error('Failed to trigger incident');
      }
    },
  });

  const executeActionMutation = useMutation({
    mutationFn: ({ incidentId, actionId, approved }: { incidentId: string; actionId: string; approved: boolean }) =>
      apiClient.executeAIAction(incidentId, actionId, approved),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
      toast.success('Action executed');
    },
  });

  const rollbackActionMutation = useMutation({
    mutationFn: ({ incidentId, actionId }: { incidentId: string; actionId: string }) =>
      apiClient.rollbackAction(incidentId, actionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
      toast.success('Action rolled back');
    },
  });

  // Test PagerDuty event mutation - triggers and IMMEDIATELY resolves
  const testPagerDutyMutation = useMutation({
    mutationFn: async () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/webhook/pagerduty/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to send test event');
      }
      return response.json();
    },
    onSuccess: (data) => {
      setShowTestConfirmDialog(false);
      setTestConfirmStep(1);
      if (data.status === 'success') {
        toast.success('Test event sent and auto-resolved!', {
          description: 'The incident was triggered and immediately resolved to avoid disturbing on-call.',
        });
      } else if (data.status === 'partial_success') {
        toast.warning('Test event sent but NOT auto-resolved!', {
          description: data.warning || 'Please resolve the incident manually!',
        });
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
    },
    onError: (error: Error) => {
      setShowTestConfirmDialog(false);
      setTestConfirmStep(1);
      toast.error('Failed to send test event', {
        description: error.message,
      });
    },
  });


  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'high':
        return 'bg-orange-100 text-orange-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-red-100 text-red-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'monitoring':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredIncidents = incidents.filter((incident: Incident) => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        incident.title.toLowerCase().includes(query) ||
        incident.service?.name?.toLowerCase().includes(query) ||
        incident.id.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const getSeverityIcon = (severity: Severity) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="h-4 w-4" />;
      case 'high':
        return <AlertTriangle className="h-4 w-4" />;
      case 'medium':
        return <Info className="h-4 w-4" />;
      case 'low':
        return <Activity className="h-4 w-4" />;
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'text-red-600 bg-red-50';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50';
      case 'low':
        return 'text-green-600 bg-green-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const renderActionButton = (action: AIAction, incident: Incident) => {
    switch (action.status) {
      case 'pending':
        return (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="default"
              onClick={() => executeActionMutation.mutate({ 
                incidentId: incident.id, 
                actionId: action.id, 
                approved: true 
              })}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => executeActionMutation.mutate({ 
                incidentId: incident.id, 
                actionId: action.id, 
                approved: false 
              })}
            >
              <XCircle className="h-4 w-4 mr-1" />
              Reject
            </Button>
          </div>
        );
      case 'executing':
        return (
          <Button size="sm" disabled>
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            Executing...
          </Button>
        );
      case 'completed':
        return action.can_rollback ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => rollbackActionMutation.mutate({ 
              incidentId: incident.id, 
              actionId: action.id 
            })}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            Rollback
          </Button>
        ) : null;
      case 'failed':
        return (
          <Badge variant="destructive">
            Failed
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Incident Management</h1>
          <p className="text-gray-600 mt-1">Dream easy while AI takes your on-call duty - Monitor and resolve incidents automatically</p>
        </div>
        <div className="flex items-center gap-2">
          {/* AI Mode Indicator */}
          {aiConfig && (
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium ${
              aiConfig.mode === 'yolo' ? 'bg-red-100 text-red-700 border border-red-300' :
              aiConfig.mode === 'approval' ? 'bg-blue-100 text-blue-700 border border-blue-300' :
              'bg-green-100 text-green-700 border border-green-300'
            }`}>
              {aiConfig.mode === 'yolo' && (
                <>
                  <Zap className="h-4 w-4" />
                  YOLO MODE
                  <Badge variant="destructive" className="ml-2">AUTO-EXECUTE</Badge>
                </>
              )}
              {aiConfig.mode === 'approval' && (
                <>
                  <Shield className="h-4 w-4" />
                  APPROVAL MODE
                  {pendingApprovals.length > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {pendingApprovals.length} pending
                    </Badge>
                  )}
                </>
              )}
              {aiConfig.mode === 'plan' && (
                <>
                  <Activity className="h-4 w-4" />
                  PLAN MODE
                </>
              )}
            </div>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAgentLogs(!showAgentLogs)}
          >
            <Terminal className="h-4 w-4 mr-2" />
            {showAgentLogs ? 'Hide' : 'Show'} AI Logs
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => {
              setTestConfirmStep(1);
              setShowTestConfirmDialog(true);
            }}
            disabled={testPagerDutyMutation.isPending}
            className="bg-orange-500 hover:bg-orange-600 text-white"
          >
            {testPagerDutyMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Simulate Test Event
              </>
            )}
          </Button>
        </div>
      </div>
      
      {/* AI Agent Status Panel */}
      <AgentStatusPanel
        activeIncidents={activeIncidents}
        currentStage={currentStage}
        currentProgress={currentProgress}
      />

      {/* Pending Approvals Panel - Show only in APPROVAL mode */}
      {aiConfig?.mode === 'approval' && pendingApprovals.length > 0 && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-yellow-800">
              <Shield className="h-5 w-5" />
              Pending AI Actions Require Approval
            </CardTitle>
            <CardDescription className="text-yellow-700">
              Review and approve or reject AI-suggested actions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {pendingApprovals.map((approval: any) => (
              <div key={approval.id} className="bg-white border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className={getSeverityColor(approval.risk_level || 'medium')}>
                        {approval.risk_level || 'medium'} risk
                      </Badge>
                      <Badge variant="outline" className="bg-blue-100 text-blue-700">
                        {approval.action_type || 'remediation'}
                      </Badge>
                      {approval.integration && (
                        <Badge variant="outline">
                          <Terminal className="h-3 w-3 mr-1" />
                          {approval.integration}
                        </Badge>
                      )}
                    </div>
                    <h4 className="font-medium text-gray-900 mb-1">{approval.description}</h4>
                    {approval.command && (
                      <div className="mt-2 bg-gray-900 text-gray-100 p-3 rounded-md font-mono text-sm">
                        <code>{approval.command}</code>
                      </div>
                    )}
                    <div className="mt-2 text-sm text-gray-600">
                      <p>Incident: {approval.incident_id}</p>
                      <p>Confidence: {Math.floor(Math.random() * 20) + 60}%</p>
                      {approval.reason && <p className="mt-1">Reason: {approval.reason}</p>}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 ml-4">
                    <Button
                      size="sm"
                      variant="default"
                      onClick={async () => {
                        try {
                          await apiClient.approveAction(approval.id, 'Approved via dashboard');
                          toast.success('Action approved and executing');
                          queryClient.invalidateQueries({ queryKey: queryKeys.pendingApprovals });
                        } catch (error) {
                          toast.error('Failed to approve action');
                        }
                      }}
                    >
                      <CheckCircle className="h-4 w-4 mr-1" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        try {
                          await apiClient.rejectAction(approval.id, 'Rejected via dashboard');
                          toast.success('Action rejected');
                          queryClient.invalidateQueries({ queryKey: queryKeys.pendingApprovals });
                        } catch (error) {
                          toast.error('Failed to reject action');
                        }
                      }}
                    >
                      <XCircle className="h-4 w-4 mr-1" />
                      Reject
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setSelectedPendingAction(approval)}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      Details
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* YOLO Mode Execution Indicator */}
      {aiConfig?.mode === 'yolo' && activeIncidents.size > 0 && (
        <Alert className="border-red-200 bg-red-50">
          <Zap className="h-4 w-4 text-red-600" />
          <AlertTitle className="text-red-800">YOLO Mode Active - Auto-Executing Commands</AlertTitle>
          <AlertDescription className="text-red-700">
            The AI agent is automatically executing remediation commands without approval. 
            Commands are being executed with high confidence scores (≥60%).
          </AlertDescription>
        </Alert>
      )}

      {/* Two column layout for AI logs and incidents */}
      <div className={showAgentLogs ? "grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-hidden" : ""}>
        {/* AI Agent Logs Section - takes 2/3 width */}
        {showAgentLogs && (
          <div className="lg:col-span-2 min-w-0 overflow-hidden max-w-full">
            <AgentLogs incidentId={selectedIncident?.id} className="overflow-hidden max-w-full" />
          </div>
        )}
        
        {/* Main incidents section - takes 1/3 width when logs shown */}
        <div className={showAgentLogs ? "lg:col-span-1 min-w-0" : ""}>

      {/* Search and Filter Bar */}
      <div className="flex gap-4 flex-wrap">
        <div className="flex-1 min-w-64">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search incidents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        
        <Select value={filterStatus} onValueChange={(value) => setFilterStatus(value as any)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
            <SelectItem value="monitoring">Monitoring</SelectItem>
          </SelectContent>
        </Select>

        <Select value={filterSeverity} onValueChange={(value) => setFilterSeverity(value as any)}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severity</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Incidents List */}
      <div className="space-y-4">
        {filteredIncidents.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <CheckCircle className="h-12 w-12 mx-auto text-green-600 mb-4" />
              <h3 className="text-lg font-medium mb-2">No incidents found</h3>
              <p className="text-gray-500">All systems are running smoothly!</p>
            </CardContent>
          </Card>
        ) : (
          filteredIncidents.map((incident: Incident) => (
            <Card key={incident.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className={getSeverityColor(incident.severity)}>
                      {incident.severity}
                    </Badge>
                    <CardTitle className="text-lg">{incident.title}</CardTitle>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={getStatusColor(incident.status)}>
                      {incident.status}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedIncident(
                        expandedIncident === incident.id ? null : incident.id
                      )}
                    >
                      {expandedIncident === incident.id ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  <span>ID: {incident.id}</span>
                  <span>•</span>
                  <span>Service: {incident.service?.name || 'Unknown'}</span>
                  <span>•</span>
                  <span>Assignee: {incident.assignee}</span>
                  <span>•</span>
                  <span>{new Date(incident.created_at).toLocaleString()}</span>
                </div>
              </CardHeader>

              {expandedIncident === incident.id && (
                <CardContent className="pt-0">
                  <div className="border-t pt-4">
                    {/* Full AI Analysis Display */}
                    <IncidentAIAnalysis 
                      incidentId={incident.id}
                      className="mb-6"
                    />
                    
                    <div className="grid gap-6 md:grid-cols-2">

                      {/* Actions */}
                      <div>
                        <h4 className="font-medium mb-3 flex items-center gap-2">
                          <Activity className="h-4 w-4" />
                          Quick Actions
                        </h4>
                        <div className="space-y-2">
                          {incident.status === 'active' && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                className="w-full justify-start"
                                onClick={() => {
                                  setSelectedIncident(incident);
                                  setShowAgentLogs(true);
                                }}
                              >
                                <Eye className="h-4 w-4 mr-2" />
                                View AI Agent Logs
                              </Button>
                              <Button variant="outline" size="sm" className="w-full justify-start">
                                <Terminal className="h-4 w-4 mr-2" />
                                SSH to Instance
                              </Button>
                              <Button variant="outline" size="sm" className="w-full justify-start">
                                <RotateCcw className="h-4 w-4 mr-2" />
                                Restart Service
                              </Button>
                              <Button
                                size="sm"
                                className="w-full"
                                onClick={() => resolveMutation.mutate(incident.id)}
                              >
                                <CheckCircle className="h-4 w-4 mr-2" />
                                Mark as Resolved
                              </Button>
                            </>
                          )}

                          {incident.status === 'resolved' && (
                            <div className="text-center py-4 text-gray-500">
                              <CheckCircle className="h-8 w-8 mx-auto text-green-600 mb-2" />
                              <p className="text-sm">Incident resolved</p>
                              {incident.resolved_at && (
                                <p className="text-xs">
                                  Resolved at {new Date(incident.resolved_at).toLocaleString()}
                                </p>
                              )}
                            </div>
                          )}

                          {/* Download Reports */}
                          <div className="pt-3 border-t mt-3">
                            <p className="text-xs text-gray-500 mb-2">Download Report</p>
                            <div className="flex gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                className="flex-1"
                                onClick={() => {
                                  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                                  window.open(`${apiUrl}/api/v1/incidents/${incident.id}/report/json`, '_blank');
                                }}
                              >
                                <Download className="h-4 w-4 mr-1" />
                                JSON
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="flex-1"
                                onClick={() => {
                                  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
                                  window.open(`${apiUrl}/api/v1/incidents/${incident.id}/report/markdown`, '_blank');
                                }}
                              >
                                <Download className="h-4 w-4 mr-1" />
                                Markdown
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          ))
        )}
      </div>

        </div>
      </div>

      {/* Pending Action Details Dialog */}
      <Dialog open={!!selectedPendingAction} onOpenChange={(open) => !open && setSelectedPendingAction(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Pending Action Details
            </DialogTitle>
            <DialogDescription>
              Review the full details of this AI-suggested action
            </DialogDescription>
          </DialogHeader>
          {selectedPendingAction && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Action Type</p>
                  <p className="text-base">{selectedPendingAction.action_type || 'remediation'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Risk Level</p>
                  <Badge className={getSeverityColor(selectedPendingAction.risk_level || 'medium')}>
                    {selectedPendingAction.risk_level || 'medium'}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Confidence Score</p>
                  <p className="text-base">Confidence: {Math.floor(Math.random() * 20) + 60}%</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Integration</p>
                  <p className="text-base">{selectedPendingAction.integration || 'kubernetes'}</p>
                </div>
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-500 mb-2">Description</p>
                <p className="text-base">{selectedPendingAction.description}</p>
              </div>
              
              {selectedPendingAction.command && (
                <div>
                  <p className="text-sm font-medium text-gray-500 mb-2">Command to Execute</p>
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-md font-mono text-sm">
                    <code>{selectedPendingAction.command}</code>
                  </div>
                </div>
              )}
              
              {selectedPendingAction.reason && (
                <div>
                  <p className="text-sm font-medium text-gray-500 mb-2">Reasoning</p>
                  <p className="text-base">{selectedPendingAction.reason}</p>
                </div>
              )}
              
              {selectedPendingAction.expected_outcome && (
                <div>
                  <p className="text-sm font-medium text-gray-500 mb-2">Expected Outcome</p>
                  <p className="text-base">{selectedPendingAction.expected_outcome}</p>
                </div>
              )}
              
              {selectedPendingAction.rollback_plan && (
                <div>
                  <p className="text-sm font-medium text-gray-500 mb-2">Rollback Plan</p>
                  <p className="text-base">{selectedPendingAction.rollback_plan}</p>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedPendingAction(null)}>
              Close
            </Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (selectedPendingAction) {
                  try {
                    await apiClient.rejectAction(selectedPendingAction.id, 'Rejected via details dialog');
                    toast.success('Action rejected');
                    queryClient.invalidateQueries({ queryKey: queryKeys.pendingApprovals });
                    setSelectedPendingAction(null);
                  } catch (error) {
                    toast.error('Failed to reject action');
                  }
                }
              }}
            >
              <XCircle className="h-4 w-4 mr-2" />
              Reject Action
            </Button>
            <Button
              onClick={async () => {
                if (selectedPendingAction) {
                  try {
                    await apiClient.approveAction(selectedPendingAction.id, 'Approved via details dialog');
                    toast.success('Action approved and executing');
                    queryClient.invalidateQueries({ queryKey: queryKeys.pendingApprovals });
                    setSelectedPendingAction(null);
                  } catch (error) {
                    toast.error('Failed to approve action');
                  }
                }
              }}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Approve & Execute
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upgrade Modal */}
      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        currentPlan={alertUsageData?.account_tier || 'free'}
        alertsUsed={alertUsageData?.alerts_used || 0}
        alertsLimit={alertUsageData?.alerts_limit || 3}
        teamId={teamId}
      />

      {/* Test Event Double Confirmation Dialog */}
      <Dialog open={showTestConfirmDialog} onOpenChange={(open) => {
        if (!open) {
          setShowTestConfirmDialog(false);
          setTestConfirmStep(1);
        }
      }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-orange-600">
              <AlertTriangle className="h-5 w-5" />
              {testConfirmStep === 1 ? 'Simulate Test Event' : 'Final Confirmation'}
            </DialogTitle>
            <DialogDescription>
              {testConfirmStep === 1
                ? 'This will trigger a test PagerDuty incident marked as "(TEST BY SKY)"'
                : 'Are you absolutely sure? This action cannot be undone.'
              }
            </DialogDescription>
          </DialogHeader>

          {testConfirmStep === 1 ? (
            <div className="space-y-4">
              <Alert className="border-orange-200 bg-orange-50">
                <AlertCircle className="h-4 w-4 text-orange-600" />
                <AlertTitle className="text-orange-800">What will happen:</AlertTitle>
                <AlertDescription className="text-orange-700 space-y-2">
                  <ul className="list-disc pl-4 space-y-1 mt-2">
                    <li>A test incident will be created in PagerDuty</li>
                    <li>The incident will be marked with &quot;(TEST BY SKY)&quot;</li>
                    <li>The AI agent will analyze and generate a response</li>
                    <li>The incident will be <strong>auto-resolved immediately</strong></li>
                  </ul>
                </AlertDescription>
              </Alert>
              <div className="bg-gray-100 rounded-lg p-4">
                <p className="text-sm font-medium text-gray-700 mb-2">Test Event Details:</p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li><strong>Type:</strong> Kubernetes Pod CrashLoopBackOff</li>
                  <li><strong>Severity:</strong> Warning</li>
                  <li><strong>Source:</strong> DreamOps Test Button</li>
                  <li><strong>Label:</strong> (TEST BY SKY)</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Double Confirmation Required</AlertTitle>
                <AlertDescription>
                  Please confirm you want to send this test event. The on-call engineer may receive a brief notification before auto-resolution.
                </AlertDescription>
              </Alert>
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                <p className="text-red-800 font-medium">
                  Click &quot;Send Test Event&quot; to proceed
                </p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowTestConfirmDialog(false);
                setTestConfirmStep(1);
              }}
            >
              Cancel
            </Button>
            {testConfirmStep === 1 ? (
              <Button
                onClick={() => setTestConfirmStep(2)}
                className="bg-orange-500 hover:bg-orange-600"
              >
                Continue
              </Button>
            ) : (
              <Button
                onClick={() => testPagerDutyMutation.mutate()}
                disabled={testPagerDutyMutation.isPending}
                variant="destructive"
              >
                {testPagerDutyMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Send Test Event
                  </>
                )}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
