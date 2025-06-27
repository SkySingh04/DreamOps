'use client';

import { useState, useEffect } from 'react';

interface APIKey {
  id: string;
  provider: string;
  api_key_masked: string;
  name: string;
  status: string;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
  error_count: number;
  last_error: string | null;
}

interface APIKeySettings {
  active_key_id: string;
  fallback_key_ids: string[];
  auto_fallback_enabled: boolean;
  max_retries_before_fallback: number;
}

export function useAPIKeys() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [settings, setSettings] = useState<APIKeySettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = async () => {
    try {
      const response = await fetch('/api/v1/api-keys');
      if (!response.ok) {
        throw new Error('Failed to fetch API keys');
      }
      const data = await response.json();
      setKeys(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/v1/api-keys/settings');
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (err) {
      // Settings might not exist yet
    }
  };

  useEffect(() => {
    fetchKeys();
    fetchSettings();
  }, []);

  const refetch = () => {
    setLoading(true);
    fetchKeys();
    fetchSettings();
  };

  const activeKeys = keys.filter(k => k.status === 'active');
  const primaryKey = keys.find(k => k.is_primary);
  const hasWorkingKeys = activeKeys.length > 0;
  const primaryKeyExhausted = primaryKey && primaryKey.status !== 'active';

  return {
    keys,
    settings,
    loading,
    error,
    refetch,
    hasKeys: keys.length > 0,
    needsOnboarding: !loading && keys.length === 0,
    hasWorkingKeys,
    primaryKeyExhausted,
    activeKeys,
    primaryKey,
  };
}