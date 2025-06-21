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
import { Input } from '@/components/ui/input';
import { Search, Filter, ExternalLink } from 'lucide-react';

export default function IncidentsPage() {
  // Mock incident data
  const incidents = [
    {
      id: 'INC-001',
      title: 'API Gateway High Error Rate',
      service: 'api-gateway',
      severity: 'critical',
      status: 'active',
      createdAt: '2024-06-21T10:30:00Z',
      assignee: 'John Doe',
      aiAnalysis: 'Claude identified potential database connection issues'
    },
    {
      id: 'INC-002',
      title: 'Database Connection Pool Exhausted',
      service: 'user-service',
      severity: 'high',
      status: 'resolved',
      createdAt: '2024-06-21T08:15:00Z',
      resolvedAt: '2024-06-21T09:45:00Z',
      assignee: 'Jane Smith',
      aiAnalysis: 'Claude recommended connection pool size increase'
    },
    {
      id: 'INC-003',
      title: 'High Memory Usage Warning',
      service: 'order-service',
      severity: 'medium',
      status: 'monitoring',
      createdAt: '2024-06-21T07:00:00Z',
      assignee: 'Mike Johnson',
      aiAnalysis: 'Claude detected memory leak pattern in recent deployment'
    }
  ];

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

  return (
    <section className="flex-1 p-4 lg:p-8">
      <div className="mb-6">
        <h1 className="text-lg lg:text-2xl font-medium mb-4">Incident History</h1>
        
        {/* Search and Filter Bar */}
        <div className="flex gap-4 mb-6">
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
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
  Lightbulb,
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
import { Incident, AIAction, TimelineEvent, Severity, IncidentStatus } from '@/lib/types';
import { format, formatDistanceToNow } from 'date-fns';

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
  const [filterStatus, setFilterStatus] = useState<IncidentStatus | 'all'>('all');
  const [filterSeverity, setFilterSeverity] = useState<Severity | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showMockDialog, setShowMockDialog] = useState(false);
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Fetch incidents
  const { data: incidentsData, isLoading } = useQuery({
    queryKey: queryKeys.incidents({ 
      status: filterStatus !== 'all' ? filterStatus : undefined,
      severity: filterSeverity !== 'all' ? filterSeverity : undefined,
    }),
    queryFn: () => apiClient.getIncidents({
      status: filterStatus !== 'all' ? filterStatus : undefined,
      severity: filterSeverity !== 'all' ? filterSeverity : undefined,
    }),
  });

  // WebSocket for real-time updates
  useWebSocket({
    onMessage: (message) => {
      if (message.type === 'incident_update') {
        queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
        toast.info('Incident updated', {
          description: `${message.data.title} status changed to ${message.data.status}`,
        });
      }
      if (message.type === 'ai_action') {
        queryClient.invalidateQueries({ queryKey: queryKeys.incident(message.data.incident_id) });
      }
    },
  });

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

  const triggerMockMutation = useMutation({
    mutationFn: (type: string) => apiClient.triggerMockIncident(type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.incidents() });
      toast.success('Mock incident triggered');
      setShowMockDialog(false);
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

  const incidents = incidentsData?.data?.incidents || [];
  const filteredIncidents = incidents.filter(incident => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        incident.title.toLowerCase().includes(query) ||
        incident.service.name.toLowerCase().includes(query) ||
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

  if (isLoading) {
    return (
      <div className="flex-1 p-4 lg:p-8">
        <div className="space-y-4">
          <Skeleton className="h-12 w-64" />
          <div className="grid gap-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <section className="flex-1 p-4 lg:p-8">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Incident Management</h1>
            <p className="text-muted-foreground mt-1">
              Monitor and manage incidents with AI-powered resolution
            </p>
          </div>
          <Button onClick={() => setShowMockDialog(true)}>
            <Zap className="h-4 w-4 mr-2" />
            Trigger Mock Incident
          </Button>
        </div>

        {/* Filters and Search */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search incidents..."
              className="pl-10"
            />
          </div>
          <Button variant="outline">
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
        </div>

        {/* Incidents Table */}
        <Card>
          <CardHeader>
            <CardTitle>All Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">ID</th>
                    <th className="text-left py-3 px-4">Title</th>
                    <th className="text-left py-3 px-4">Service</th>
                    <th className="text-left py-3 px-4">Severity</th>
                    <th className="text-left py-3 px-4">Status</th>
                    <th className="text-left py-3 px-4">Assignee</th>
                    <th className="text-left py-3 px-4">Created</th>
                    <th className="text-left py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {incidents.map((incident) => (
                    <tr key={incident.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-mono text-sm">{incident.id}</td>
                      <td className="py-3 px-4">
                        <div>
                          <p className="font-medium">{incident.title}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            AI: {incident.aiAnalysis}
                          </p>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="secondary">{incident.service}</Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge className={getSeverityColor(incident.severity)}>
                          {incident.severity}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <Badge className={getStatusColor(incident.status)}>
                          {incident.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{incident.assignee}</td>
                      <td className="py-3 px-4 text-sm">
                        {new Date(incident.createdAt).toLocaleString()}
                      </td>
                      <td className="py-3 px-4">
                        <Button variant="ghost" size="sm">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Select value={filterStatus} onValueChange={(value: any) => setFilterStatus(value)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="acknowledged">Acknowledged</SelectItem>
              <SelectItem value="monitoring">Monitoring</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filterSeverity} onValueChange={(value: any) => setFilterSeverity(value)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Severities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Active Incidents Alert */}
        {filteredIncidents.filter(i => i.status === 'active').length > 0 && (
          <Alert variant="destructive" className="mb-6">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Active Incidents Require Attention</AlertTitle>
            <AlertDescription>
              There are {filteredIncidents.filter(i => i.status === 'active').length} active incidents. 
              The AI agent is analyzing and proposing resolutions.
            </AlertDescription>
          </Alert>
        )}

        {/* Incidents List */}
        <div className="space-y-4">
          {filteredIncidents.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <CheckCircle className="h-12 w-12 text-green-600 mb-4" />
                <h3 className="text-lg font-semibold mb-2">No incidents found</h3>
                <p className="text-muted-foreground">All systems are operational</p>
              </CardContent>
            </Card>
          ) : (
            filteredIncidents.map((incident) => (
              <Card key={incident.id} className="overflow-hidden">
                <CardHeader className="pb-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <div className={`p-1.5 rounded ${
                          incident.severity === 'critical' ? 'bg-red-100' :
                          incident.severity === 'high' ? 'bg-orange-100' :
                          incident.severity === 'medium' ? 'bg-yellow-100' :
                          'bg-blue-100'
                        }`}>
                          {getSeverityIcon(incident.severity)}
                        </div>
                        <Badge 
                          variant="outline"
                          className={`${
                            incident.severity === 'critical' ? 'text-red-700 border-red-300' :
                            incident.severity === 'high' ? 'text-orange-700 border-orange-300' :
                            incident.severity === 'medium' ? 'text-yellow-700 border-yellow-300' :
                            'text-blue-700 border-blue-300'
                          }`}
                        >
                          {incident.severity}
                        </Badge>
                        <Badge
                          variant={incident.status === 'active' ? 'destructive' : 
                                   incident.status === 'resolved' ? 'default' : 
                                   'secondary'}
                        >
                          {incident.status}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          #{incident.incident_number}
                        </span>
                      </div>
                      <h3 className="text-lg font-semibold">{incident.title}</h3>
                      <p className="text-sm text-muted-foreground mt-1">{incident.description}</p>
                      <div className="flex items-center gap-4 mt-3 text-sm">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}
                        </span>
                        <span>Service: {incident.service.name}</span>
                        {incident.ai_analysis && (
                          <span className="flex items-center gap-1">
                            <Shield className="h-3 w-3" />
                            AI Confidence: {Math.round(incident.ai_analysis.confidence_score * 100)}%
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {incident.status === 'active' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => acknowledgeMutation.mutate(incident.id)}
                        >
                          Acknowledge
                        </Button>
                      )}
                      {incident.status !== 'resolved' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => resolveMutation.mutate(incident.id)}
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Resolve
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
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
                </CardHeader>

                {expandedIncident === incident.id && (
                  <CardContent className="border-t">
                    <Tabs defaultValue="analysis" className="mt-4">
                      <TabsList className="grid w-full grid-cols-4">
                        <TabsTrigger value="analysis">AI Analysis</TabsTrigger>
                        <TabsTrigger value="actions">Actions</TabsTrigger>
                        <TabsTrigger value="timeline">Timeline</TabsTrigger>
                        <TabsTrigger value="details">Details</TabsTrigger>
                      </TabsList>

                      <TabsContent value="analysis" className="space-y-4 mt-4">
                        {incident.ai_analysis ? (
                          <>
                            <div className="grid gap-4 md:grid-cols-2">
                              <Card>
                                <CardHeader className="pb-3">
                                  <CardTitle className="text-sm">Root Cause Analysis</CardTitle>
                                </CardHeader>
                                <CardContent>
                                  <p className="font-medium mb-2">
                                    {incident.ai_analysis.root_cause_analysis.likely_cause}
                                  </p>
                                  <div className="space-y-1">
                                    {incident.ai_analysis.root_cause_analysis.evidence.map((evidence, idx) => (
                                      <p key={idx} className="text-sm text-muted-foreground">
                                        • {evidence}
                                      </p>
                                    ))}
                                  </div>
                                  <Progress 
                                    value={incident.ai_analysis.root_cause_analysis.confidence * 100} 
                                    className="mt-3"
                                  />
                                </CardContent>
                              </Card>

                              <Card>
                                <CardHeader className="pb-3">
                                  <CardTitle className="text-sm">Impact Assessment</CardTitle>
                                </CardHeader>
                                <CardContent>
                                  <div className="space-y-2">
                                    <div>
                                      <span className="text-sm font-medium">Scope:</span>
                                      <p className="text-sm text-muted-foreground">
                                        {incident.ai_analysis.impact_assessment.scope}
                                      </p>
                                    </div>
                                    <div>
                                      <span className="text-sm font-medium">Business Impact:</span>
                                      <p className="text-sm text-muted-foreground">
                                        {incident.ai_analysis.impact_assessment.business_impact}
                                      </p>
                                    </div>
                                    <div>
                                      <span className="text-sm font-medium">Affected Components:</span>
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {incident.ai_analysis.impact_assessment.affected_components.map((comp) => (
                                          <Badge key={comp} variant="secondary" className="text-xs">
                                            {comp}
                                          </Badge>
                                        ))}
                                      </div>
                                    </div>
                                  </div>
                                </CardContent>
                              </Card>
                            </div>

                            <Card>
                              <CardHeader className="pb-3">
                                <CardTitle className="text-sm">Recommended Actions</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="grid gap-4 md:grid-cols-2">
                                  <div>
                                    <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                                      <Zap className="h-4 w-4 text-yellow-600" />
                                      Immediate Actions
                                    </h4>
                                    <ul className="space-y-1">
                                      {incident.ai_analysis.recommended_actions.immediate.map((action, idx) => (
                                        <li key={idx} className="text-sm text-muted-foreground">
                                          {idx + 1}. {action}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                  <div>
                                    <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                                      <Clock className="h-4 w-4 text-blue-600" />
                                      Follow-up Actions
                                    </h4>
                                    <ul className="space-y-1">
                                      {incident.ai_analysis.recommended_actions.follow_up.map((action, idx) => (
                                        <li key={idx} className="text-sm text-muted-foreground">
                                          {idx + 1}. {action}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>

                            <Card>
                              <CardHeader className="pb-3">
                                <CardTitle className="text-sm">Monitoring Suggestions</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="grid gap-2">
                                  {incident.ai_analysis.monitoring_suggestions.map((suggestion, idx) => (
                                    <div key={idx} className="flex items-start gap-2">
                                      <Activity className="h-4 w-4 text-green-600 mt-0.5" />
                                      <p className="text-sm">{suggestion}</p>
                                    </div>
                                  ))}
                                </div>
                              </CardContent>
                            </Card>
                          </>
                        ) : (
                          <Card>
                            <CardContent className="flex items-center justify-center py-8">
                              <Bot className="h-8 w-8 text-muted-foreground mr-3" />
                              <p className="text-muted-foreground">AI analysis pending...</p>
                            </CardContent>
                          </Card>
                        )}
                      </TabsContent>

                      <TabsContent value="actions" className="space-y-4 mt-4">
                        {incident.actions && incident.actions.length > 0 ? (
                          incident.actions.map((action) => (
                            <Card key={action.id}>
                              <CardHeader className="pb-3">
                                <div className="flex items-start justify-between">
                                  <div>
                                    <div className="flex items-center gap-2 mb-1">
                                      <Badge className={getRiskLevelColor(action.risk_level)}>
                                        Risk: {action.risk_level}
                                      </Badge>
                                      <Badge variant="outline">
                                        {action.type}
                                      </Badge>
                                      <span className="text-xs text-muted-foreground">
                                        Confidence: {Math.round(action.confidence_score * 100)}%
                                      </span>
                                    </div>
                                    <p className="font-medium">{action.description}</p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                      {format(new Date(action.timestamp), 'MMM d, HH:mm:ss')}
                                    </p>
                                  </div>
                                  {renderActionButton(action, incident)}
                                </div>
                              </CardHeader>
                              {action.result && (
                                <CardContent className="border-t pt-3">
                                  <div className={`text-sm ${
                                    action.result.success ? 'text-green-600' : 'text-red-600'
                                  }`}>
                                    {action.result.success ? (
                                      <CheckCircle className="h-4 w-4 inline mr-1" />
                                    ) : (
                                      <XCircle className="h-4 w-4 inline mr-1" />
                                    )}
                                    {action.result.message}
                                  </div>
                                </CardContent>
                              )}
                            </Card>
                          ))
                        ) : (
                          <Card>
                            <CardContent className="flex items-center justify-center py-8">
                              <p className="text-muted-foreground">No AI actions proposed yet</p>
                            </CardContent>
                          </Card>
                        )}
                      </TabsContent>

                      <TabsContent value="timeline" className="mt-4">
                        <div className="space-y-4">
                          {/* Mock timeline events */}
                          <div className="relative">
                            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200"></div>
                            <div className="space-y-6">
                              <div className="flex gap-4">
                                <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-red-100">
                                  <AlertCircle className="h-4 w-4 text-red-600" />
                                </div>
                                <div className="flex-1">
                                  <p className="font-medium">Incident created</p>
                                  <p className="text-sm text-muted-foreground">
                                    Alert triggered by monitoring system
                                  </p>
                                  <p className="text-xs text-muted-foreground mt-1">
                                    {format(new Date(incident.created_at), 'MMM d, HH:mm:ss')}
                                  </p>
                                </div>
                              </div>
                              <div className="flex gap-4">
                                <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-blue-100">
                                  <Bot className="h-4 w-4 text-blue-600" />
                                </div>
                                <div className="flex-1">
                                  <p className="font-medium">AI Agent assigned</p>
                                  <p className="text-sm text-muted-foreground">
                                    Started analysis and context gathering
                                  </p>
                                  <p className="text-xs text-muted-foreground mt-1">
                                    2 seconds after creation
                                  </p>
                                </div>
                              </div>
                              {incident.acknowledged_at && (
                                <div className="flex gap-4">
                                  <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-yellow-100">
                                    <Eye className="h-4 w-4 text-yellow-600" />
                                  </div>
                                  <div className="flex-1">
                                    <p className="font-medium">Incident acknowledged</p>
                                    <p className="text-sm text-muted-foreground">
                                      Engineer on-call acknowledged the incident
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                      {format(new Date(incident.acknowledged_at), 'MMM d, HH:mm:ss')}
                                    </p>
                                  </div>
                                </div>
                              )}
                              {incident.resolved_at && (
                                <div className="flex gap-4">
                                  <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full bg-green-100">
                                    <CheckCircle className="h-4 w-4 text-green-600" />
                                  </div>
                                  <div className="flex-1">
                                    <p className="font-medium">Incident resolved</p>
                                    <p className="text-sm text-muted-foreground">
                                      Issue has been successfully resolved
                                    </p>
                                    <p className="text-xs text-muted-foreground mt-1">
                                      {format(new Date(incident.resolved_at), 'MMM d, HH:mm:ss')}
                                    </p>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </TabsContent>

                      <TabsContent value="details" className="mt-4">
                        <div className="space-y-4">
                          <Card>
                            <CardHeader className="pb-3">
                              <CardTitle className="text-sm">Incident Details</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <dl className="grid gap-3 text-sm">
                                <div>
                                  <dt className="font-medium">Incident ID</dt>
                                  <dd className="text-muted-foreground font-mono">{incident.id}</dd>
                                </div>
                                <div>
                                  <dt className="font-medium">Service</dt>
                                  <dd className="text-muted-foreground">
                                    {incident.service.name}
                                    {incident.service.summary && (
                                      <span className="block text-xs">{incident.service.summary}</span>
                                    )}
                                  </dd>
                                </div>
                                <div>
                                  <dt className="font-medium">Created</dt>
                                  <dd className="text-muted-foreground">
                                    {format(new Date(incident.created_at), 'PPpp')}
                                  </dd>
                                </div>
                                {incident.assignee && (
                                  <div>
                                    <dt className="font-medium">Assignee</dt>
                                    <dd className="text-muted-foreground">{incident.assignee}</dd>
                                  </div>
                                )}
                              </dl>
                            </CardContent>
                          </Card>

                          {incident.custom_details && Object.keys(incident.custom_details).length > 0 && (
                            <Card>
                              <CardHeader className="pb-3">
                                <CardTitle className="text-sm">Technical Details</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <pre className="text-xs bg-gray-50 p-3 rounded overflow-x-auto">
                                  {JSON.stringify(incident.custom_details, null, 2)}
                                </pre>
                              </CardContent>
                            </Card>
                          )}
                        </div>
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                )}
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Mock Incident Dialog */}
      <Dialog open={showMockDialog} onOpenChange={setShowMockDialog}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Trigger Mock Incident</DialogTitle>
            <DialogDescription>
              Create a simulated incident for testing the AI agent response
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {MOCK_INCIDENT_TYPES.map((type) => (
              <Button
                key={type.value}
                variant="outline"
                className="justify-between"
                onClick={() => triggerMockMutation.mutate(type.value)}
                disabled={triggerMockMutation.isPending}
              >
                <span>{type.label}</span>
                <Badge 
                  variant="outline"
                  className={`${
                    type.severity === 'critical' ? 'text-red-700 border-red-300' :
                    type.severity === 'high' ? 'text-orange-700 border-orange-300' :
                    type.severity === 'medium' ? 'text-yellow-700 border-yellow-300' :
                    'text-blue-700 border-blue-300'
                  }`}
                >
                  {type.severity}
                </Badge>
              </Button>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}