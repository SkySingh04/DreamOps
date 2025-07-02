'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Cloud,
  CheckCircle,
  XCircle,
  AlertCircle,
  Settings,
  RefreshCw,
  TestTube,
  Plus,
  Trash2,
  Edit,
  Loader2,
  Info,
  Shield,
  Server,
  Layers,
  Activity,
  ChevronLeft,
  Terminal,
  Key,
  FileCode,
  FolderOpen,
  Globe,
  Lock,
  Unlock,
  Database,
  Box,
  Users,
  Cpu,
  HardDrive
} from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { cn } from '@/lib/utils';

interface KubernetesContext {
  name: string;
  cluster: string;
  namespace: string;
  user: string;
  kubeconfig_path: string;
  cluster_info: {
    server: string;
    insecure?: boolean;
  };
  is_current: boolean;
}

interface KubernetesConfig {
  id: string;
  integration_type: string;
  config: {
    name: string;
    context: string;
    namespace: string;
    enable_destructive_operations?: boolean;
    kubeconfig_path?: string;
  };
  is_required: boolean;
  created_at: string;
  updated_at: string;
}

interface TestResult {
  success: boolean;
  error?: string;
  context?: string;
  namespace?: string;
  namespace_exists?: boolean;
  cluster_version?: string;
  node_count?: number;
  connection_time?: string;
  permissions?: {
    can_list_pods: boolean;
    can_list_nodes: boolean;
    can_list_namespaces: boolean;
  };
}

interface ClusterInfo {
  success: boolean;
  cluster_info?: {
    node_count: number;
    namespace_count: number;
    pod_count: number;
    service_count: number;
    deployment_count: number;
    total_cpu_millicores: number;
    total_memory_bytes: number;
    namespaces: string[];
    nodes: Array<{
      name: string;
      status: string;
      version: string;
      os: string;
      container_runtime: string;
    }>;
  };
}

