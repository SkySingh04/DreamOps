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
  Loader2,
  Skull,
  Flame,
  Bomb,
  ShieldAlert,
  Siren
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
  const [showChaosDialog, setShowChaosDialog] = useState(false);
  const [showChaosConfirmDialog, setShowChaosConfirmDialog] = useState(false);
  const [showServiceSelector, setShowServiceSelector] = useState(false);
  const [chaosLoading, setChaosLoading] = useState(false);
  const [chaosResults, setChaosResults] = useState<string[]>([]);
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [serviceStatuses, setServiceStatuses] = useState<Record<string, 'pending' | 'loading' | 'success' | 'error'>>({});
  const [nukeProgress, setNukeProgress] = useState({ current: 0, total: 0 });
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null);
  const [showAgentLogs, setShowAgentLogs] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [alertUsageData, setAlertUsageData] = useState<any>(null);
  const queryClient = useQueryClient();
  const teamId = "team_123"; // In production, get from context/auth
  
  // Check if we're in dev mode
  const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true' || process.env.NODE_ENV === 'development';

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

  // Define the 5 chaos services from the script
  const chaosServices = [
    {
      id: 'pod_crash',
      name: 'Pod Crash',
      shortName: 'PODS',
      description: 'Simulate CrashLoopBackOff',
      icon: '💥',
      details: 'Creates pods that repeatedly crash and restart',
      severity: 'high'
    },
    {
      id: 'image_pull',
      name: 'Image Pull Error',
      shortName: 'IMAGES',
      description: 'Simulate ImagePullBackOff',
      icon: '🚫',
      details: 'Creates pods with non-existent images',
      severity: 'high'
    },
    {
      id: 'oom_kill',
      name: 'OOM Kill',
      shortName: 'MEMORY',
      description: 'Simulate memory exhaustion',
      icon: '💀',
      details: 'Creates memory-hungry pods that get killed',
      severity: 'critical'
    },
    {
      id: 'deployment_failure',
      name: 'Deployment Failure',
      shortName: 'DEPLOYS',
      description: 'Simulate failed deployments',
      icon: '⚠️',
      details: 'Creates deployments that fail to roll out',
      severity: 'medium'
    },
    {
      id: 'service_unavailable',
      name: 'Service Unavailable',
      shortName: 'SERVICES',
      description: 'Simulate broken services',
      icon: '🔴',
      details: 'Creates services with no working endpoints',
      severity: 'medium'
    }
  ];
  
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

  // Trigger PagerDuty alert for chaos action
  const triggerPagerDutyAlert = async (serviceId?: string) => {
    try {
      const response = await apiClient.post('/api/v1/chaos/trigger-alert', {
        service: serviceId,
        action: serviceId ? 'single' : 'all',
        description: serviceId 
          ? `Chaos engineering test: ${chaosServices.find(s => s.id === serviceId)?.name}`
          : 'Chaos engineering test: All services nuked'
      });
      
      if (response.status === 'success' && response.data.success) {
        console.log('✅ PagerDuty alert triggered successfully');
        toast.success('PagerDuty alert triggered!', {
          description: 'The oncall agent should start responding to the incident soon.'
        });
      } else {
        console.warn('⚠️ Failed to trigger PagerDuty alert:', response.data?.message || 'Unknown error');
        // Don't fail the chaos action if PagerDuty fails
      }
    } catch (error) {
      console.error('❌ Error triggering PagerDuty alert:', error);
      // Don't fail the chaos action if PagerDuty fails
    }
  };

  // Execute individual service chaos
  const executeServiceChaos = async (serviceId: string, retries = 2): Promise<{ success: boolean; results: string[]; error?: string }> => {
    const service = chaosServices.find(s => s.id === serviceId);
    if (!service) throw new Error(`Service ${serviceId} not found`);

    for (let attempt = 1; attempt <= retries + 1; attempt++) {
      try {
        console.log(`🔥 Attempting to nuke ${service.name} (attempt ${attempt}/${retries + 1})`);
        
        const response = await fetch('/api/chaos-engineering', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ service: serviceId })
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || `Failed to nuke ${service.name}`);
        }

        return {
          success: true,
          results: data.results || [`✅ ${service.name} successfully nuked!`]
        };

      } catch (error) {
        console.error(`❌ Failed to nuke ${service.name} (attempt ${attempt}):`, error);
        
        if (attempt === retries + 1) {
          return {
            success: false,
            results: [`❌ Failed to nuke ${service.name} after ${retries + 1} attempts`],
            error: error instanceof Error ? error.message : 'Unknown error'
          };
        }
        
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, 2000 * attempt));
      }
    }

    return { success: false, results: [], error: 'Max retries exceeded' };
  };

  const executeChaosEngineering = async (serviceId?: string) => {
    setChaosLoading(true);
    setChaosResults([]);
    setShowChaosDialog(true);
    setShowChaosConfirmDialog(false);
    setShowServiceSelector(false);
    
    try {
      const service = serviceId ? chaosServices.find(s => s.id === serviceId) : null;
      const isAllServices = !serviceId;
      
      // Initialize service statuses
      if (isAllServices) {
        const initialStatuses: Record<string, 'pending' | 'loading' | 'success' | 'error'> = {};
        chaosServices.forEach(s => {
          initialStatuses[s.id] = 'pending';
        });
        setServiceStatuses(initialStatuses);
        setNukeProgress({ current: 0, total: chaosServices.length });
      } else if (serviceId) {
        setServiceStatuses({ [serviceId]: 'loading' });
        setNukeProgress({ current: 0, total: 1 });
      }
      
      // Show initial loading message
      setChaosResults([
        `🔥 Initializing ${service ? service.name : 'ALL SERVICES'} chaos...`, 
        '⚡ Connecting to Kubernetes cluster...'
      ]);
      
      // Trigger PagerDuty alert first
      setChaosResults(prev => [...prev, '🚨 Triggering PagerDuty alert...']);
      await triggerPagerDutyAlert(serviceId);

      if (isAllServices) {
        // Sequential execution for "nuke all" to prevent conflicts
        setChaosResults(prev => [...prev, '', '🎯 NUCLEAR PROTOCOL: Sequential service destruction initiated', '']);
        
        let successCount = 0;
        let failureCount = 0;
        const allResults: string[] = [];

        for (let i = 0; i < chaosServices.length; i++) {
          const currentService = chaosServices[i];
          
          // Update current service status to loading
          setServiceStatuses(prev => ({ ...prev, [currentService.id]: 'loading' }));
          setNukeProgress({ current: i + 1, total: chaosServices.length });
          
          setChaosResults(prev => [
            ...prev, 
            `${currentService.icon} [${i + 1}/${chaosServices.length}] Nuking ${currentService.name}...`
          ]);

          const result = await executeServiceChaos(currentService.id);
          
          if (result.success) {
            successCount++;
            setServiceStatuses(prev => ({ ...prev, [currentService.id]: 'success' }));
            setChaosResults(prev => [
              ...prev, 
              `✅ [${i + 1}/${chaosServices.length}] ${currentService.name} successfully destroyed!`
            ]);
          } else {
            failureCount++;
            setServiceStatuses(prev => ({ ...prev, [currentService.id]: 'error' }));
            setChaosResults(prev => [
              ...prev, 
              `❌ [${i + 1}/${chaosServices.length}] ${currentService.name} failed: ${result.error}`
            ]);
          }
          
          allResults.push(...result.results);
          
          // Add delay between services to prevent conflicts
          if (i < chaosServices.length - 1) {
            setChaosResults(prev => [...prev, '⏳ Waiting 3 seconds before next service...']);
            await new Promise(resolve => setTimeout(resolve, 3000));
          }
        }

        // Final results
        setChaosResults(prev => [
          ...prev,
          '',
          `🎯 NUCLEAR RESULTS: ${successCount}/${chaosServices.length} services destroyed`,
          successCount === chaosServices.length ? '🎉 TOTAL INFRASTRUCTURE ANNIHILATION COMPLETE!' : 
          `⚠️ Partial success: ${failureCount} services failed to nuke`,
          '',
          '📋 Detailed Results:',
          ...allResults
        ]);

        toast.success(`Infrastructure chaos deployed! 💥`, {
          description: `${successCount}/${chaosServices.length} services successfully nuked`,
        });

      } else if (service) {
        // Single service execution
        setServiceStatuses({ [service.id]: 'loading' });
        
        const result = await executeServiceChaos(service.id);
        
        if (result.success) {
          setServiceStatuses({ [service.id]: 'success' });
          setChaosResults(prev => [
            ...prev,
            `${service.icon} Deploying ${service.name.toLowerCase()} simulation`,
            `📋 ${service.details}`,
            '📊 Triggering CloudWatch alarms...',
            '🎯 Activating PagerDuty alerts...',
            `✅ ${service.name} successfully compromised!`,
            '',
            '🎉 MISSION ACCOMPLISHED: Service chaos deployed!',
            '',
            '📋 Detailed Results:',
            ...result.results
          ]);
          
          toast.success(`${service.name} successfully nuked! 💥`, {
            description: 'Service chaos deployed successfully',
          });
        } else {
          setServiceStatuses({ [service.id]: 'error' });
          throw new Error(result.error || 'Service nuke failed');
        }
      }
      
      setChaosLoading(false);
      
    } catch (error) {
      setChaosLoading(false);
      setChaosResults(prev => [...prev, '', '❌ Chaos engineering failed:', error instanceof Error ? error.message : 'Unknown error']);
      toast.error('Chaos engineering failed', {
        description: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    }
  };

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
      {/* Prominent FUCK INFRA Button - Top Center - Only show in dev mode */}
      {isDevMode ? (
        <div className="flex justify-center mb-8">
          <Button 
            onClick={() => setShowServiceSelector(true)}
            className="bg-gradient-to-r from-red-600 via-red-700 to-red-800 hover:from-red-700 hover:via-red-800 hover:to-red-900 text-white border-red-600 shadow-2xl hover:shadow-3xl transform hover:scale-110 transition-all duration-300 font-bold text-3xl px-12 py-6 h-auto rounded-xl border-4 border-red-500 animate-pulse"
            disabled={chaosLoading}
            size="lg"
          >
            {chaosLoading ? (
              <>
                <Loader2 className="h-8 w-8 mr-4 animate-spin" />
                <Flame className="h-6 w-6 mr-2 animate-bounce" />
                NUKING INFRA...
                <Flame className="h-6 w-6 ml-2 animate-bounce" />
              </>
            ) : (
              <>
                <Bomb className="h-8 w-8 mr-4 animate-bounce" />
                <Flame className="h-6 w-6 mr-2" />
                NUKE INFRA
                <Flame className="h-6 w-6 ml-2" />
                <Skull className="h-8 w-8 ml-4 animate-bounce" />
              </>
            )}
          </Button>
        </div>
      ) : (
        <div className="flex justify-center mb-8">
          <Alert className="max-w-2xl border-yellow-200 bg-yellow-50">
            <ShieldAlert className="h-4 w-4 text-yellow-600" />
            <AlertTitle className="text-yellow-800">Chaos Engineering Disabled</AlertTitle>
            <AlertDescription className="text-yellow-700">
              The infrastructure nuke button is only available in development mode. 
              Set NEXT_PUBLIC_DEV_MODE=true or NODE_ENV=development to enable chaos engineering features.
            </AlertDescription>
          </Alert>
        </div>
      )}

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

      {/* Service Selector Modal */}
      <Dialog open={showServiceSelector} onOpenChange={setShowServiceSelector}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-center gap-3 text-3xl text-red-600 mb-4">
              <Bomb className="h-8 w-8 animate-pulse" />
              <Flame className="h-6 w-6" />
              INFRASTRUCTURE CHAOS CONTROL
              <Flame className="h-6 w-6" />
              <Skull className="h-8 w-8 animate-pulse" />
            </DialogTitle>
            <DialogDescription className="text-center text-lg">
              Choose your target or go nuclear with all services
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* Individual Service Options - Horizontal Cards */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-800 text-center">Choose Target Service</h3>
              <div className="space-y-3">
                {chaosServices.map((service) => (
                  <div 
                    key={service.id} 
                    className="w-full bg-white border-2 border-gray-200 hover:border-red-300 rounded-lg p-4 transition-all duration-200 min-h-[100px] flex items-center justify-between"
                  >
                    {/* Left: Icon */}
                    <div className="flex items-center justify-center w-16 h-16 bg-gray-50 rounded-lg border">
                      <span className="text-3xl">{service.icon}</span>
                    </div>
                    
                    {/* Middle: Service Info */}
                    <div className="flex-1 px-4">
                      <div className="flex items-center gap-3 mb-1">
                        <h4 className="text-lg font-semibold text-gray-800">{service.name}</h4>
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${
                            service.severity === 'critical' ? 'border-red-500 text-red-700 bg-red-50' :
                            service.severity === 'high' ? 'border-orange-500 text-orange-700 bg-orange-50' :
                            'border-yellow-500 text-yellow-700 bg-yellow-50'
                          }`}
                        >
                          {service.severity}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600">{service.description}</p>
                      <p className="text-xs text-gray-500 mt-1">{service.details}</p>
                    </div>
                    
                    {/* Right: NUKE Button */}
                    <div className="flex-shrink-0">
                      <Button
                        onClick={() => {
                          setSelectedService(service.id);
                          setShowChaosConfirmDialog(true);
                          setShowServiceSelector(false);
                        }}
                        className="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 text-sm rounded-lg shadow-md hover:shadow-lg transition-all duration-200 min-w-[140px]"
                        size="default"
                      >
                        <Flame className="h-4 w-4 mr-2" />
                        NUKE {service.shortName}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Nuclear Option - NUKE IT ALL */}
            <div className="border-t pt-6">
              <div className="text-center space-y-4">
                <div className="bg-red-50 border-2 border-red-300 rounded-lg p-6">
                  <div className="flex items-center justify-center mb-4">
                    <Bomb className="h-12 w-12 text-red-600 animate-pulse mr-4" />
                    <div>
                      <h3 className="text-2xl font-bold text-red-800">NUCLEAR OPTION</h3>
                      <p className="text-red-700">Destroy ALL 5 services simultaneously</p>
                    </div>
                    <Skull className="h-12 w-12 text-red-600 animate-pulse ml-4" />
                  </div>
                  <Button
                    onClick={() => {
                      setSelectedService(null);
                      setShowChaosConfirmDialog(true);
                      setShowServiceSelector(false);
                    }}
                    className="bg-gradient-to-r from-red-700 via-red-800 to-red-900 hover:from-red-800 hover:via-red-900 hover:to-black text-white font-bold text-xl px-8 py-4 h-auto rounded-lg shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200"
                    size="lg"
                  >
                    <Bomb className="h-6 w-6 mr-3" />
                    <Flame className="h-5 w-5 mr-2" />
                    💣 NUKE IT ALL 💣
                    <Flame className="h-5 w-5 ml-2" />
                    <Skull className="h-6 w-6 ml-3" />
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowServiceSelector(false)}>
              🛡️ Keep Infrastructure Safe
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Chaos Engineering Confirmation Dialog */}
      <Dialog open={showChaosConfirmDialog} onOpenChange={setShowChaosConfirmDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <ShieldAlert className="h-5 w-5" />
              ⚠️ {selectedService ? 'SERVICE' : 'INFRASTRUCTURE'} CHAOS WARNING ⚠️
            </DialogTitle>
            <DialogDescription className="text-center">
              <div className="space-y-4 mt-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-center justify-center mb-3">
                    <Bomb className="h-8 w-8 text-red-600 animate-pulse" />
                  </div>
                  {selectedService ? (
                    <>
                      {(() => {
                        const service = chaosServices.find(s => s.id === selectedService);
                        return service ? (
                          <>
                            <div className="flex items-center justify-center gap-3 mb-3">
                              <span className="text-4xl">{service.icon}</span>
                              <div>
                                <p className="text-red-800 font-bold text-lg">{service.name}</p>
                                <p className="text-red-700 text-sm">{service.description}</p>
                              </div>
                            </div>
                            <p className="text-red-700 text-sm mb-2">
                              Are you sure you want to nuke {service.name}?
                            </p>
                            <p className="text-red-600 text-xs">{service.details}</p>
                          </>
                        ) : null;
                      })()}
                    </>
                  ) : (
                    <>
                      <p className="text-red-800 font-semibold mb-2">
                        Are you absolutely sure you want to nuke ALL infrastructure?
                      </p>
                      <p className="text-red-700 text-sm">
                        This will intentionally break ALL 5 Kubernetes services:
                      </p>
                      <ul className="text-left text-sm text-red-700 mt-2 space-y-1">
                        {chaosServices.map(service => (
                          <li key={service.id}>• {service.name} ({service.description})</li>
                        ))}
                      </ul>
                    </>
                  )}
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-yellow-800 text-sm font-medium">
                    🔥 This will create real incidents and trigger PagerDuty alerts!
                  </p>
                </div>
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="sm:justify-center">
            <Button variant="outline" onClick={() => {
              setShowChaosConfirmDialog(false);
              setSelectedService(null);
            }}>
              🛡️ Keep Infrastructure Safe
            </Button>
            <Button 
              onClick={() => executeChaosEngineering(selectedService || undefined)}
              className="bg-red-600 hover:bg-red-700 text-white"
              disabled={chaosLoading}
            >
              {chaosLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Nuking...
                </>
              ) : (
                <>
                  <Skull className="h-4 w-4 mr-2" />
                  💣 {selectedService ? 'NUKE SERVICE' : 'NUKE IT ALL'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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

      {/* Chaos Results Dialog */}
      <Dialog open={showChaosDialog} onOpenChange={setShowChaosDialog}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Siren className="h-5 w-5 animate-pulse" />
              🔥 INFRASTRUCTURE CHAOS RESULTS 🔥
            </DialogTitle>
            <DialogDescription>
              Real-time chaos deployment status and results
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {/* Progress tracking for nuke all */}
            {nukeProgress.total > 1 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-blue-800">Nuclear Progress</span>
                  <span className="text-sm text-blue-600">{nukeProgress.current}/{nukeProgress.total} services</span>
                </div>
                <Progress value={(nukeProgress.current / nukeProgress.total) * 100} className="h-2" />
              </div>
            )}

            {/* Service status grid for nuke all */}
            {Object.keys(serviceStatuses).length > 1 && (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <h4 className="text-sm font-medium text-gray-800 mb-3">Service Status</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {chaosServices.map((service) => {
                    const status = serviceStatuses[service.id];
                    if (!status) return null;
                    
                    return (
                      <div key={service.id} className="flex items-center gap-2 text-sm">
                        <span className="text-lg">{service.icon}</span>
                        <span className="flex-1 truncate">{service.shortName}</span>
                        {status === 'pending' && <Clock className="h-4 w-4 text-gray-400" />}
                        {status === 'loading' && <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />}
                        {status === 'success' && <CheckCircle className="h-4 w-4 text-green-600" />}
                        {status === 'error' && <XCircle className="h-4 w-4 text-red-600" />}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Chaos logs */}
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-h-96 overflow-y-auto">
              {chaosResults.length > 0 ? (
                <div className="space-y-2">
                  {chaosResults.map((result, index) => (
                    <div key={index} className="flex items-start gap-2 text-sm">
                      <Flame className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                      <span className="text-red-800 font-mono">{result}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-red-600 mx-auto mb-2" />
                  <p className="text-red-700">Deploying chaos across infrastructure...</p>
                </div>
              )}
            </div>

            {/* Success/completion message */}
            {chaosResults.length > 0 && !chaosLoading && (
              <Alert className="border-yellow-200 bg-yellow-50">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <AlertTitle className="text-yellow-800">
                  {Object.keys(serviceStatuses).length > 1 ? 'Nuclear Mission Status' : 'Mission Accomplished!'}
                </AlertTitle>
                <AlertDescription className="text-yellow-700">
                  {Object.keys(serviceStatuses).length > 1 ? (
                    <>
                      {Object.values(serviceStatuses).filter(s => s === 'success').length} out of {Object.keys(serviceStatuses).length} services successfully destroyed.
                      Check your monitoring systems and PagerDuty for alerts.
                    </>
                  ) : (
                    'Infrastructure has been successfully compromised. Check your monitoring systems and PagerDuty for alerts. Your DreamOps agent should start analyzing and attempting to resolve these incidents automatically.'
                  )}
                </AlertDescription>
              </Alert>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowChaosDialog(false)}>
              Close Chaos Report
            </Button>
            <Button 
              onClick={() => {
                navigator.clipboard.writeText(chaosResults.join('\n'));
                toast.success('Chaos logs copied to clipboard');
              }}
              disabled={chaosResults.length === 0}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy Logs
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
    </section>
  );
}
