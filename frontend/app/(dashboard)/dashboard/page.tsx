'use client';

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Activity, AlertCircle, CheckCircle, Clock, TrendingUp, Shield, Server, RefreshCw, Settings } from 'lucide-react';
import { useWebSocket } from '@/lib/hooks/use-websocket';
import { Button } from '@/components/ui/button';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { AlertUsageCard } from '@/components/dashboard/alert-usage-card';

interface DashboardMetrics {
  activeIncidents: number;
  resolvedToday: number;
  avgResponseTime: string;
  healthScore: number;
  aiAgentStatus: 'online' | 'offline';
}

interface RecentIncident {
  id: number;
  title: string;
  severity: string;
  status: string;
  createdAt: string;
}

interface RecentAiAction {
  id: number;
  action: string;
  description: string | null;
  createdAt: string;
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [userId, setUserId] = useState<number | null>(null);
  const [showRollbackPlan, setShowRollbackPlan] = useState(false);
  const [rollbackPlanData, setRollbackPlanData] = useState<any>(null);

  // Fetch dashboard metrics
  const { data: metrics, isLoading: metricsLoading } = useQuery<DashboardMetrics>({
    queryKey: ['dashboard-metrics'],
    queryFn: async () => {
      const response = await fetch('/api/public/dashboard/metrics');
      if (!response.ok) throw new Error('Failed to fetch metrics');
      return response.json();
    },
    refetchInterval: 5000, // Refetch every 5 seconds for real-time feel
  });

  // Fetch recent incidents
  const { data: incidents, isLoading: incidentsLoading } = useQuery<RecentIncident[]>({
    queryKey: ['recent-incidents'],
    queryFn: async () => {
      const response = await fetch('/api/public/dashboard/incidents?limit=5');
      if (!response.ok) throw new Error('Failed to fetch incidents');
      return response.json();
    },
    refetchInterval: 5000,
  });

  // Fetch recent AI actions
  const { data: aiActions, isLoading: aiActionsLoading } = useQuery<RecentAiAction[]>({
    queryKey: ['recent-ai-actions'],
    queryFn: async () => {
      const response = await fetch('/api/public/dashboard/ai-actions?limit=5');
      if (!response.ok) throw new Error('Failed to fetch AI actions');
      return response.json();
    },
    refetchInterval: 5000,
  });

