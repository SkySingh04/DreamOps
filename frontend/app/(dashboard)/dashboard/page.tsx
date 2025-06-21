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
import { Activity, AlertCircle, CheckCircle, Clock, TrendingUp, Shield, Server } from 'lucide-react';
import { useWebSocket } from '@/lib/hooks/use-websocket';

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
  const [teamId, setTeamId] = useState<number | null>(null);

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

  // Get team ID from user session
  useEffect(() => {
    async function fetchTeamId() {
      try {
        const response = await fetch('/api/user/team');
        if (response.ok) {
          const { teamId: userTeamId } = await response.json();
          setTeamId(userTeamId);
        } else {
          // Fallback to team 1 for testing
          setTeamId(1);
        }
      } catch (error) {
        console.error('Error fetching team ID:', error);
        // Fallback to team 1 for testing
        setTeamId(1);
      }
    }
    
    fetchTeamId();
  }, []);

  // Set up WebSocket for real-time updates
  const { isConnected } = useWebSocket({
    teamId: teamId || undefined,
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
          <h1 className="text-2xl font-bold">Oncall AI Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Real-time incident monitoring and AI-powered resolution
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge 
            variant="outline" 
            className={`px-3 py-1 ${
              isConnected 
                ? 'bg-blue-50 text-blue-700 border-blue-300' 
                : 'bg-gray-50 text-gray-700 border-gray-300'
            }`}
          >
            <span className={`mr-2 h-2 w-2 rounded-full ${
              isConnected ? 'bg-blue-600' : 'bg-gray-600'
            }`}></span>
            {isConnected ? 'Live' : 'Disconnected'}
          </Badge>
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
        </div>
      </div>
      
      {/* Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
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

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Avg Response Time
            </CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metricsLoading ? '...' : currentMetrics.avgResponseTime}
            </div>
            <p className="text-xs text-gray-600">
              Target: &lt; 5 min
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              System Health
            </CardTitle>
            <Activity className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {metricsLoading ? '...' : `${currentMetrics.healthScore}%`}
            </div>
            <Progress value={currentMetrics.healthScore} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {incidentsLoading ? (
                <div className="text-sm text-gray-500">Loading incidents...</div>
              ) : incidents && incidents.length > 0 ? (
                incidents.map((incident) => (
                  <div key={incident.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertCircle className={`h-4 w-4 ${
                        incident.severity === 'critical' ? 'text-red-500' :
                        incident.severity === 'high' ? 'text-orange-500' :
                        incident.severity === 'medium' ? 'text-yellow-500' :
                        'text-blue-500'
                      }`} />
                      <span className="text-sm truncate">{incident.title}</span>
                    </div>
                    <Badge 
                      variant={
                        incident.status === 'resolved' ? 'secondary' :
                        incident.severity === 'critical' ? 'destructive' :
                        'outline'
                      } 
                      className="text-xs"
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

        <Card>
          <CardHeader>
            <CardTitle>AI Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {aiActionsLoading ? (
                <div className="text-sm text-gray-500">Loading AI actions...</div>
              ) : aiActions && aiActions.length > 0 ? (
                aiActions.map((action) => (
                  <div key={action.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-green-500" />
                      <span className="text-sm truncate">
                        {action.description || action.action}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date(action.createdAt).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-sm text-gray-500">No recent AI actions</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}