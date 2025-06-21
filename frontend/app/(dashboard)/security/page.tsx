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
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { 
  Shield, 
  Activity,
  RotateCcw,
  Eye,
  Download,
  Filter,
  Calendar,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  User,
  Clock,
  Code,
  FileText,
  Lock,
  Unlock,
  Terminal,
  GitBranch,
  Database,
  Server,
  Key,
  RefreshCw,
  Settings
} from 'lucide-react';
import { format, formatDistanceToNow, subDays } from 'date-fns';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { AIAction, RiskLevel } from '@/lib/types';

interface AuditEntry {
  id: string;
  timestamp: string;
  action_type: 'ai_action' | 'config_change' | 'user_action' | 'system_event';
  user?: string;
  description: string;
  risk_level: RiskLevel;
  status: 'success' | 'failed' | 'rolled_back';
  metadata?: {
    incident_id?: string;
    integration?: string;
    before?: any;
    after?: any;
    error?: string;
  };
  can_rollback?: boolean;
}

interface SecurityConfig {
  api_keys: Array<{
    id: string;
    name: string;
    service: string;
    last_used?: string;
    created_at: string;
    expires_at?: string;
  }>;
  permissions: Array<{
    role: string;
    permissions: string[];
  }>;
  security_settings: {
    two_factor_required: boolean;
    session_timeout: number;
    ip_whitelist_enabled: boolean;
    audit_retention_days: number;
  };
}

const MOCK_AUDIT_ENTRIES: AuditEntry[] = [
  {
    id: '1',
    timestamp: new Date().toISOString(),
    action_type: 'ai_action',
    description: 'Scaled kubernetes deployment from 3 to 5 replicas',
    risk_level: 'medium',
    status: 'success',
    metadata: {
      incident_id: 'INC-1234',
      integration: 'kubernetes',
    },
    can_rollback: true,
  },
  {
    id: '2',
    timestamp: subDays(new Date(), 1).toISOString(),
    action_type: 'config_change',
    user: 'admin@example.com',
    description: 'Changed AI mode from approval to plan',
    risk_level: 'high',
    status: 'success',
    metadata: {
      before: { mode: 'approval' },
      after: { mode: 'plan' },
    },
  },
  {
    id: '3',
    timestamp: subDays(new Date(), 2).toISOString(),
    action_type: 'ai_action',
    description: 'Attempted to restart database service',
    risk_level: 'high',
    status: 'failed',
    metadata: {
      incident_id: 'INC-1233',
      integration: 'kubernetes',
      error: 'Permission denied: high-risk action requires approval',
    },
  },
];

const MOCK_SECURITY_CONFIG: SecurityConfig = {
  api_keys: [
    {
      id: '1',
      name: 'PagerDuty Integration',
      service: 'pagerduty',
      last_used: new Date().toISOString(),
      created_at: subDays(new Date(), 30).toISOString(),
    },
    {
      id: '2',
      name: 'GitHub MCP Server',
      service: 'github',
      last_used: subDays(new Date(), 1).toISOString(),
      created_at: subDays(new Date(), 60).toISOString(),
    },
    {
      id: '3',
      name: 'Kubernetes API',
      service: 'kubernetes',
      last_used: new Date().toISOString(),
      created_at: subDays(new Date(), 90).toISOString(),
    },
  ],
  permissions: [
    {
      role: 'admin',
      permissions: ['all'],
    },
    {
      role: 'operator',
      permissions: ['view_incidents', 'acknowledge_incidents', 'execute_low_risk_actions'],
    },
    {
      role: 'viewer',
      permissions: ['view_incidents', 'view_analytics'],
    },
  ],
  security_settings: {
    two_factor_required: true,
    session_timeout: 3600,
    ip_whitelist_enabled: false,
    audit_retention_days: 90,
  },
};

