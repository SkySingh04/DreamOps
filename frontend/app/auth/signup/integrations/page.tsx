'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Circle, AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { IntegrationSetupModal } from '@/components/integrations/integration-setup-modal';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@/lib/firebase/auth-context';

interface Integration {
  type: string;
  name: string;
  description: string;
  whyNeeded: string;
  required: boolean;
  setupDifficulty: 'easy' | 'medium' | 'advanced';
  icon: string;
  status: 'pending' | 'configuring' | 'testing' | 'connected' | 'failed' | 'skipped';
  config?: any;
  testResult?: any;
}

const INTEGRATIONS_DATA: Integration[] = [
  {
    type: 'pagerduty',
    name: 'PagerDuty',
    description: 'Receives alerts and triggers AI incident response',
    whyNeeded: 'Core alert ingestion - without this, no incidents reach the AI',
    required: true,
    setupDifficulty: 'easy',
    icon: '🚨',
    status: 'pending'
  },
  {
    type: 'kubernetes',
    name: 'Kubernetes',
    description: 'Monitors pods, deployments, and enables automated fixes',
    whyNeeded: 'Infrastructure remediation - restart pods, scale deployments',
    required: true,
    setupDifficulty: 'medium',
    icon: '☸️',
    status: 'pending'
  },
  {
    type: 'github',
    name: 'GitHub',
    description: 'Provides codebase context for incident analysis',
    whyNeeded: 'Links incidents to recent commits and creates issues',
    required: false,
    setupDifficulty: 'easy',
    icon: '🐙',
    status: 'pending'
  },
  {
    type: 'notion',
    name: 'Notion',
    description: 'Accesses internal runbooks and documentation',
    whyNeeded: 'AI references your team\'s incident procedures',
    required: false,
    setupDifficulty: 'easy',
    icon: '📝',
    status: 'pending'
  },
  {
    type: 'grafana',
    name: 'Grafana',
    description: 'Fetches metrics and dashboard data during incidents',
    whyNeeded: 'Provides performance context for root cause analysis',
    required: false,
    setupDifficulty: 'medium',
    icon: '📊',
    status: 'pending'
  }
];

