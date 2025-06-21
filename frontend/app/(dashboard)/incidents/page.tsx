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

  // Using mock data for now
  const incidents = [
    {
      id: 'INC-001',
      title: 'API Gateway High Error Rate',
      service: { name: 'api-gateway' },
      severity: 'critical',
      status: 'active',
      created_at: '2024-06-21T10:30:00Z',
      assignee: 'John Doe',
      ai_analysis: {
        summary: 'Claude identified potential database connection issues',
        confidence_score: 0.92,
        recommendations: [
          'Check database connection pool',
          'Review recent deployments',
          'Monitor API response times'
        ]
      }
    },
    {
      id: 'INC-002',
      title: 'Database Connection Pool Exhausted',
      service: { name: 'user-service' },
      severity: 'high',
      status: 'resolved',
      created_at: '2024-06-21T08:15:00Z',
      resolved_at: '2024-06-21T09:45:00Z',
      assignee: 'Jane Smith',
      ai_analysis: {
        summary: 'Claude recommended connection pool size increase',
        confidence_score: 0.88,
        recommendations: [
          'Increase connection pool size',
          'Add connection pooling metrics',
          'Set up alerting for pool exhaustion'
        ]
      }
    }
  ];

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

  const filteredIncidents = incidents.filter((incident: any) => {
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

  const isLoading = false; // Mock data, no loading needed

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Incident Management</h1>
          <p className="text-gray-600 mt-1">Monitor and resolve incidents with AI assistance</p>
        </div>
        <Button onClick={() => setShowMockDialog(true)}>
          <Zap className="h-4 w-4 mr-2" />
          Trigger Test Incident
        </Button>
      </div>

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
          filteredIncidents.map((incident) => (
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
                  <span>Service: {incident.service.name}</span>
                  <span>•</span>
                  <span>Assignee: {incident.assignee}</span>
                  <span>•</span>
                  <span>{new Date(incident.created_at).toLocaleString()}</span>
                </div>
              </CardHeader>

              {expandedIncident === incident.id && (
                <CardContent className="pt-0">
                  <div className="border-t pt-4">
                    <div className="grid gap-6 md:grid-cols-2">
                      {/* AI Analysis */}
                      <div>
                        <h4 className="font-medium mb-3 flex items-center gap-2">
                          <Bot className="h-4 w-4" />
                          AI Analysis
                        </h4>
                        <div className="space-y-3">
                          <div className="p-3 bg-blue-50 rounded-lg">
                            <p className="text-sm">{incident.ai_analysis?.summary}</p>
                            <div className="flex items-center gap-2 mt-2">
                              <Shield className="h-3 w-3" />
                              <span className="text-xs">
                                Confidence: {Math.round((incident.ai_analysis?.confidence_score || 0) * 100)}%
                              </span>
                            </div>
                          </div>
                          
                          <div>
                            <h5 className="text-sm font-medium mb-2">Recommendations:</h5>
                            <ul className="space-y-1">
                              {incident.ai_analysis?.recommendations?.map((rec, index) => (
                                <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                                  <span className="text-blue-500">•</span>
                                  {rec}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>

                      {/* Actions */}
                      <div>
                        <h4 className="font-medium mb-3 flex items-center gap-2">
                          <Activity className="h-4 w-4" />
                          Quick Actions
                        </h4>
                        <div className="space-y-2">
                          {incident.status === 'active' && (
                            <>
                              <Button variant="outline" size="sm" className="w-full justify-start">
                                <Eye className="h-4 w-4 mr-2" />
                                View Logs
                              </Button>
                              <Button variant="outline" size="sm" className="w-full justify-start">
                                <Terminal className="h-4 w-4 mr-2" />
                                SSH to Instance
                              </Button>
                              <Button variant="outline" size="sm" className="w-full justify-start">
                                <RotateCcw className="h-4 w-4 mr-2" />
                                Restart Service
                              </Button>
                              <Button size="sm" className="w-full">
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

      {/* Mock Incident Dialog */}
      <Dialog open={showMockDialog} onOpenChange={setShowMockDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Trigger Test Incident</DialogTitle>
            <DialogDescription>
              Create a mock incident to test the system response
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-3">
              <Button variant="outline" onClick={() => toast.success('Mock critical incident triggered')}>
                <AlertCircle className="h-4 w-4 mr-2" />
                Critical: Server Down
              </Button>
              <Button variant="outline" onClick={() => toast.success('Mock high incident triggered')}>
                <AlertTriangle className="h-4 w-4 mr-2" />
                High: Database Error
              </Button>
              <Button variant="outline" onClick={() => toast.success('Mock medium incident triggered')}>
                <Info className="h-4 w-4 mr-2" />
                Medium: High Memory Usage
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMockDialog(false)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}