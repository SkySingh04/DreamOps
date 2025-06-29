'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import {
  Cloud,
  ChevronLeft,
  Upload,
  Key,
  FileCode,
  ShieldCheck,
  Globe,
  Loader2,
  CheckCircle,
  Info,
  Lock,
  AlertCircle,
  Server,
  Copy,
  Eye,
  EyeOff,
} from 'lucide-react';
import { toast } from 'sonner';

interface AuthMethodConfig {
  method: 'kubeconfig' | 'service-account' | 'client-cert';
  clusterName: string;
  namespace: string;
  verifySSL: boolean;
  // Kubeconfig
  kubeconfigContent?: string;
  contextName?: string;
  // Service Account
  clusterEndpoint?: string;
  serviceAccountToken?: string;
  caCertificate?: string;
  // Client Certificate
  clientCertificate?: string;
  clientKey?: string;
}

export default function KubernetesSetupPage() {
  const router = useRouter();
  const [authMethod, setAuthMethod] = useState<'kubeconfig' | 'service-account' | 'client-cert'>('kubeconfig');
  const [config, setConfig] = useState<AuthMethodConfig>({
    method: 'kubeconfig',
    clusterName: '',
    namespace: 'default',
    verifySSL: true,
  });
  const [showTokens, setShowTokens] = useState(false);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionTestResult, setConnectionTestResult] = useState<any>(null);

  // Kubeconfig upload mutation
  const uploadKubeconfigMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/integrations/kubernetes/upload-kubeconfig`,
        {
          method: 'POST',
          body: formData,
        }
      );
      if (!response.ok) throw new Error('Failed to upload kubeconfig');
      return response.json();
    },
    onSuccess: (data) => {
      setConnectionTestResult(data);
      toast.success('Kubeconfig uploaded and validated successfully');
      // Store encrypted credentials in localStorage for demo (in production, would be in database)
      localStorage.setItem('k8s_encrypted_creds', data.encrypted_credentials);
    },
    onError: (error) => {
      toast.error('Failed to upload kubeconfig');
      console.error(error);
    },
  });

  // Service account authentication mutation
  const authenticateServiceAccountMutation = useMutation({
    mutationFn: async (config: AuthMethodConfig) => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/integrations/kubernetes/auth/service-account`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cluster_endpoint: config.clusterEndpoint,
            service_account_token: config.serviceAccountToken,
            ca_certificate: config.caCertificate,
            cluster_name: config.clusterName,
            namespace: config.namespace,
            verify_ssl: config.verifySSL,
          }),
        }
      );
      if (!response.ok) throw new Error('Failed to authenticate');
      return response.json();
    },
    onSuccess: (data) => {
      setConnectionTestResult(data);
      toast.success('Service account authenticated successfully');
      localStorage.setItem('k8s_encrypted_creds', data.encrypted_credentials);
    },
    onError: (error) => {
      toast.error('Failed to authenticate with service account');
      console.error(error);
    },
  });

  // Client certificate authentication mutation
  const authenticateClientCertMutation = useMutation({
    mutationFn: async (config: AuthMethodConfig) => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/integrations/kubernetes/auth/client-cert`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cluster_endpoint: config.clusterEndpoint,
            client_certificate: config.clientCertificate,
            client_key: config.clientKey,
            ca_certificate: config.caCertificate,
            cluster_name: config.clusterName,
            namespace: config.namespace,
            verify_ssl: config.verifySSL,
          }),
        }
      );
      if (!response.ok) throw new Error('Failed to authenticate');
      return response.json();
    },
    onSuccess: (data) => {
      setConnectionTestResult(data);
      toast.success('Client certificate authenticated successfully');
      localStorage.setItem('k8s_encrypted_creds', data.encrypted_credentials);
    },
    onError: (error) => {
      toast.error('Failed to authenticate with client certificate');
      console.error(error);
    },
  });

  const handleKubeconfigUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('namespace', config.namespace);
    if (config.contextName) {
      formData.append('context_name', config.contextName);
    }

    uploadKubeconfigMutation.mutate(formData);
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setConnectionTestResult(null);

    try {
      switch (authMethod) {
        case 'kubeconfig':
          if (!config.kubeconfigContent) {
            toast.error('Please upload a kubeconfig file first');
            return;
          }
          // Would call the kubeconfig auth endpoint
          break;
        case 'service-account':
          if (!config.clusterEndpoint || !config.serviceAccountToken) {
            toast.error('Please fill in all required fields');
            return;
          }
          await authenticateServiceAccountMutation.mutateAsync(config);
          break;
        case 'client-cert':
          if (!config.clusterEndpoint || !config.clientCertificate || !config.clientKey) {
            toast.error('Please fill in all required fields');
            return;
          }
          await authenticateClientCertMutation.mutateAsync(config);
          break;
      }
    } finally {
      setIsTestingConnection(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <section className="flex-1 p-4 lg:p-8 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push('/integrations/kubernetes')}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Cloud className="h-6 w-6" />
            Setup Kubernetes Integration
          </h1>
          <p className="text-gray-600 mt-1">
            Connect to any Kubernetes cluster in the world
          </p>
        </div>
      </div>

      {/* Setup Instructions Alert */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Choose your preferred authentication method below. All credentials are encrypted and stored securely.
          Your cluster can be anywhere - on-premises, cloud, or hybrid.
        </AlertDescription>
      </Alert>

      {/* Authentication Methods */}
      <Tabs value={authMethod} onValueChange={(v) => setAuthMethod(v as any)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="kubeconfig" className="flex items-center gap-2">
            <FileCode className="h-4 w-4" />
            Kubeconfig File
          </TabsTrigger>
          <TabsTrigger value="service-account" className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            Service Account
          </TabsTrigger>
          <TabsTrigger value="client-cert" className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" />
            Client Certificate
          </TabsTrigger>
        </TabsList>

        {/* Kubeconfig Method */}
        <TabsContent value="kubeconfig" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Upload Kubeconfig File</CardTitle>
              <CardDescription>
                The easiest way to connect. Upload your kubeconfig file and we'll handle the rest.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <Label htmlFor="kubeconfig-file" className="cursor-pointer">
                  <span className="text-blue-600 hover:text-blue-700">Click to upload</span> or drag and drop
                </Label>
                <Input
                  id="kubeconfig-file"
                  type="file"
                  accept=".yaml,.yml,.conf"
                  className="hidden"
                  onChange={handleKubeconfigUpload}
                />
                <p className="text-sm text-gray-500 mt-2">Supports .yaml, .yml, or .conf files</p>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="context-name">Context Name (optional)</Label>
                <Input
                  id="context-name"
                  placeholder="Leave empty to use current context"
                  value={config.contextName || ''}
                  onChange={(e) => setConfig({ ...config, contextName: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="namespace">Default Namespace</Label>
                <Input
                  id="namespace"
                  placeholder="default"
                  value={config.namespace}
                  onChange={(e) => setConfig({ ...config, namespace: e.target.value })}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Service Account Method */}
        <TabsContent value="service-account" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Service Account Token Authentication</CardTitle>
              <CardDescription>
                Connect using a Kubernetes service account token. Ideal for production environments.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="cluster-endpoint">Cluster API Endpoint *</Label>
                <Input
                  id="cluster-endpoint"
                  placeholder="https://kubernetes.example.com:6443"
                  value={config.clusterEndpoint || ''}
                  onChange={(e) => setConfig({ ...config, clusterEndpoint: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="cluster-name">Cluster Name *</Label>
                <Input
                  id="cluster-name"
                  placeholder="production-cluster"
                  value={config.clusterName}
                  onChange={(e) => setConfig({ ...config, clusterName: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="sa-token">Service Account Token *</Label>
                <div className="relative">
                  <Input
                    id="sa-token"
                    placeholder="Paste your service account token here"
                    className="pr-10 font-mono text-sm"
                    value={config.serviceAccountToken || ''}
                    onChange={(e) => setConfig({ ...config, serviceAccountToken: e.target.value })}
                    type={showTokens ? 'text' : 'password'}
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-2"
                    onClick={() => setShowTokens(!showTokens)}
                  >
                    {showTokens ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="ca-cert">CA Certificate (optional)</Label>
                <Textarea
                  id="ca-cert"
                  placeholder="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
                  className="font-mono text-sm"
                  rows={4}
                  value={config.caCertificate || ''}
                  onChange={(e) => setConfig({ ...config, caCertificate: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="sa-namespace">Default Namespace</Label>
                <Input
                  id="sa-namespace"
                  placeholder="default"
                  value={config.namespace}
                  onChange={(e) => setConfig({ ...config, namespace: e.target.value })}
                />
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-gray-500" />
                  <Label htmlFor="verify-ssl" className="cursor-pointer">
                    Verify SSL Certificate
                  </Label>
                </div>
                <Switch
                  id="verify-ssl"
                  checked={config.verifySSL}
                  onCheckedChange={(checked) => setConfig({ ...config, verifySSL: checked })}
                />
              </div>
            </CardContent>
          </Card>

          {/* Service Account Creation Instructions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">How to Create a Service Account</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <p className="text-sm font-medium">1. Create the service account:</p>
                <div className="bg-gray-100 rounded p-3 font-mono text-sm relative">
                  kubectl create serviceaccount oncall-agent -n default
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-2 h-6 w-6"
                    onClick={() => copyToClipboard('kubectl create serviceaccount oncall-agent -n default')}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">2. Create a cluster role binding:</p>
                <div className="bg-gray-100 rounded p-3 font-mono text-sm relative">
                  kubectl create clusterrolebinding oncall-agent --clusterrole=cluster-admin --serviceaccount=default:oncall-agent
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-2 h-6 w-6"
                    onClick={() => copyToClipboard('kubectl create clusterrolebinding oncall-agent --clusterrole=cluster-admin --serviceaccount=default:oncall-agent')}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">3. Get the service account token:</p>
                <div className="bg-gray-100 rounded p-3 font-mono text-sm relative">
                  kubectl create token oncall-agent -n default --duration=87600h
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-2 h-6 w-6"
                    onClick={() => copyToClipboard('kubectl create token oncall-agent -n default --duration=87600h')}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-sm">
                  For production use, create a more restrictive role with only the necessary permissions.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Client Certificate Method */}
        <TabsContent value="client-cert" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Client Certificate Authentication</CardTitle>
              <CardDescription>
                Connect using X.509 client certificates. Common in enterprise environments.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="cert-endpoint">Cluster API Endpoint *</Label>
                <Input
                  id="cert-endpoint"
                  placeholder="https://kubernetes.example.com:6443"
                  value={config.clusterEndpoint || ''}
                  onChange={(e) => setConfig({ ...config, clusterEndpoint: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="cert-cluster-name">Cluster Name *</Label>
                <Input
                  id="cert-cluster-name"
                  placeholder="production-cluster"
                  value={config.clusterName}
                  onChange={(e) => setConfig({ ...config, clusterName: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="client-cert">Client Certificate *</Label>
                <Textarea
                  id="client-cert"
                  placeholder="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
                  className="font-mono text-sm"
                  rows={4}
                  value={config.clientCertificate || ''}
                  onChange={(e) => setConfig({ ...config, clientCertificate: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="client-key">Client Private Key *</Label>
                <Textarea
                  id="client-key"
                  placeholder="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
                  className="font-mono text-sm"
                  rows={4}
                  value={config.clientKey || ''}
                  onChange={(e) => setConfig({ ...config, clientKey: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="cert-ca">CA Certificate (optional)</Label>
                <Textarea
                  id="cert-ca"
                  placeholder="-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----"
                  className="font-mono text-sm"
                  rows={4}
                  value={config.caCertificate || ''}
                  onChange={(e) => setConfig({ ...config, caCertificate: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="cert-namespace">Default Namespace</Label>
                <Input
                  id="cert-namespace"
                  placeholder="default"
                  value={config.namespace}
                  onChange={(e) => setConfig({ ...config, namespace: e.target.value })}
                />
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-gray-500" />
                  <Label htmlFor="cert-verify-ssl" className="cursor-pointer">
                    Verify SSL Certificate
                  </Label>
                </div>
                <Switch
                  id="cert-verify-ssl"
                  checked={config.verifySSL}
                  onCheckedChange={(checked) => setConfig({ ...config, verifySSL: checked })}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Connection Test Results */}
      {connectionTestResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {connectionTestResult.success ? (
                <>
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  Connection Successful
                </>
              ) : (
                <>
                  <AlertCircle className="h-5 w-5 text-red-600" />
                  Connection Failed
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {connectionTestResult.success ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">Cluster</p>
                    <p className="font-medium">{connectionTestResult.cluster}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Version</p>
                    <p className="font-medium">{connectionTestResult.cluster_version}</p>
                  </div>
                </div>
                
                {connectionTestResult.permissions && (
                  <div className="pt-3 border-t">
                    <p className="text-sm font-medium mb-2">Permissions Verified:</p>
                    <div className="space-y-1">
                      {connectionTestResult.permissions.permissions?.map((perm: any) => (
                        <div key={perm.permission} className="flex items-center justify-between text-sm">
                          <span>{perm.permission}</span>
                          {perm.allowed ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-red-600" />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-2 pt-4">
                  <Button onClick={() => router.push('/integrations/kubernetes')}>
                    <Server className="h-4 w-4 mr-2" />
                    View Cluster Details
                  </Button>
                  <Button variant="outline" onClick={() => setConnectionTestResult(null)}>
                    Test Another Connection
                  </Button>
                </div>
              </div>
            ) : (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {connectionTestResult.error || 'Unable to connect to the cluster'}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Action Buttons */}
      {!connectionTestResult && (
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => router.push('/integrations/kubernetes')}
          >
            Cancel
          </Button>
          <Button
            onClick={handleTestConnection}
            disabled={isTestingConnection}
          >
            {isTestingConnection ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing Connection...
              </>
            ) : (
              <>
                <Globe className="h-4 w-4 mr-2" />
                Test Connection
              </>
            )}
          </Button>
        </div>
      )}
    </section>
  );
}