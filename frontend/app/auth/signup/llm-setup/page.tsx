'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Loader2, AlertCircle, Info, ArrowRight, Key, Brain } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@/lib/firebase/auth-context';
import { useDevAutofill } from '@/lib/hooks/use-dev-autofill';

interface LLMProvider {
  id: 'anthropic' | 'openai';
  name: string;
  icon: string;
  models: Array<{
    id: string;
    name: string;
    description: string;
  }>;
  keyPrefix: string;
  keyPlaceholder: string;
  consoleUrl: string;
  description: string;
}

const LLM_PROVIDERS: LLMProvider[] = [
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    icon: '🤖',
    models: [
      { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', description: 'Most capable, best for complex tasks' },
      { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku', description: 'Fast and efficient' },
    ],
    keyPrefix: 'sk-ant-',
    keyPlaceholder: 'sk-ant-api03-...',
    consoleUrl: 'https://console.anthropic.com/account/keys',
    description: 'State-of-the-art AI with excellent reasoning capabilities'
  },
  {
    id: 'openai',
    name: 'OpenAI GPT-4',
    icon: '🧠',
    models: [
      { id: 'gpt-4o', name: 'GPT-4o', description: 'Most capable OpenAI model' },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini', description: 'Faster and more cost-effective' },
    ],
    keyPrefix: 'sk-',
    keyPlaceholder: 'sk-...',
    consoleUrl: 'https://platform.openai.com/api-keys',
    description: 'Industry-leading AI with broad capabilities'
  }
];

type ValidationState = 'idle' | 'validating' | 'valid' | 'invalid';

export default function LLMSetupPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [selectedProvider, setSelectedProvider] = useState<'anthropic' | 'openai'>('anthropic');
  const [apiKey, setApiKey] = useState('');
  const [keyName, setKeyName] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [validationState, setValidationState] = useState<ValidationState>('idle');
  const [validationError, setValidationError] = useState<string>('');
  const [rateLimitInfo, setRateLimitInfo] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const currentProvider = LLM_PROVIDERS.find(p => p.id === selectedProvider)!;
  
  const { isDevMode, getDevConfig } = useDevAutofill('llm');
  
  // Auto-fill in dev mode
  useEffect(() => {
    if (isDevMode) {
      const devConfig = getDevConfig('llm');
      if (devConfig && 'provider' in devConfig && 'api_key' in devConfig && 'model' in devConfig) {
        setSelectedProvider(devConfig.provider);
        setApiKey(devConfig.api_key);
        setKeyName('Development API Key');
        setSelectedModel(devConfig.model);
      }
    }
  }, [isDevMode]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/sign-in?redirect=/auth/signup/llm-setup');
    }
  }, [user, authLoading, router]);

  const handleProviderChange = (value: string) => {
    setSelectedProvider(value as 'anthropic' | 'openai');
    setSelectedModel('');
    setValidationState('idle');
    setValidationError('');
    setRateLimitInfo(null);
  };

  const validateApiKey = async () => {
    if (!apiKey) {
      setValidationError('Please enter an API key');
      return;
    }

    setValidationState('validating');
    setValidationError('');

    try {
      const response = await apiClient.post('/api/v1/auth/test-llm', {
        provider: selectedProvider,
        api_key: apiKey,
        model: selectedModel || undefined
      });

      if (response.status !== 'success') {
        throw new Error(response.error?.message || 'Failed to validate API key');
      }

      const data = response.data;
      
      if (data.valid) {
        setValidationState('valid');
        setRateLimitInfo(data.rate_limit_info);
        
        // Auto-select model if not selected
        if (!selectedModel && data.model_info?.model) {
          setSelectedModel(data.model_info.model);
        }
        
        toast.success('API Key Valid', {
          description: 'Your API key has been verified successfully!'
        });
      } else {
        setValidationState('invalid');
        setValidationError(data.error || 'Invalid API key');
      }
    } catch (error: any) {
      setValidationState('invalid');
      setValidationError('Failed to validate API key');
    }
  };

  const handleSubmit = async () => {
    if (validationState !== 'valid') {
      toast.error('Validation Required', {
        description: 'Please validate your API key before continuing'
      });
      return;
    }

    setIsSubmitting(true);

    try {
      // Save the LLM configuration
      const response = await apiClient.post('/api/v1/auth/llm-config', {
        provider: selectedProvider,
        api_key: apiKey,
        key_name: keyName || `${currentProvider.name} Key`,
        model: selectedModel || undefined
      });
      
      if (response.status !== 'success') {
        throw new Error(response.error?.message || 'Failed to save configuration');
      }

      toast.success('LLM configuration saved successfully!');

      // Navigate to integrations setup
      router.push('/auth/signup/integrations');
    } catch (error: any) {
      toast.error(error.message || 'Failed to save configuration');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getValidationIcon = () => {
    switch (validationState) {
      case 'validating':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-600" />;
      case 'valid':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'invalid':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return null;
    }
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Brain className="h-12 w-12 text-indigo-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Configure Your AI Assistant
            {isDevMode && (
              <span className="ml-2 text-sm font-normal bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                DEV MODE
              </span>
            )}
          </h1>
          <p className="text-lg text-gray-600">
            DreamOps uses advanced AI to analyze and resolve incidents automatically
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-center space-x-2 mb-4">
            <div className="flex items-center">
              <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-white font-semibold">
                1
              </div>
              <span className="ml-2 text-sm font-medium">Account</span>
            </div>
            <div className="w-16 h-1 bg-gray-300"></div>
            <div className="flex items-center">
              <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-white font-semibold">
                2
              </div>
              <span className="ml-2 text-sm font-medium">AI Setup</span>
            </div>
            <div className="w-16 h-1 bg-gray-300"></div>
            <div className="flex items-center">
              <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-gray-600 font-semibold">
                3
              </div>
              <span className="ml-2 text-sm text-gray-500">Integrations</span>
            </div>
          </div>
          <Progress value={33} className="h-2" />
        </div>

        {/* Main Card */}
        <Card className="shadow-xl">
          <CardHeader>
            <CardTitle className="text-2xl">Choose Your LLM Provider</CardTitle>
            <CardDescription>
              Select the AI model that will power your incident response
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Provider Selection */}
            <div className="space-y-4">
              <Label>AI Provider</Label>
              <RadioGroup value={selectedProvider} onValueChange={handleProviderChange}>
                {LLM_PROVIDERS.map((provider) => (
                  <div key={provider.id} className="flex items-start space-x-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer">
                    <RadioGroupItem value={provider.id} id={provider.id} className="mt-1" />
                    <div className="flex-1">
                      <Label htmlFor={provider.id} className="cursor-pointer">
                        <div className="flex items-center gap-2">
                          <span className="text-2xl">{provider.icon}</span>
                          <span className="font-semibold">{provider.name}</span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{provider.description}</p>
                      </Label>
                    </div>
                  </div>
                ))}
              </RadioGroup>
            </div>

            {/* Model Selection */}
            {currentProvider && (
              <div className="space-y-2">
                <Label htmlFor="model">Model (Optional)</Label>
                <select
                  id="model"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                >
                  <option value="">Auto-select best model</option>
                  {currentProvider.models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} - {model.description}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* API Key Input */}
            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key</Label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2">
                  <Key className="h-4 w-4 text-gray-400" />
                </div>
                <Input
                  id="apiKey"
                  type="password"
                  placeholder={currentProvider.keyPlaceholder}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="pl-10 pr-10"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {getValidationIcon()}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <a
                  href={currentProvider.consoleUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-indigo-600 hover:text-indigo-500"
                >
                  Get your API key →
                </a>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={validateApiKey}
                  disabled={!apiKey || validationState === 'validating'}
                >
                  {validationState === 'validating' ? 'Validating...' : 'Validate Key'}
                </Button>
              </div>
            </div>

            {/* Key Name (Optional) */}
            <div className="space-y-2">
              <Label htmlFor="keyName">Key Name (Optional)</Label>
              <Input
                id="keyName"
                placeholder="e.g., Production Key"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
              />
              <p className="text-sm text-gray-500">
                Give your key a friendly name to identify it later
              </p>
            </div>

            {/* Validation Messages */}
            {validationError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{validationError}</AlertDescription>
              </Alert>
            )}

            {validationState === 'valid' && rateLimitInfo && (
              <Alert className="border-green-200 bg-green-50">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  API key validated successfully!
                  {rateLimitInfo.requests_remaining && (
                    <span className="block text-sm mt-1">
                      Rate limit: {rateLimitInfo.requests_remaining} requests remaining
                    </span>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {/* Info Alert */}
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Your API key is encrypted and stored securely. You can add multiple API keys
                or change providers later from your settings.
              </AlertDescription>
            </Alert>

            {/* Submit Button */}
            <div className="pt-4">
              <Button
                onClick={handleSubmit}
                disabled={validationState !== 'valid' || isSubmitting}
                className="w-full"
                size="lg"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving Configuration...
                  </>
                ) : (
                  <>
                    Continue to Integrations
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}