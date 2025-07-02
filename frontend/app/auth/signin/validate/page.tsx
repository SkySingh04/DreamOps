'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Loader2, AlertCircle, RefreshCw, Settings } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface ValidationItem {
  type: string;
  name: string;
  status: 'checking' | 'valid' | 'invalid' | 'warning';
  message?: string;
  canFix?: boolean;
}

export default function SignInValidatePage() {
  const router = useRouter();
  const [validationItems, setValidationItems] = useState<ValidationItem[]>([
    { type: 'llm_config', name: 'AI Configuration', status: 'checking' },
    { type: 'pagerduty', name: 'PagerDuty', status: 'checking' },
    { type: 'kubernetes', name: 'Kubernetes', status: 'checking' },
  ]);
  const [isValidating, setIsValidating] = useState(true);
  const [canProceed, setCanProceed] = useState(false);
  const [setupStatus, setSetupStatus] = useState<any>(null);

  useEffect(() => {
    validateUserSetup();
  }, []);

  const validateUserSetup = async () => {
    setIsValidating(true);
    
    try {
      // First, get setup status
      const statusResponse = await apiClient.get('/api/v1/auth/setup-status');
      setSetupStatus(statusResponse.data);

      // If setup is not complete, redirect to complete it
      if (!statusResponse.data.is_setup_complete) {
        toast.error('Setup Incomplete', {
          description: 'Please complete your setup to continue'
        });
        router.push('/auth/complete-setup');
        return;
      }

      // Then validate all configurations
      const validationResponse = await apiClient.get('/api/v1/auth/validate-setup');
      const results = validationResponse.data.validation_results;

      // Update validation items based on results
      setValidationItems(prev => prev.map(item => {
        const result = results.find((r: any) => 
          r.target === item.type || 
          (r.validation_type === 'llm_key' && item.type === 'llm_config')
        );

        if (result) {
          return {
            ...item,
            status: result.is_successful ? 'valid' : 'invalid',
            message: result.error_message,
            canFix: !result.is_successful
          };
        }

        return { ...item, status: 'warning', message: 'Not configured' };
      }));

      // Check if user can proceed
      const criticalItems = ['llm_config', 'pagerduty', 'kubernetes'];
      const allCriticalValid = results
        .filter((r: any) => criticalItems.includes(r.target) || r.validation_type === 'llm_key')
        .every((r: any) => r.is_successful);

      setCanProceed(allCriticalValid);

      if (allCriticalValid) {
        // Auto-redirect after successful validation
        setTimeout(() => {
          router.push('/dashboard');
        }, 2000);
      }

    } catch (error: any) {
      console.error('Validation error:', error);
      toast.error('Validation Failed', {
        description: error.response?.data?.detail || 'Failed to validate your setup'
      });
      
      // Set all items to invalid
      setValidationItems(prev => prev.map(item => ({
        ...item,
        status: 'invalid',
        message: 'Validation failed',
        canFix: true
      })));
    } finally {
      setIsValidating(false);
    }
  };

  const getStatusIcon = (status: ValidationItem['status']) => {
    switch (status) {
      case 'checking':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-600" />;
      case 'valid':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'invalid':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
    }
  };

  const getProgress = () => {
    const total = validationItems.length;
    const valid = validationItems.filter(item => item.status === 'valid').length;
    return (valid / total) * 100;
  };

  const handleFixItem = (item: ValidationItem) => {
    switch (item.type) {
      case 'llm_config':
        router.push('/settings?tab=api-keys');
        break;
      case 'pagerduty':
      case 'kubernetes':
        router.push('/settings/integrations');
        break;
    }
  };

  const handleRetryValidation = () => {
    setValidationItems(prev => prev.map(item => ({ ...item, status: 'checking' })));
    validateUserSetup();
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-lg w-full">
        <Card className="shadow-lg">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Validating Your Configuration</CardTitle>
            <CardDescription>
              {isValidating 
                ? 'Checking your setup to ensure everything is working...'
                : canProceed
                ? 'All systems operational! Redirecting to dashboard...'
                : 'Some configurations need attention'
              }
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Progress */}
            <div>
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Validation Progress</span>
                <span>{Math.round(getProgress())}%</span>
              </div>
              <Progress value={getProgress()} className="h-2" />
            </div>

            {/* Validation Items */}
            <div className="space-y-3">
              {validationItems.map((item) => (
                <div
                  key={item.type}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    item.status === 'valid' 
                      ? 'bg-green-50 border-green-200' 
                      : item.status === 'invalid'
                      ? 'bg-red-50 border-red-200'
                      : item.status === 'warning'
                      ? 'bg-yellow-50 border-yellow-200'
                      : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(item.status)}
                    <div>
                      <p className="font-medium">{item.name}</p>
                      {item.message && (
                        <p className="text-sm text-gray-600">{item.message}</p>
                      )}
                    </div>
                  </div>
                  {item.canFix && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleFixItem(item)}
                    >
                      Fix
                    </Button>
                  )}
                </div>
              ))}
            </div>

            {/* Status Alert */}
            {!isValidating && (
              <>
                {canProceed ? (
                  <Alert className="border-green-200 bg-green-50">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <AlertDescription className="text-green-800">
                      All configurations validated successfully! You'll be redirected to the dashboard shortly.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Some configurations failed validation. Please fix them to continue.
                    </AlertDescription>
                  </Alert>
                )}
              </>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              {!isValidating && !canProceed && (
                <>
                  <Button
                    variant="outline"
                    onClick={handleRetryValidation}
                    className="flex-1"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry Validation
                  </Button>
                  <Button
                    onClick={() => router.push('/settings')}
                    className="flex-1"
                  >
                    <Settings className="h-4 w-4 mr-2" />
                    Go to Settings
                  </Button>
                </>
              )}
              {canProceed && (
                <Button
                  onClick={() => router.push('/dashboard')}
                  className="w-full"
                >
                  Continue to Dashboard
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Setup Summary */}
        {setupStatus && !isValidating && (
          <Card className="mt-4 shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg">Setup Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">LLM Provider:</span>
                  <span className="font-medium">
                    {setupStatus.llm_provider || 'Not configured'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Setup Progress:</span>
                  <span className="font-medium">
                    {Math.round(setupStatus.setup_progress_percentage)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Missing Items:</span>
                  <span className="font-medium">
                    {setupStatus.missing_requirements.length || 'None'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}