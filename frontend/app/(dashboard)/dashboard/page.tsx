'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  Activity, 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  TrendingUp,
  TrendingDown,
  Zap,
  Shield,
  Server,
  AlertTriangle,
  Info
} from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { apiClient, queryKeys } from '@/lib/api-client';
import { useWebSocket } from '@/lib/hooks/use-websocket';
import { DashboardMetrics, Incident, Integration } from '@/lib/types';
import { format } from 'date-fns';

const SEVERITY_COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#f59e0b',
  low: '#3b82f6',
};

const STATUS_COLORS = {
  active: '#dc2626',
  acknowledged: '#f59e0b',
  monitoring: '#3b82f6',
  resolved: '#10b981',
};

export default function DashboardPage() {
  const [realtimeMetrics, setRealtimeMetrics] = useState<Partial<DashboardMetrics>>({});
  
  // Fetch dashboard metrics
  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => apiClient.getDashboardMetrics(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch recent incidents
  const { data: incidentsData } = useQuery({
    queryKey: queryKeys.incidents({ limit: 10 }),
    queryFn: () => apiClient.getIncidents({ limit: 10 }),
  });

  // Fetch integrations status
  const { data: integrationsData } = useQuery({
    queryKey: queryKeys.integrations,
    queryFn: () => apiClient.getIntegrations(),
  });

  // WebSocket connection for real-time updates
  const { lastMessage } = useWebSocket({
    onMessage: (message) => {
      if (message.type === 'metric_update') {
        setRealtimeMetrics(prev => ({ ...prev, ...message.data }));
      }
    },
  });

  const metrics = {
    ...metricsData?.data,
    ...realtimeMetrics,
  } as DashboardMetrics;

  const incidents = incidentsData?.data || [];
  const integrations = integrationsData?.data || [];

  // Calculate integration health
  const integrationHealth = integrations.reduce(
    (acc, integration) => {
      if (integration.status === 'connected') acc.connected++;
      else if (integration.status === 'error') acc.errors++;
      return acc;
    },
    { connected: 0, errors: 0, total: integrations.length }
  );

  // Mock data for charts
  const incidentTrendData = [
    { hour: '00:00', incidents: 2 },
    { hour: '04:00', incidents: 1 },
    { hour: '08:00', incidents: 4 },
    { hour: '12:00', incidents: 3 },
    { hour: '16:00', incidents: 5 },
    { hour: '20:00', incidents: 2 },
  ];

  const severityDistribution = [
    { name: 'Critical', value: 15, color: SEVERITY_COLORS.critical },
    { name: 'High', value: 25, color: SEVERITY_COLORS.high },
    { name: 'Medium', value: 35, color: SEVERITY_COLORS.medium },
    { name: 'Low', value: 25, color: SEVERITY_COLORS.low },
  ];

  if (metricsLoading) {
    return (
      <div className="flex-1 p-4 lg:p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Oncall AI Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Real-time incident monitoring and AI-powered resolution
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge 
            variant="outline" 
            className={`px-3 py-1 ${
              metrics?.ai_agent_status === 'online' 
                ? 'bg-green-50 text-green-700 border-green-300' 
                : 'bg-red-50 text-red-700 border-red-300'
            }`}
          >
            <span className={`mr-2 h-2 w-2 rounded-full ${
              metrics?.ai_agent_status === 'online' ? 'bg-green-600' : 'bg-red-600'
            } inline-block animate-pulse`} />
            AI Agent: {metrics?.ai_agent_status || 'Unknown'}
          </Badge>
          <Badge variant="secondary" className="px-3 py-1">
            Mode: {metrics?.ai_mode?.toUpperCase() || 'Unknown'}
          </Badge>
        </div>
      </div>

      {/* Alert for critical incidents */}
      {metrics?.active_incidents > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Active Incidents</AlertTitle>
          <AlertDescription>
            There are {metrics.active_incidents} active incidents requiring attention.
          </AlertDescription>
        </Alert>
      )}

      {/* Key Metrics Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Incidents</CardTitle>
            <AlertCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.active_incidents || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {metrics?.active_incidents > 0 ? 'Requires immediate attention' : 'All clear'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Resolved Today</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.resolved_today || 0}</div>
            <Progress value={metrics?.success_rate || 0} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {metrics?.success_rate || 0}% success rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Resolution</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.avg_resolution_time || '0m'}</div>
            <p className="text-xs text-muted-foreground mt-1">
              <TrendingDown className="h-3 w-3 text-green-600 inline mr-1" />
              15% faster than last week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Time Saved</CardTitle>
            <Zap className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.time_saved_hours || 0}h</div>
            <p className="text-xs text-muted-foreground mt-1">
              By AI automation this month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Integration Health</CardTitle>
            <Server className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {integrationHealth.connected}/{integrationHealth.total}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {integrationHealth.errors > 0 && (
                <span className="text-red-600">{integrationHealth.errors} errors</span>
              )}
              {integrationHealth.errors === 0 && 'All systems operational'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts and Recent Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Incident Trend Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Incident Trend (24h)</CardTitle>
            <CardDescription>Number of incidents over the last 24 hours</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={incidentTrendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="incidents" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Severity Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Incident Severity Distribution</CardTitle>
            <CardDescription>Breakdown by severity level this week</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={severityDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {severityDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Incidents and Integration Status */}
      <Tabs defaultValue="incidents" className="space-y-4">
        <TabsList>
          <TabsTrigger value="incidents">Recent Incidents</TabsTrigger>
          <TabsTrigger value="integrations">Integration Status</TabsTrigger>
          <TabsTrigger value="activity">AI Activity Log</TabsTrigger>
        </TabsList>

        <TabsContent value="incidents">
          <Card>
            <CardHeader>
              <CardTitle>Recent Incidents</CardTitle>
              <CardDescription>Latest incidents across all services</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {incidents.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-600" />
                    <p>No active incidents. All systems operational!</p>
                  </div>
                )}
                {incidents.map((incident) => (
                  <div
                    key={incident.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <Badge 
                          variant="outline"
                          className={`${
                            incident.severity === 'critical' ? 'bg-red-50 text-red-700 border-red-300' :
                            incident.severity === 'high' ? 'bg-orange-50 text-orange-700 border-orange-300' :
                            incident.severity === 'medium' ? 'bg-yellow-50 text-yellow-700 border-yellow-300' :
                            'bg-blue-50 text-blue-700 border-blue-300'
                          }`}
                        >
                          {incident.severity}
                        </Badge>
                        <p className="font-medium">{incident.title}</p>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <span>Service: {incident.service.name}</span>
                        <span>•</span>
                        <span>{format(new Date(incident.created_at), 'MMM d, HH:mm')}</span>
                        {incident.ai_analysis && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <Shield className="h-3 w-3" />
                              AI Confidence: {Math.round(incident.ai_analysis.confidence_score * 100)}%
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <Badge
                      variant={incident.status === 'active' ? 'destructive' : 
                               incident.status === 'resolved' ? 'default' : 
                               'secondary'}
                    >
                      {incident.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="integrations">
          <Card>
            <CardHeader>
              <CardTitle>Integration Status</CardTitle>
              <CardDescription>Health and status of connected services</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {integrations.map((integration) => (
                  <div
                    key={integration.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${
                        integration.status === 'connected' ? 'bg-green-100' :
                        integration.status === 'error' ? 'bg-red-100' :
                        'bg-gray-100'
                      }`}>
                        <Server className={`h-5 w-5 ${
                          integration.status === 'connected' ? 'text-green-600' :
                          integration.status === 'error' ? 'text-red-600' :
                          'text-gray-600'
                        }`} />
                      </div>
                      <div>
                        <p className="font-medium">{integration.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {integration.last_sync ? `Last sync: ${integration.last_sync}` : 'Never synced'}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={integration.status === 'connected' ? 'default' :
                               integration.status === 'error' ? 'destructive' :
                               'secondary'}
                    >
                      {integration.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardHeader>
              <CardTitle>AI Agent Activity</CardTitle>
              <CardDescription>Recent actions taken by the AI agent</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-start gap-3 text-sm">
                  <Info className="h-4 w-4 text-blue-600 mt-0.5" />
                  <div>
                    <p className="font-medium">Analyzed K8s pod crash</p>
                    <p className="text-muted-foreground">Identified OOM issue, recommended memory limit increase</p>
                    <p className="text-xs text-muted-foreground mt-1">2 minutes ago</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 text-sm">
                  <CheckCircle className="h-4 w-4 text-green-600 mt-0.5" />
                  <div>
                    <p className="font-medium">Auto-resolved API timeout</p>
                    <p className="text-muted-foreground">Scaled service replicas from 3 to 5</p>
                    <p className="text-xs text-muted-foreground mt-1">15 minutes ago</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 text-sm">
                  <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5" />
                  <div>
                    <p className="font-medium">Requested approval for database restart</p>
                    <p className="text-muted-foreground">High-risk action requires manual approval</p>
                    <p className="text-xs text-muted-foreground mt-1">1 hour ago</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </section>
  );
}