export default function IntegrationsSetupPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [integrations, setIntegrations] = useState<Integration[]>(INTEGRATIONS_DATA);
  const [selectedIntegration, setSelectedIntegration] = useState<Integration | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTestingAll, setIsTestingAll] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/sign-in?redirect=/auth/signup/integrations');
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    // Get team ID from user context
    if (user) {
      fetchUserTeam();
    }
  }, [user]);

  const fetchUserTeam = async () => {
    try {
    } catch (error) {
      console.error('Failed to fetch user team:', error);
      toast.error('Failed to load user information');
    }
  };

  const getProgress = () => {
    const required = integrations.filter(i => i.required);
    const completed = required.filter(i => i.status === 'connected').length;
    return (completed / required.length) * 100;
  };

  const getSetupDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy':
        return 'text-green-600';
      case 'medium':
        return 'text-yellow-600';
      case 'advanced':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      case 'testing':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-600" />;
      default:
        return <Circle className="h-5 w-5 text-gray-400" />;
    }
  };

  const handleConfigure = (integration: Integration) => {
    setSelectedIntegration(integration);
    setIsModalOpen(true);
  };

  const handleIntegrationSave = async (config: any) => {
    console.log('Signup: handleIntegrationSave called', { selectedIntegration, config });
    if (!selectedIntegration) {
      console.error('Signup: Missing selectedIntegration', { selectedIntegration });
      return;
    }

    try {
      // For PagerDuty, skip testing and save directly
      if (selectedIntegration.type === 'pagerduty') {
        updateIntegrationStatus(selectedIntegration.type, 'connected', config);
        
        // Save the integration
        await apiClient.post('/api/v1/user/integrations', {
          integration_type: selectedIntegration.type,
          config,
          is_required: selectedIntegration.required
        });
        
        toast.success(`${selectedIntegration.name} configured successfully!`);
      } else {
        // Update integration status
        updateIntegrationStatus(selectedIntegration.type, 'testing');

        // Test the integration
        const testResponse = await apiClient.post(
          `/api/v1/integrations/test/${selectedIntegration.type}`,
          { integration_type: selectedIntegration.type, config }
        );
        
        if (testResponse.status !== 'success') {
          throw new Error(testResponse.error?.message || 'Test failed');
        }
        
        const testResult = testResponse.data;

        if (testResult.success) {
          // Save the integration
          await apiClient.post('/api/v1/user/integrations', {
            integration_type: selectedIntegration.type,
            config,
            is_required: selectedIntegration.required
          });

          updateIntegrationStatus(selectedIntegration.type, 'connected', config, testResult);
          
          toast.success(`${selectedIntegration.name} connected successfully!`);
        } else {
          updateIntegrationStatus(selectedIntegration.type, 'failed', config, testResult);
        
          toast.error(testResult.error || 'Failed to connect integration');
        }
      }
    } catch (error: any) {
      updateIntegrationStatus(selectedIntegration.type, 'failed');
      
      toast.error(error.message || 'Failed to save integration');
    }

    setIsModalOpen(false);
  };

  const handleSkip = (integration: Integration) => {
    updateIntegrationStatus(integration.type, 'skipped');
    toast.info(`You can set up ${integration.name} later from settings`);
  };

  const updateIntegrationStatus = (
    type: string, 
    status: Integration['status'], 
    config?: any, 
    testResult?: any
  ) => {
    setIntegrations(prev => 
      prev.map(i => 
        i.type === type 
          ? { ...i, status, config, testResult } 
          : i
      )
    );
  };

  const handleTestAll = async () => {
    setIsTestingAll(true);
    
    try {
      const response = await apiClient.post('/api/v1/integrations/test-all');
      
      if (response.status !== 'success') {
        throw new Error(response.error?.message || 'Failed to test integrations');
      }
      
      const data = response.data;
      
      // Update statuses based on results
      data.results.forEach((result: any) => {
        const integration = integrations.find(i => i.type === result.integration_type);
        if (integration) {
          updateIntegrationStatus(
            result.integration_type, 
            result.success ? 'connected' : 'failed',
            integration.config,
            result
          );
        }
      });

      toast.success(`${data.summary.successful} of ${data.summary.total} integrations connected`);
    } catch (error) {
      toast.error('Failed to test integrations');
    } finally {
      setIsTestingAll(false);
    }
  };

  const canContinue = () => {
    const requiredIntegrations = integrations.filter(i => i.required);
    return requiredIntegrations.every(i => i.status === 'connected');
  };

  const handleContinue = () => {
    router.push('/dashboard');
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render the page if not authenticated
  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Let's connect your tools to get started
          </h1>
          <p className="text-lg text-gray-600">
            DreamOps needs access to your infrastructure to monitor and fix issues automatically
          </p>
        </div>

        {/* Progress */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">Setup Progress</span>
            <span className="text-sm text-gray-600">
              {integrations.filter(i => i.required && i.status === 'connected').length} of {integrations.filter(i => i.required).length} required integrations
            </span>
          </div>
          <Progress value={getProgress()} className="h-2" />
        </div>

        {/* Integration Cards */}
        <div className="space-y-4 mb-8">
          {integrations.map((integration) => (
            <Card 
              key={integration.type} 
              className={`${
                integration.status === 'connected' ? 'border-green-200 bg-green-50/50' : ''
              }`}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4">
                    <span className="text-3xl">{integration.icon}</span>
                    <div>
                      <CardTitle className="text-xl flex items-center gap-2">
                        {integration.name}
                        {integration.required && (
                          <Badge variant="destructive" className="text-xs">REQUIRED</Badge>
                        )}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        {integration.description}
                      </CardDescription>
                    </div>
                  </div>
                  {getStatusIcon(integration.status)}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-start space-x-2">
                    <span className="text-sm font-medium text-gray-700">Why we need it:</span>
                    <span className="text-sm text-gray-600">{integration.whyNeeded}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-700">Setup:</span>
                    <span className={`text-sm capitalize ${getSetupDifficultyColor(integration.setupDifficulty)}`}>
                      {integration.setupDifficulty}
                    </span>
                  </div>
                  <div className="flex gap-2 mt-4">
                    {integration.status === 'pending' && (
                      <>
                        <Button 
                          onClick={() => handleConfigure(integration)}
                          size="sm"
                        >
                          Configure
                        </Button>
                        {!integration.required && (
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleSkip(integration)}
                          >
                            Skip for now
                          </Button>
                        )}
                      </>
                    )}
                    {integration.status === 'connected' && (
                      <div className="flex items-center gap-2 text-sm text-green-600">
                        <CheckCircle2 className="h-4 w-4" />
                        Connected successfully
                      </div>
                    )}
                    {integration.status === 'failed' && (
                      <>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleConfigure(integration)}
                        >
                          Retry
                        </Button>
                        <span className="text-sm text-red-600">
                          Connection failed
                        </span>
                      </>
                    )}
                    {integration.status === 'skipped' && (
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleConfigure(integration)}
                      >
                        Configure now
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Coming Soon Card */}
        <Card className="mb-8 border-dashed">
          <CardHeader>
            <div className="flex items-start space-x-4">
              <span className="text-3xl">🔜</span>
              <div>
                <CardTitle className="text-xl flex items-center gap-2">
                  Datadog
                  <Badge variant="secondary" className="text-xs">COMING SOON</Badge>
                </CardTitle>
                <CardDescription className="mt-1">
                  Alternative monitoring and APM integration
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600">
              Advanced APM and monitoring for complex applications. Available Q3 2025.
            </p>
            <Button variant="outline" size="sm" className="mt-3" disabled>
              Notify Me
            </Button>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex justify-between">
          <Button 
            variant="outline"
            onClick={handleTestAll}
            disabled={isTestingAll || integrations.every(i => i.status === 'pending')}
          >
            {isTestingAll ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing All...
              </>
            ) : (
              'Test All Connections'
            )}
          </Button>
          <Button 
            onClick={handleContinue}
            disabled={!canContinue()}
            className="gap-2"
          >
            Continue to Dashboard
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Integration Setup Modal */}
      {selectedIntegration && (
        <IntegrationSetupModal
          integration={selectedIntegration}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSave={handleIntegrationSave}
        />
      )}
    </div>
  );
}