export default function KubernetesIntegrationPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedContext, setSelectedContext] = useState<KubernetesContext | null>(null);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [showTestDialog, setShowTestDialog] = useState(false);
  const [testingContext, setTestingContext] = useState<string | null>(null);
  const [configForm, setConfigForm] = useState({
    name: '',
    context: '',
    namespace: 'default',
    enable_destructive: false,
    kubeconfig_path: '',
  });
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<string | null>(null);

  // Fetch available contexts
  const { data: contextsData, isLoading: contextsLoading, refetch: refetchContexts } = useQuery({
    queryKey: ['kubernetes', 'contexts'],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/integrations/kubernetes/discover`);
      if (!response.ok) throw new Error('Failed to discover contexts');
      return response.json();
    },
  });

  // Fetch saved configurations
  const { data: configsData, isLoading: configsLoading } = useQuery({
    queryKey: ['kubernetes', 'configs'],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/user/integrations`);
      if (!response.ok) throw new Error('Failed to fetch configs');
      const data = await response.json();
      // Filter for kubernetes integrations
      return {
        configs: data.integrations?.filter((i: any) => i.integration_type === 'kubernetes') || []
      };
    },
  });

  // Fetch integration health
  const { data: healthData } = useQuery({
    queryKey: ['kubernetes', 'health'],
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/integrations/kubernetes/health`);
      if (!response.ok) throw new Error('Failed to fetch health');
      return response.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: async ({ context_name, namespace }: { context_name: string; namespace: string }) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/integrations/kubernetes/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_name, namespace }),
      });
      if (!response.ok) throw new Error('Test failed');
      return response.json();
    },
    onSuccess: (data) => {
      setTestResult(data);
      if (data.success) {
        toast.success('Connection test successful');
      } else {
        toast.error(`Connection test failed: ${data.error}`);
      }
    },
    onError: () => {
      toast.error('Connection test failed');
    },
  });

  // Save configuration mutation
  const saveConfigMutation = useMutation({
    mutationFn: async (config: typeof configForm) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/user/integrations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          integration_type: 'kubernetes',
          config: {
            name: config.name,
            context: config.context,
            namespace: config.namespace,
            enable_destructive_operations: config.enable_destructive,
            kubeconfig_path: config.kubeconfig_path,
          },
          is_required: false,
        }),
      });
      if (!response.ok) throw new Error('Failed to save config');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kubernetes', 'configs'] });
      toast.success('Configuration saved successfully');
      setShowConfigDialog(false);
      resetForm();
    },
    onError: () => {
      toast.error('Failed to save configuration');
    },
  });

  // Get cluster info mutation
  const getClusterInfoMutation = useMutation({
    mutationFn: async (context_name: string) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/integrations/kubernetes/cluster-info?context_name=${context_name}`);
      if (!response.ok) throw new Error('Failed to get cluster info');
      return response.json();
    },
  });

  // Verify permissions mutation
  const verifyPermissionsMutation = useMutation({
    mutationFn: async (context_name: string) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/integrations/kubernetes/verify-permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_name }),
      });
      if (!response.ok) throw new Error('Failed to verify permissions');
      return response.json();
    },
  });

  const contexts = contextsData?.contexts || [];
  const configs = configsData?.configs || [];

  const resetForm = () => {
    setConfigForm({
      name: '',
      context: '',
      namespace: 'default',
      enable_destructive: false,
      kubeconfig_path: '',
    });
  };

  const handleContextSelect = (context: KubernetesContext) => {
    setSelectedContext(context);
    setConfigForm(prev => ({
      ...prev,
      name: `${context.cluster} - ${context.name}`,
      context: context.name,
      namespace: context.namespace || 'default',
      kubeconfig_path: context.kubeconfig_path || '',
    }));
  };

  const handleTest = async (contextName: string, namespace: string = 'default') => {
    setTestingContext(contextName);
    setTestResult(null);
    setShowTestDialog(true);
    await testConnectionMutation.mutateAsync({ context_name: contextName, namespace });
    setTestingContext(null);
  };

  const handleSaveConfig = () => {
    if (!configForm.context) {
      toast.error('Please select a context');
      return;
    }
    saveConfigMutation.mutate(configForm);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatCPU = (millicores: number) => {
    if (millicores < 1000) return `${millicores}m`;
    return `${(millicores / 1000).toFixed(2)} cores`;
  };

  if (contextsLoading || configsLoading) {
    return (
      <div className="flex-1 p-4 lg:p-8">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push('/integrations')}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Cloud className="h-6 w-6" />
              Kubernetes Integration
            </h1>
            <p className="text-gray-600 mt-1">
              Connect and manage your Kubernetes clusters
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchContexts()}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push('/integrations/kubernetes/setup')}
          >
            <Globe className="h-4 w-4 mr-2" />
            Connect Any Cluster
          </Button>
          <Button onClick={() => setShowConfigDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Local Cluster
          </Button>
        </div>
      </div>

      {/* Health Status */}
      {healthData && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Integration Status</CardTitle>
              <Badge variant={healthData.status === 'healthy' ? 'default' : 'destructive'}>
                {healthData.status}
              </Badge>
            </div>
          </CardHeader>
          {healthData.connected && healthData.connection_info && (
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Current Context</p>
                  <p className="font-medium">{healthData.connection_info.current_context}</p>
                </div>
                <div>
                  <p className="text-gray-500">Namespace</p>
                  <p className="font-medium">{healthData.connection_info.namespace}</p>
                </div>
                <div>
                  <p className="text-gray-500">Destructive Ops</p>
                  <p className="font-medium flex items-center gap-1">
                    {healthData.connection_info.destructive_operations_enabled ? (
                      <>
                        <Unlock className="h-3 w-3 text-yellow-600" />
                        Enabled
                      </>
                    ) : (
                      <>
                        <Lock className="h-3 w-3 text-green-600" />
                        Disabled
                      </>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Connected Since</p>
                  <p className="font-medium">
                    {healthData.connection_time ? new Date(healthData.connection_time).toLocaleTimeString() : 'N/A'}
                  </p>
                </div>
              </div>
            </CardContent>
          )}
        </Card>
      )}

      <Tabs defaultValue="contexts" className="space-y-4">
        <TabsList>
          <TabsTrigger value="contexts">Available Contexts</TabsTrigger>
          <TabsTrigger value="configs">Saved Configurations</TabsTrigger>
          <TabsTrigger value="details">Cluster Details</TabsTrigger>
        </TabsList>

        <TabsContent value="contexts" className="space-y-4">
          {/* Discovered Contexts */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {contexts.map((context: KubernetesContext) => (
              <Card key={context.name} className={cn(
                "hover:shadow-md transition-shadow cursor-pointer",
                context.is_current && "ring-2 ring-blue-500"
              )}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Server className="h-5 w-5 text-gray-500" />
                      <CardTitle className="text-base">{context.name}</CardTitle>
                    </div>
                    {context.is_current && (
                      <Badge variant="outline" className="text-xs">Current</Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="text-sm space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">Cluster:</span>
                      <span className="font-medium">{context.cluster}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">User:</span>
                      <span className="font-medium">{context.user}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">Namespace:</span>
                      <span className="font-medium">{context.namespace}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">Server:</span>
                      <span className="font-medium text-xs truncate max-w-[150px]" title={context.cluster_info.server}>
                        {context.cluster_info.server}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleTest(context.name, context.namespace)}
                      disabled={testingContext === context.name}
                    >
                      {testingContext === context.name ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : (
                        <TestTube className="h-4 w-4 mr-1" />
                      )}
                      Test
                    </Button>
                    <Button
                      size="sm"
                      className="flex-1"
                      onClick={() => {
                        handleContextSelect(context);
                        setShowConfigDialog(true);
                      }}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Use
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {contexts.length === 0 && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Cloud className="h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-600 text-center">
                  No Kubernetes contexts found.
                </p>
                <p className="text-sm text-gray-500 text-center mt-2">
                  Make sure you have a valid kubeconfig file at ~/.kube/config
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="configs" className="space-y-4">
          {/* Saved Configurations */}
          <div className="grid gap-4">
            {configs.map((config: KubernetesConfig) => (
              <Card key={config.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">{config.config.name}</CardTitle>
                      <CardDescription className="mt-1">
                        Context: {config.config.context} • Namespace: {config.config.namespace}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={config.is_required ? 'default' : 'secondary'}>
                        {config.is_required ? 'Required' : 'Optional'}
                      </Badge>
                      {config.config.enable_destructive_operations && (
                        <Badge variant="destructive" className="gap-1">
                          <Unlock className="h-3 w-3" />
                          Destructive
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-500">
                      Created: {new Date(config.created_at).toLocaleDateString()}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest(config.config.context, config.config.namespace)}
                      >
                        <TestTube className="h-4 w-4 mr-1" />
                        Test
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedCluster(config.config.context);
                          getClusterInfoMutation.mutate(config.config.context);
                        }}
                      >
                        <Info className="h-4 w-4 mr-1" />
                        Details
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {configs.length === 0 && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Database className="h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-600 text-center">
                  No saved configurations yet.
                </p>
                <Button
                  className="mt-4"
                  onClick={() => setShowConfigDialog(true)}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Configuration
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="details" className="space-y-4">
          {/* Cluster Details */}
          {selectedCluster && getClusterInfoMutation.data?.success && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Cluster Overview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <Server className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                      <div className="text-2xl font-bold">
                        {getClusterInfoMutation.data.cluster_info.node_count}
                      </div>
                      <div className="text-sm text-gray-600">Nodes</div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <Box className="h-8 w-8 mx-auto mb-2 text-green-600" />
                      <div className="text-2xl font-bold">
                        {getClusterInfoMutation.data.cluster_info.pod_count}
                      </div>
                      <div className="text-sm text-gray-600">Pods</div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <Layers className="h-8 w-8 mx-auto mb-2 text-purple-600" />
                      <div className="text-2xl font-bold">
                        {getClusterInfoMutation.data.cluster_info.service_count}
                      </div>
                      <div className="text-sm text-gray-600">Services</div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 rounded-lg">
                      <FolderOpen className="h-8 w-8 mx-auto mb-2 text-orange-600" />
                      <div className="text-2xl font-bold">
                        {getClusterInfoMutation.data.cluster_info.namespace_count}
                      </div>
                      <div className="text-sm text-gray-600">Namespaces</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <Cpu className="h-5 w-5 text-blue-600" />
                        <span className="font-medium">Total CPU</span>
                      </div>
                      <div className="text-2xl font-bold text-blue-700">
                        {formatCPU(getClusterInfoMutation.data.cluster_info.total_cpu_millicores)}
                      </div>
                    </div>
                    <div className="p-4 bg-green-50 rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        <HardDrive className="h-5 w-5 text-green-600" />
                        <span className="font-medium">Total Memory</span>
                      </div>
                      <div className="text-2xl font-bold text-green-700">
                        {formatBytes(getClusterInfoMutation.data.cluster_info.total_memory_bytes)}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Nodes</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {getClusterInfoMutation.data.cluster_info.nodes.map((node: any) => (
                      <div key={node.name} className="p-3 border rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium">{node.name}</p>
                            <p className="text-sm text-gray-600">
                              {node.os} • {node.container_runtime}
                            </p>
                          </div>
                          <div className="text-right">
                            <Badge variant={node.status === 'Ready' ? 'default' : 'destructive'}>
                              {node.status}
                            </Badge>
                            <p className="text-sm text-gray-600 mt-1">{node.version}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {!selectedCluster && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Info className="h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-600 text-center">
                  Select a cluster from the Saved Configurations tab to view details.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Configuration Dialog */}
      <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add Kubernetes Cluster</DialogTitle>
            <DialogDescription>
              Configure a new Kubernetes cluster connection
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Configuration Name</Label>
              <Input
                id="name"
                value={configForm.name}
                onChange={(e) => setConfigForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., Production Cluster"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="context">Kubernetes Context</Label>
              {selectedContext ? (
                <div className="flex items-center gap-2 p-2 border rounded-lg bg-gray-50">
                  <Server className="h-4 w-4 text-gray-500" />
                  <span className="font-medium">{selectedContext.name}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-auto"
                    onClick={() => {
                      setSelectedContext(null);
                      setConfigForm(prev => ({ ...prev, context: '' }));
                    }}
                  >
                    Change
                  </Button>
                </div>
              ) : (
                <Select
                  value={configForm.context}
                  onValueChange={(value) => {
                    const ctx = contexts.find((c: KubernetesContext) => c.name === value);
                    if (ctx) handleContextSelect(ctx);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a context" />
                  </SelectTrigger>
                  <SelectContent>
                    {contexts.map((ctx: KubernetesContext) => (
                      <SelectItem key={ctx.name} value={ctx.name}>
                        <div className="flex items-center gap-2">
                          <span>{ctx.name}</span>
                          {ctx.is_current && (
                            <Badge variant="outline" className="text-xs">Current</Badge>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="namespace">Default Namespace</Label>
              <Input
                id="namespace"
                value={configForm.namespace}
                onChange={(e) => setConfigForm(prev => ({ ...prev, namespace: e.target.value }))}
                placeholder="default"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="kubeconfig">Kubeconfig Path (optional)</Label>
              <Input
                id="kubeconfig"
                value={configForm.kubeconfig_path}
                onChange={(e) => setConfigForm(prev => ({ ...prev, kubeconfig_path: e.target.value }))}
                placeholder="~/.kube/config"
              />
              <p className="text-xs text-gray-500">
                Leave empty to use the default kubeconfig location
              </p>
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg bg-yellow-50">
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-yellow-600" />
                <div>
                  <Label htmlFor="destructive" className="text-base cursor-pointer">
                    Enable Destructive Operations
                  </Label>
                  <p className="text-sm text-gray-600">
                    Allow the AI agent to delete pods, scale deployments, etc.
                  </p>
                </div>
              </div>
              <Switch
                id="destructive"
                checked={configForm.enable_destructive}
                onCheckedChange={(checked) => setConfigForm(prev => ({ ...prev, enable_destructive: checked }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setShowConfigDialog(false);
              resetForm();
              setSelectedContext(null);
            }}>
              Cancel
            </Button>
            <Button onClick={handleSaveConfig} disabled={saveConfigMutation.isPending}>
              {saveConfigMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Configuration'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Results Dialog */}
      <Dialog open={showTestDialog} onOpenChange={setShowTestDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connection Test Results</DialogTitle>
          </DialogHeader>
          
          {testResult && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                {testResult.success ? (
                  <>
                    <CheckCircle className="h-5 w-5 text-green-600" />
                    <span className="font-medium text-green-600">Connection Successful</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-5 w-5 text-red-600" />
                    <span className="font-medium text-red-600">Connection Failed</span>
                  </>
                )}
              </div>

              {testResult.success ? (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Context:</span>
                    <span className="font-medium">{testResult.context}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Namespace:</span>
                    <span className="font-medium">{testResult.namespace}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Cluster Version:</span>
                    <span className="font-medium">{testResult.cluster_version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Node Count:</span>
                    <span className="font-medium">{testResult.node_count}</span>
                  </div>
                  
                  {testResult.permissions && (
                    <div className="pt-2 border-t">
                      <p className="font-medium mb-2">Permissions:</p>
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">List Pods:</span>
                          {testResult.permissions.can_list_pods ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-600" />
                          )}
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">List Nodes:</span>
                          {testResult.permissions.can_list_nodes ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-600" />
                          )}
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600">List Namespaces:</span>
                          {testResult.permissions.can_list_namespaces ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-600" />
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>{testResult.error}</AlertDescription>
                </Alert>
              )}
            </div>
          )}

          <DialogFooter>
            <Button onClick={() => {
              setShowTestDialog(false);
              setTestResult(null);
            }}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}