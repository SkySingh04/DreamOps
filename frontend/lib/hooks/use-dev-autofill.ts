import { useEffect, useState } from 'react';

interface DevConfig {
  llm_config: {
    provider: string;
    api_key: string;
    model: string;
    key_name: string;
  };
  integrations: {
    pagerduty: {
      enabled: boolean;
      api_key: string;
      user_email: string;
      webhook_secret: string;
    };
    kubernetes: {
      enabled: boolean;
      config_path: string;
      context: string;
      namespace: string;
      enable_destructive: boolean;
    };
    github: {
      enabled: boolean;
      token: string;
      org: string;
    };
    notion: {
      enabled: boolean;
      token: string;
      database_id: string;
    };
    grafana: {
      enabled: boolean;
      url: string;
      api_key: string;
    };
  };
  is_dev_mode: boolean;
}

// Fallback configurations if backend is not available
const FALLBACK_DEV_CONFIGS = {
  pagerduty: {
    api_key: 'u+wtxR9ysxHtPM9xPL8Q',
    user_email: 'test@dreamops.ai',
    webhook_secret: 'dev-webhook-secret-123456'
  },
  kubernetes: {
    contexts: ['kind-oncall-test'],
    namespaces: {
      'kind-oncall-test': 'oncall-demo'
    },
    enable_destructive_operations: true,
    kubeconfig_path: '~/.kube/config'
  },
  github: {
    token: 'ghp_devTokenForTesting123456789',
    organization: 'dreamops-test',
    repositories: ['backend', 'frontend']
  },
  notion: {
    token: 'secret_devNotionToken123456',
    workspace_id: 'dev-workspace-123'
  },
  grafana: {
    url: 'https://grafana.dev.local',
    api_key: 'dev-grafana-api-key-123'
  },
  llm: {
    provider: 'anthropic',
    api_key: 'sk-ant-api03-devKeyForTesting123456789',
    model: 'claude-3-opus-20240229'
  }
};

export function useDevAutofill(integrationType?: string) {
  const isDevMode = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
  const [devConfig, setDevConfig] = useState<DevConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isDevMode) return;

    const fetchDevConfig = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Try to fetch from backend first
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${backendUrl}/api/v1/dev/config`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'omit', // Don't send cookies for dev endpoint
        });

        if (response.ok) {
          const data = await response.json();
          setDevConfig(data);
        } else if (response.status === 403) {
          // Not in dev mode on backend
          setError('Backend is not in development mode');
        } else {
          throw new Error(`Failed to fetch dev config: ${response.status}`);
        }
      } catch (err) {
        console.warn('Failed to fetch dev config from backend, using fallback:', err);
        setError('Using fallback configuration');
        // Backend not available, we'll use fallback configs
      } finally {
        setIsLoading(false);
      }
    };

    fetchDevConfig();
  }, [isDevMode]);

  const getDevConfig = (type?: string) => {
    if (!isDevMode) return null;
    
    // If we have backend config, use it
    if (devConfig) {
      if (type === 'llm') {
        return devConfig.llm_config;
      }
      if (type && type in devConfig.integrations) {
        return devConfig.integrations[type as keyof typeof devConfig['integrations']];
      }
      return devConfig;
    }
    
    // Otherwise use fallback
    if (type && type in FALLBACK_DEV_CONFIGS) {
      return FALLBACK_DEV_CONFIGS[type as keyof typeof FALLBACK_DEV_CONFIGS];
    }
    
    return FALLBACK_DEV_CONFIGS;
  };

  const autofillForm = (config: any, onChange: (key: string, value: any) => void) => {
    if (!isDevMode || !config) return;
    
    // Add a small delay to ensure form is rendered
    setTimeout(() => {
      Object.entries(config).forEach(([key, value]) => {
        // Skip empty values
        if (value !== '' && value !== null && value !== undefined) {
          onChange(key, value);
        }
      });
    }, 100);
  };

  return {
    isDevMode,
    getDevConfig,
    autofillForm,
    devConfigs: devConfig || FALLBACK_DEV_CONFIGS,
    isLoading,
    error,
    hasBackendConfig: !!devConfig
  };
}