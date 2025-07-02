'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Circle, AlertCircle, ArrowRight, Settings, Key, Plug } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';

interface SetupStep {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  status: 'pending' | 'completed' | 'current';
  route: string;
}

export default function CompleteSetupPage() {
  const router = useRouter();
  const [setupSteps, setSetupSteps] = useState<SetupStep[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);
  const [setupStatus, setSetupStatus] = useState<any>(null);

  useEffect(() => {
    fetchSetupStatus();
  }, []);

  const fetchSetupStatus = async () => {
    setIsLoading(true);
    try {
      // Use apiClient which automatically handles Firebase authentication
      const response = await apiClient.get('/api/v1/auth/setup-status');
      
      if (response.status !== 'success') {
        throw new Error(response.error?.message || 'Failed to fetch setup status');
      }
      
      const status = response.data;
      setSetupStatus(status);

      // Build setup steps based on status
      const steps: SetupStep[] = [
        {
          id: 'llm_config',
          name: 'AI Configuration',
          description: 'Configure your LLM provider and API key',
          icon: <Key className="h-5 w-5" />,
          status: status.llm_configured ? 'completed' : 'pending',
          route: '/auth/signup/llm-setup'
        },
        {
          id: 'integrations',
          name: 'Connect Integrations',
          description: 'Set up PagerDuty, Kubernetes, and other tools',
          icon: <Plug className="h-5 w-5" />,
          status: status.integrations_configured.pagerduty && status.integrations_configured.kubernetes
            ? 'completed' 
            : 'pending',
          route: '/auth/signup/integrations'
        }
      ];

      // Find current step
      const currentIndex = steps.findIndex(step => step.status === 'pending');
      if (currentIndex >= 0) {
        steps[currentIndex].status = 'current';
        setCurrentStep(currentIndex);
      }

      setSetupSteps(steps);

      // If setup is complete, redirect to dashboard
      if (status.is_setup_complete) {
        toast.success('Setup Complete', {
          description: 'Redirecting to dashboard...'
        });
        setTimeout(() => router.push('/dashboard'), 1500);
      }

    } catch (error: any) {
      console.error('Failed to fetch setup status:', error);
      toast.error('Failed to load setup status');
    } finally {
      setIsLoading(false);
    }
  };

  const handleContinueSetup = () => {
    const currentStepData = setupSteps[currentStep];
    if (currentStepData) {
      router.push(currentStepData.route);
    }
  };

  const handleSkipToSettings = () => {
    router.push('/settings');
  };

  const getStepIcon = (step: SetupStep) => {
    if (step.status === 'completed') {
      return <CheckCircle2 className="h-8 w-8 text-green-600" />;
    } else if (step.status === 'current') {
      return (
        <div className="h-8 w-8 rounded-full bg-indigo-600 flex items-center justify-center text-white">
          {step.icon}
        </div>
      );
    } else {
      return (
        <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500">
          {step.icon}
        </div>
      );
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="w-96">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading your setup status...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Complete Your Setup
          </h1>
          <p className="text-lg text-gray-600">
            You're almost there! Complete the remaining steps to start using DreamOps.
          </p>
        </div>

        {/* Progress */}
        <Card className="mb-8">
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="text-lg">Setup Progress</CardTitle>
              <span className="text-sm text-gray-600">
                {setupStatus?.setup_progress_percentage.toFixed(0)}% Complete
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <Progress 
              value={setupStatus?.setup_progress_percentage || 0} 
              className="h-3"
            />
          </CardContent>
        </Card>

        {/* Setup Steps */}
        <div className="space-y-6 mb-8">
          {setupSteps.map((step, index) => (
            <Card 
              key={step.id}
              className={`transition-all ${
                step.status === 'current' 
                  ? 'ring-2 ring-indigo-600 shadow-lg' 
                  : step.status === 'completed'
                  ? 'bg-green-50 border-green-200'
                  : 'opacity-75'
              }`}
            >
              <CardContent className="p-6">
                <div className="flex items-start space-x-4">
                  {getStepIcon(step)}
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      {step.name}
                      {step.status === 'current' && (
                        <span className="text-sm font-normal text-indigo-600">
                          (Current Step)
                        </span>
                      )}
                    </h3>
                    <p className="text-gray-600 mt-1">{step.description}</p>
                    
                    {step.status === 'current' && (
                      <Button
                        onClick={handleContinueSetup}
                        className="mt-4"
                        size="sm"
                      >
                        Continue Setup
                        <ArrowRight className="h-4 w-4 ml-2" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Missing Requirements Alert */}
        {setupStatus?.missing_requirements.length > 0 && (
          <Alert className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Missing Requirements:</strong>
              <ul className="list-disc list-inside mt-2">
                {setupStatus.missing_requirements.map((req: string) => (
                  <li key={req} className="capitalize">
                    {req.replace('_', ' ')}
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Actions */}
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handleSkipToSettings}
          >
            <Settings className="h-4 w-4 mr-2" />
            Configure in Settings
          </Button>
          
          {setupSteps.some(step => step.status === 'current') && (
            <Button
              onClick={handleContinueSetup}
              size="lg"
            >
              Continue Setup
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}