export default function SecurityPage() {
  const [filterDateRange, setFilterDateRange] = useState('7d');
  const [filterRiskLevel, setFilterRiskLevel] = useState<RiskLevel | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showDiffDialog, setShowDiffDialog] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  const [showRevokeDialog, setShowRevokeDialog] = useState(false);
  const [selectedApiKey, setSelectedApiKey] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // In a real app, these would fetch from the API
  const auditEntries = MOCK_AUDIT_ENTRIES;
  const securityConfig = MOCK_SECURITY_CONFIG;

  const filteredEntries = auditEntries.filter(entry => {
    if (filterRiskLevel !== 'all' && entry.risk_level !== filterRiskLevel) return false;
    if (filterStatus !== 'all' && entry.status !== filterStatus) return false;
    if (searchQuery && !entry.description.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const getRiskLevelColor = (level: RiskLevel) => {
    switch (level) {
      case 'high':
        return 'text-red-600 bg-red-50 border-red-300';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-300';
      case 'low':
        return 'text-green-600 bg-green-50 border-green-300';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'rolled_back':
        return <RotateCcw className="h-4 w-4 text-yellow-600" />;
      default:
        return <Info className="h-4 w-4 text-gray-600" />;
    }
  };

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'ai_action':
        return <Activity className="h-4 w-4" />;
      case 'config_change':
        return <Settings className="h-4 w-4" />;
      case 'user_action':
        return <User className="h-4 w-4" />;
      case 'system_event':
        return <Server className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const handleRollback = async (entryId: string) => {
    // In production, this would call the API
    toast.success('Action rolled back successfully');
  };

  const handleExportAudit = () => {
    const csv = [
      ['Timestamp', 'Type', 'Description', 'Risk Level', 'Status', 'User'],
      ...filteredEntries.map(entry => [
        entry.timestamp,
        entry.action_type,
        entry.description,
        entry.risk_level,
        entry.status,
        entry.user || 'System',
      ]),
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('Audit log exported');
  };

  const handleRevokeApiKey = (keyId: string) => {
    // In production, this would call the API
    toast.success('API key revoked');
    setShowRevokeDialog(false);
  };

  const handleRotateApiKey = (keyId: string) => {
    // In production, this would call the API
    toast.success('API key rotated. New key has been generated.');
  };

  return (
    <div className="flex-1 p-4 lg:p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Security & Audit Trail</h1>
          <p className="text-muted-foreground mt-1">
            Monitor all actions, manage access controls, and review security settings
          </p>
        </div>
        <Button onClick={handleExportAudit}>
          <Download className="h-4 w-4 mr-2" />
          Export Audit Log
        </Button>
      </div>

      <Tabs defaultValue="audit" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="audit">Audit Trail</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="permissions">Permissions</TabsTrigger>
          <TabsTrigger value="settings">Security Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="audit" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardHeader>
              <CardTitle>Filters</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <Input
                    placeholder="Search actions..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full"
                  />
                </div>
                <Select value={filterDateRange} onValueChange={setFilterDateRange}>
                  <SelectTrigger className="w-[180px]">
                    <Calendar className="h-4 w-4 mr-2" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="24h">Last 24 hours</SelectItem>
                    <SelectItem value="7d">Last 7 days</SelectItem>
                    <SelectItem value="30d">Last 30 days</SelectItem>
                    <SelectItem value="90d">Last 90 days</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={filterRiskLevel} onValueChange={(value: any) => setFilterRiskLevel(value)}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="All Risk Levels" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Risk Levels</SelectItem>
                    <SelectItem value="low">Low Risk</SelectItem>
                    <SelectItem value="medium">Medium Risk</SelectItem>
                    <SelectItem value="high">High Risk</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="All Statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="rolled_back">Rolled Back</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Audit Entries */}
          <Card>
            <CardHeader>
              <CardTitle>Action History</CardTitle>
              <CardDescription>
                Comprehensive log of all AI agent actions and system changes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {filteredEntries.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Shield className="h-12 w-12 mx-auto mb-4" />
                    <p>No audit entries found</p>
                  </div>
                ) : (
                  filteredEntries.map((entry) => (
                    <div
                      key={entry.id}
                      className="flex items-start gap-4 p-4 border rounded-lg hover:bg-gray-50"
                    >
                      <div className="flex items-center gap-2">
                        {getStatusIcon(entry.status)}
                        <div className="p-2 bg-gray-100 rounded">
                          {getActionIcon(entry.action_type)}
                        </div>
                      </div>
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <p className="font-medium">{entry.description}</p>
                          <Badge 
                            variant="outline" 
                            className={getRiskLevelColor(entry.risk_level)}
                          >
                            {entry.risk_level} risk
                          </Badge>
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                          </span>
                          {entry.user && (
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {entry.user}
                            </span>
                          )}
                          {entry.metadata?.integration && (
                            <span className="flex items-center gap-1">
                              <Server className="h-3 w-3" />
                              {entry.metadata.integration}
                            </span>
                          )}
                          {entry.metadata?.incident_id && (
                            <span className="flex items-center gap-1">
                              <AlertTriangle className="h-3 w-3" />
                              {entry.metadata.incident_id}
                            </span>
                          )}
                        </div>
                        
                        {entry.metadata?.error && (
                          <Alert variant="destructive" className="mt-2">
                            <AlertDescription className="text-xs">
                              {entry.metadata.error}
                            </AlertDescription>
                          </Alert>
                        )}
                      </div>
                      
                      <div className="flex gap-2">
                        {entry.metadata?.before && entry.metadata?.after && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedEntry(entry);
                              setShowDiffDialog(true);
                            }}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            View Changes
                          </Button>
                        )}
                        {entry.can_rollback && entry.status === 'success' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRollback(entry.id)}
                          >
                            <RotateCcw className="h-4 w-4 mr-1" />
                            Rollback
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="api-keys" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API Key Management</CardTitle>
              <CardDescription>
                Manage API keys for integrations and services
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {securityConfig.api_keys.map((key) => (
                  <div
                    key={key.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-gray-100 rounded">
                        <Key className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="font-medium">{key.name}</p>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>Service: {key.service}</span>
                          <span>Created: {format(new Date(key.created_at), 'MMM d, yyyy')}</span>
                          {key.last_used && (
                            <span>Last used: {formatDistanceToNow(new Date(key.last_used), { addSuffix: true })}</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRotateApiKey(key.id)}
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Rotate
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedApiKey(key.id);
                          setShowRevokeDialog(true);
                        }}
                      >
                        <XCircle className="h-4 w-4 mr-1" />
                        Revoke
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6">
                <Button>
                  <Key className="h-4 w-4 mr-2" />
                  Generate New API Key
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="permissions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Role-Based Access Control</CardTitle>
              <CardDescription>
                Define permissions for different user roles
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {securityConfig.permissions.map((role) => (
                  <div key={role.role} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium capitalize">{role.role}</h4>
                      <Button variant="outline" size="sm">
                        Edit Permissions
                      </Button>
                    </div>
                    <div className="grid gap-2">
                      {role.permissions.map((permission) => (
                        <div key={permission} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <span className="text-muted-foreground">{permission.replace(/_/g, ' ')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6">
                <Button>
                  <User className="h-4 w-4 mr-2" />
                  Create New Role
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>
                Configure security policies and requirements
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="2fa" className="text-base">
                      Two-Factor Authentication
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Require 2FA for all users
                    </p>
                  </div>
                  <Switch
                    id="2fa"
                    checked={securityConfig.security_settings.two_factor_required}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="session-timeout">
                    Session Timeout
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="session-timeout"
                      type="number"
                      value={securityConfig.security_settings.session_timeout / 60}
                      className="w-32"
                    />
                    <span className="text-sm text-muted-foreground">minutes</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="ip-whitelist" className="text-base">
                      IP Whitelist
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Only allow access from whitelisted IP addresses
                    </p>
                  </div>
                  <Switch
                    id="ip-whitelist"
                    checked={securityConfig.security_settings.ip_whitelist_enabled}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="audit-retention">
                    Audit Log Retention
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="audit-retention"
                      type="number"
                      value={securityConfig.security_settings.audit_retention_days}
                      className="w-32"
                    />
                    <span className="text-sm text-muted-foreground">days</span>
                  </div>
                </div>
                
                <div className="pt-4">
                  <Button>
                    Save Security Settings
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Diff Dialog */}
      <Dialog open={showDiffDialog} onOpenChange={setShowDiffDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Configuration Changes</DialogTitle>
            <DialogDescription>
              Review what changed in this configuration update
            </DialogDescription>
          </DialogHeader>
          {selectedEntry && (
            <div className="grid gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">Before</h4>
                  <pre className="text-xs bg-red-50 p-3 rounded overflow-x-auto">
                    {JSON.stringify(selectedEntry.metadata?.before, null, 2)}
                  </pre>
                </div>
                <div>
                  <h4 className="font-medium mb-2">After</h4>
                  <pre className="text-xs bg-green-50 p-3 rounded overflow-x-auto">
                    {JSON.stringify(selectedEntry.metadata?.after, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Revoke API Key Dialog */}
      <Dialog open={showRevokeDialog} onOpenChange={setShowRevokeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API Key</DialogTitle>
            <DialogDescription>
              This action cannot be undone. The API key will be permanently revoked.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRevokeDialog(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={() => selectedApiKey && handleRevokeApiKey(selectedApiKey)}
            >
              Revoke Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}