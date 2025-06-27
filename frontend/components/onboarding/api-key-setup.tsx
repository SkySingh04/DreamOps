'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Key, CheckCircle, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface APIKeySetupProps {
  open: boolean;
  onComplete: () => void;
  title?: string;
  description?: string;
  urgent?: boolean;
}

export function APIKeySetup({ 
  open, 
  onComplete, 
  title = "Welcome to DreamOps!",
  description = "To get started, please add your LLM API key. This allows DreamOps to analyze and respond to incidents using AI.",
  urgent = false 
}: APIKeySetupProps) {
  const [provider, setProvider] = useState<'anthropic' | 'openai'>('anthropic');
  const [apiKey, setApiKey] = useState('');
  const [keyName, setKeyName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [validating, setValidating] = useState(false);

  const validateAndSaveKey = async () => {
    if (!apiKey.trim()) {
      setError('Please enter an API key');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // First, create the API key
      const createResponse = await fetch('/api/v1/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          api_key: apiKey,
          name: keyName || `${provider} API Key`,
          is_primary: true,
        }),
      });

      if (!createResponse.ok) {
        const data = await createResponse.json();
        throw new Error(data.detail || 'Failed to save API key');
      }

      const createdKey = await createResponse.json();

      // Then validate it
      setValidating(true);
      const validateResponse = await fetch(`/api/v1/api-keys/${createdKey.id}/validate`, {
        method: 'POST',
      });

      const validationResult = await validateResponse.json();

      if (!validationResult.valid) {
        // Delete the invalid key
        await fetch(`/api/v1/api-keys/${createdKey.id}`, {
          method: 'DELETE',
        });
        throw new Error(validationResult.error || 'Invalid API key');
      }

      setSuccess(true);
      setTimeout(() => {
        onComplete();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
      setValidating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-[500px]" onPointerDownOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className={`flex items-center gap-2 ${urgent ? 'text-red-600' : ''}`}>
            {urgent ? <AlertCircle className="h-5 w-5" /> : <Key className="h-5 w-5" />}
            {title}
          </DialogTitle>
          <DialogDescription className={urgent ? 'text-red-700' : ''}>
            {description}
          </DialogDescription>
        </DialogHeader>

        {!success ? (
          <div className="space-y-4 mt-4">
            <div className="space-y-3">
              <Label>Select your LLM provider</Label>
              <RadioGroup value={provider} onValueChange={(v) => setProvider(v as any)}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="anthropic" id="anthropic" />
                  <Label htmlFor="anthropic">Anthropic (Claude)</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="openai" id="openai" />
                  <Label htmlFor="openai">OpenAI (GPT-4)</Label>
                </div>
              </RadioGroup>
            </div>

            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key</Label>
              <Input
                id="apiKey"
                type="password"
                placeholder={provider === 'anthropic' ? 'sk-ant-...' : 'sk-...'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                disabled={loading}
              />
              <p className="text-sm text-muted-foreground">
                {provider === 'anthropic' ? (
                  <>
                    Get your API key from{' '}
                    <a
                      href="https://console.anthropic.com/settings/keys"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:underline"
                    >
                      Anthropic Console
                    </a>
                  </>
                ) : (
                  <>
                    Get your API key from{' '}
                    <a
                      href="https://platform.openai.com/api-keys"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:underline"
                    >
                      OpenAI Platform
                    </a>
                  </>
                )}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="keyName">Key Name (optional)</Label>
              <Input
                id="keyName"
                placeholder="e.g., Production Key"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                disabled={loading}
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button
              onClick={validateAndSaveKey}
              disabled={loading || !apiKey.trim()}
              className="w-full"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {validating ? 'Validating key...' : 'Saving key...'}
                </>
              ) : (
                'Continue'
              )}
            </Button>

            <p className="text-xs text-center text-muted-foreground">
              Your API key will be encrypted and stored securely. You can add more keys or
              change providers later in Settings.
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <CheckCircle className="h-12 w-12 text-green-500" />
            <p className="text-lg font-medium">API Key validated successfully!</p>
            <p className="text-sm text-muted-foreground">Redirecting to dashboard...</p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}