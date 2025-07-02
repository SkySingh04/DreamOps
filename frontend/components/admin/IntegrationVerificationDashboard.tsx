'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  RefreshCw, 
  Activity,
  Shield,
  Link2,
  Clock,
  Users,
  BarChart3
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface IntegrationStatus {
  type: string;
  validation: {
    success: boolean;
    error_message?: string;
    details?: Record<string, any>;
    timestamp: string;
  };
  connection: {
    connected: boolean;
    latency_ms?: number;
    error_message?: string;
    capabilities?: string[];
    timestamp: string;
  };
  status: 'healthy' | 'unhealthy';
}

interface UserIntegrationHealth {
  user_id: string;
  user_email: string;
  report_timestamp: string;
  overall_health: number;
  integrations: IntegrationStatus[];
}

interface VerificationResult {
  user_id: string;
  timestamp: string;
  encryption_test: boolean;
  validations: Record<string, any>;
  connections: Record<string, any>;
  summary: {
    total_integrations: number;
    successful_validations: number;
    successful_connections: number;
    health_score: number;
  };
}

const integrationIcons: Record<string, React.ReactNode> = {
  pagerduty: '🚨',
  kubernetes: '☸️',
  github: '🐙',
  notion: '📝',
  grafana: '📊'
};

export function IntegrationVerificationDashboard() {
  const [users, setUsers] = useState<UserIntegrationHealth[]>([]);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState<string | null>(null);

  useEffect(() => {
    fetchAllUsers();
  }, []);

  const fetchAllUsers = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/admin/integrations/health-report');
      const data = await response.json();
      setUsers(data.users);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    } finally {
      setLoading(false);
    }
  };

  const testUserIntegrations = async (userId: string) => {
    setRefreshing(userId);
    try {
      const response = await fetch(`/api/v1/admin/integrations/test-user/${userId}`, {
        method: 'POST'
      });
      const data = await response.json();
      setVerificationResult(data);
      
      // Refresh the user list to update health scores
      await fetchAllUsers();
    } catch (error) {
      console.error('Failed to test user integrations:', error);
    } finally {
      setRefreshing(null);
    }
  };

  const getStatusColor = (status: 'healthy' | 'unhealthy') => {
    return status === 'healthy' ? 'text-green-600' : 'text-red-600';
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Integration Verification Dashboard</h2>
          <p className="text-muted-foreground">
            Monitor and verify all user integration configurations and connections
          </p>
        </div>
        <Button onClick={fetchAllUsers} disabled={loading}>
          <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
          Refresh All
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{users.length}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Healthy Integrations</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.reduce((acc, user) => 
                acc + user.integrations.filter(i => i.status === 'healthy').length, 0
              )}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Integrations</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.reduce((acc, user) => 
                acc + user.integrations.filter(i => i.status === 'unhealthy').length, 0
              )}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Health Score</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.length > 0 
                ? Math.round(users.reduce((acc, user) => acc + user.overall_health, 0) / users.length)
                : 0
              }%
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>User Integration Status</CardTitle>
            <CardDescription>
              Click on a user to view detailed integration verification results
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[400px]">
              <div className="space-y-2">
                {users.map((user) => (
                  <div
                    key={user.user_id}
                    className={cn(
                      "flex items-center justify-between p-4 rounded-lg border cursor-pointer hover:bg-accent",
                      selectedUser === user.user_id && "bg-accent"
                    )}
                    onClick={() => setSelectedUser(user.user_id)}
                  >
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{user.user_email}</p>
                      <div className="flex items-center gap-2">
                        <Progress 
                          value={user.overall_health} 
                          className="w-20 h-2"
                        />
                        <span className={cn("text-xs font-medium", getHealthScoreColor(user.overall_health))}>
                          {user.overall_health.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        testUserIntegrations(user.user_id);
                      }}
                      disabled={refreshing === user.user_id}
                    >
                      {refreshing === user.user_id ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <Activity className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Integration Details</CardTitle>
            <CardDescription>
              {selectedUser ? 'Detailed verification results' : 'Select a user to view details'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedUser ? (
              <Tabs defaultValue="overview" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="validation">Validation</TabsTrigger>
                  <TabsTrigger value="connection">Connection</TabsTrigger>
                </TabsList>
                
                <TabsContent value="overview" className="space-y-4">
                  {users
                    .find(u => u.user_id === selectedUser)
                    ?.integrations.map((integration) => (
                      <div key={integration.type} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{integrationIcons[integration.type]}</span>
                          <div>
                            <p className="font-medium capitalize">{integration.type}</p>
                            <p className="text-xs text-muted-foreground">
                              Last checked: {new Date(integration.validation.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <Badge variant={integration.status === 'healthy' ? 'default' : 'destructive'}>
                          {integration.status}
                        </Badge>
                      </div>
                    ))}
                </TabsContent>
                
                <TabsContent value="validation" className="space-y-4">
                  {verificationResult && (
                    <div className="space-y-4">
                      <Alert>
                        <Shield className="h-4 w-4" />
                        <AlertTitle>Encryption Test</AlertTitle>
                        <AlertDescription>
                          {verificationResult.encryption_test ? (
                            <span className="flex items-center gap-2 text-green-600">
                              <CheckCircle2 className="h-4 w-4" />
                              Encryption cycle test passed
                            </span>
                          ) : (
                            <span className="flex items-center gap-2 text-red-600">
                              <XCircle className="h-4 w-4" />
                              Encryption cycle test failed
                            </span>
                          )}
                        </AlertDescription>
                      </Alert>
                      
                      {Object.entries(verificationResult.validations).map(([type, result]: [string, any]) => (
                        <div key={type} className="p-3 border rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium capitalize">{type}</span>
                            {result.success ? (
                              <CheckCircle2 className="h-4 w-4 text-green-600" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-600" />
                            )}
                          </div>
                          {result.details && (
                            <div className="text-xs space-y-1">
                              {Object.entries(result.details).map(([key, value]) => (
                                <div key={key} className="flex justify-between">
                                  <span className="text-muted-foreground">{key}:</span>
                                  <span>{String(value)}</span>
                                </div>
                              ))}
                            </div>
                          )}
                          {result.error_message && (
                            <p className="text-xs text-red-600 mt-2">{result.error_message}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>
                
                <TabsContent value="connection" className="space-y-4">
                  {verificationResult && (
                    <div className="space-y-4">
                      {Object.entries(verificationResult.connections).map(([type, result]: [string, any]) => (
                        <div key={type} className="p-3 border rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium capitalize">{type}</span>
                            <div className="flex items-center gap-2">
                              {result.latency_ms && (
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {result.latency_ms.toFixed(0)}ms
                                </span>
                              )}
                              {result.connected ? (
                                <Link2 className="h-4 w-4 text-green-600" />
                              ) : (
                                <AlertCircle className="h-4 w-4 text-red-600" />
                              )}
                            </div>
                          </div>
                          {result.capabilities && result.capabilities.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {result.capabilities.map((cap: string) => (
                                <Badge key={cap} variant="secondary" className="text-xs">
                                  {cap}
                                </Badge>
                              ))}
                            </div>
                          )}
                          {result.error_message && (
                            <p className="text-xs text-red-600 mt-2">{result.error_message}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                Select a user to view integration details
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}