  // Rollback mutation
  const rollbackMutation = useMutation({
    mutationFn: async () => {
      // First, try to rollback the last action
      const response = await fetch('/api/v1/agent/rollback-last', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      const rollbackData = await response.json();
      
      // If no actions to rollback, generate a rollback plan using AI
      if (!response.ok || (rollbackData.success === false)) {
        const planResponse = await fetch('/api/v1/agent/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            incident_id: 'rollback-plan-' + Date.now(),
            incident_details: {
              title: 'Generate Rollback Plan',
              description: 'User requested a rollback plan for recent AI actions',
              severity: 'low',
              service: 'ai-agent'
            },
            context: {
              request_type: 'rollback_plan',
              recent_actions: aiActions?.slice(0, 5) || [],
              auto_remediate: false,
              instructions: 'Analyze the recent AI actions and provide a comprehensive rollback plan. Include specific steps to reverse or mitigate the effects of recent automated actions.'
            }
          }),
        });
        
        if (!planResponse.ok) {
          throw new Error('Failed to generate rollback plan');
        }
        
        const planData = await planResponse.json();
        return {
          success: false,
          rollbackPlan: planData.analysis?.summary || 'Unable to generate rollback plan',
          analysis: planData.analysis,
          recommended_actions: planData.analysis?.recommended_actions
        };
      }
      
      return rollbackData;
    },
    onSuccess: (data) => {
      if (data.success === false && data.rollbackPlan) {
        // Store the rollback plan data
        setRollbackPlanData({
          plan: data.rollbackPlan,
          analysis: data.analysis,
          recommended_actions: data.recommended_actions,
          timestamp: new Date().toISOString()
        });
        setShowRollbackPlan(true);
        
        toast.success('AI Rollback Plan Generated', {
          description: 'Check the rollback plan below',
        });
      } else if (data.success) {
        toast.success('Rollback executed successfully', {
          description: data.message || data.details,
        });
        queryClient.invalidateQueries({ queryKey: ['recent-ai-actions'] });
        setShowRollbackPlan(false);
        setRollbackPlanData(null);
      } else {
        toast.warning('No actions to rollback', {
          description: data.error || 'All recent actions have been rolled back or are not reversible',
        });
      }
    },
    onError: (error) => {
      toast.error('Failed to initiate rollback', {
        description: error.message,
      });
    },
  });

  // Get user ID from user session
  useEffect(() => {
    async function fetchUserId() {
      try {
        const response = await fetch('/api/user');
        if (response.ok) {
          const user = await response.json();
          setUserId(user.id);
        } else {
          // Fallback to user 1 for testing
          setUserId(1);
        }
      } catch (error) {
        console.error('Error fetching user ID:', error);
        // Fallback to user 1 for testing
        setUserId(1);
      }
    }
    
    fetchUserId();
  }, []);

  // Set up WebSocket for real-time updates
  const { isConnected } = useWebSocket({
    userId: userId || undefined,
    onMetricsUpdate: (newMetrics) => {
      queryClient.setQueryData(['dashboard-metrics'], newMetrics);
    },
    onIncidentUpdate: (incident) => {
      queryClient.invalidateQueries({ queryKey: ['recent-incidents'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-metrics'] });
    },
    onAiActionUpdate: (action) => {
      queryClient.invalidateQueries({ queryKey: ['recent-ai-actions'] });
    },
  });

  // Default values for loading states
  const defaultMetrics: DashboardMetrics = {
    activeIncidents: 0,
    resolvedToday: 0,
    avgResponseTime: '0 min',
    healthScore: 95,
    aiAgentStatus: 'online'
  };

  const currentMetrics = metrics || defaultMetrics;


  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">DreamOps Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time incident monitoring and AI-powered resolution
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge 
            variant="outline" 
            className={`px-3 py-1 ${
              currentMetrics.aiAgentStatus === 'online' 
                ? 'bg-green-50 text-green-700 border-green-300' 
                : 'bg-red-50 text-red-700 border-red-300'
            }`}
          >
            <span className={`mr-2 h-2 w-2 rounded-full ${
              currentMetrics.aiAgentStatus === 'online' ? 'bg-green-600' : 'bg-red-600'
            }`}></span>
            AI Agent {currentMetrics.aiAgentStatus === 'online' ? 'Online' : 'Offline'}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push('/dashboard/general')}
            className="flex items-center gap-2"
          >
            <Settings className="h-4 w-4" />
            Settings
          </Button>
        </div>
      </div>
      
      {/* Alert Usage Card */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <AlertUsageCard userId={userId?.toString()} className="lg:col-span-1" />
      </div>
      
      {/* Metrics Grid with Recent Incidents */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Active Incidents
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metricsLoading ? '...' : currentMetrics.activeIncidents}
            </div>
            <p className="text-xs text-gray-600">
              Requires immediate attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Resolved Today
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metricsLoading ? '...' : currentMetrics.resolvedToday}
            </div>
            <p className="text-xs text-gray-600">
              <TrendingUp className="inline h-3 w-3 mr-1" />
              +12% from yesterday
            </p>
          </CardContent>
        </Card>

        <Card className="md:col-span-2 lg:col-span-3">
          <CardHeader>
            <CardTitle>Recent Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
              {incidentsLoading ? (
                <div className="text-sm text-gray-500">Loading incidents...</div>
              ) : incidents && incidents.length > 0 ? (
                incidents.map((incident) => (
                  <div key={incident.id} className="flex items-center justify-between pb-2 border-b border-gray-100 last:border-b-0">
                    <div className="flex items-center gap-2 flex-1">
                      <AlertCircle className={`h-4 w-4 flex-shrink-0 ${
                        incident.severity === 'critical' ? 'text-red-500' :
                        incident.severity === 'high' ? 'text-orange-500' :
                        incident.severity === 'medium' ? 'text-yellow-500' :
                        'text-blue-500'
                      }`} />
                      <span className="text-sm">{incident.title}</span>
                    </div>
                    <Badge 
                      variant={
                        incident.status === 'resolved' ? 'secondary' :
                        incident.severity === 'critical' ? 'destructive' :
                        'outline'
                      } 
                      className="text-xs ml-2 flex-shrink-0"
                    >
                      {incident.status === 'resolved' ? 'Resolved' : 
                       incident.severity === 'critical' ? 'Critical' :
                       incident.severity === 'high' ? 'High' :
                       'Active'}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="text-sm text-gray-500">No recent incidents</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Rollback Plan Section */}
      {showRollbackPlan && rollbackPlanData && (
        <Card className="border-2 border-orange-200 bg-orange-50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className="h-5 w-5 text-orange-600" />
                AI Generated Rollback Plan
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowRollbackPlan(false);
                  setRollbackPlanData(null);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-white p-4 rounded-lg border border-orange-200">
              <h4 className="font-semibold text-sm mb-2">Summary</h4>
              <p className="text-sm text-gray-700">{rollbackPlanData.plan}</p>
            </div>
            
            {rollbackPlanData.analysis?.root_cause && (
              <div className="bg-white p-4 rounded-lg border border-orange-200">
                <h4 className="font-semibold text-sm mb-2">Root Cause Analysis</h4>
                <p className="text-sm text-gray-700">{rollbackPlanData.analysis.root_cause}</p>
              </div>
            )}
            
            {rollbackPlanData.recommended_actions && rollbackPlanData.recommended_actions.length > 0 && (
              <div className="bg-white p-4 rounded-lg border border-orange-200">
                <h4 className="font-semibold text-sm mb-2">Recommended Actions</h4>
                <ol className="space-y-2">
                  {rollbackPlanData.recommended_actions.map((action: any, index: number) => (
                    <li key={index} className="text-sm">
                      <span className="font-medium">{index + 1}. {action.action || action.type}:</span>
                      <span className="text-gray-700 ml-1">{action.reason}</span>
                      {action.estimated_impact && (
                        <span className="text-xs text-gray-500 block ml-4">Impact: {action.estimated_impact}</span>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            )}
            
            <div className="text-xs text-gray-500 text-right">
              Generated at {new Date(rollbackPlanData.timestamp).toLocaleTimeString()}
            </div>
          </CardContent>
        </Card>
      )}

      {/* AI Actions */}
      <Card>
        <CardHeader>
          <CardTitle>AI Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 max-h-40 overflow-y-auto overflow-x-hidden pr-2 custom-scrollbar">
            {aiActionsLoading ? (
              <div className="text-sm text-gray-500">Loading AI actions...</div>
            ) : aiActions && aiActions.length > 0 ? (
              aiActions.map((action) => (
                <div key={action.id} className="space-y-1 pb-2 border-b border-gray-100 last:border-b-0">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-2 flex-1 min-w-0">
                      <Shield className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-sm break-words">
                        {action.description || action.action}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
                      {new Date(action.createdAt).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-gray-500">No recent AI actions</div>
            )}
          </div>
          
          {/* Rollback Button */}
          {aiActions && aiActions.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <Button
                onClick={() => rollbackMutation.mutate()}
                disabled={rollbackMutation.isPending}
                variant="outline"
                size="default"
                className="w-full hover:bg-red-50 hover:text-red-700 hover:border-red-300 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${rollbackMutation.isPending ? 'animate-spin' : ''}`} />
                {rollbackMutation.isPending ? 'Generating Rollback Plan...' : 'Generate Rollback Plan'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}