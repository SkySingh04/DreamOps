'use client';

import { useAPIKeys } from '@/lib/hooks/use-api-keys';
import { APIKeySetup } from './api-key-setup';
import { KeyStatusToast } from './key-status-toast';
import { useState, useEffect } from 'react';

export function OnboardingWrapper({ children }: { children: React.ReactNode }) {
  const {
    needsOnboarding,
    loading,
    hasWorkingKeys,
    primaryKeyExhausted,
    primaryKey,
    activeKeys,
  } = useAPIKeys();
  
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showCriticalModal, setShowCriticalModal] = useState(false);

  useEffect(() => {
    if (loading) return;

    // First time user - no keys at all
    if (needsOnboarding) {
      setShowOnboarding(true);
      return;
    }

    // Critical: All keys exhausted/invalid - force user to add new key
    if (!hasWorkingKeys) {
      setShowCriticalModal(true);
      return;
    }

    // Non-critical: Primary exhausted but backups available - just show toast
    // This is handled by KeyStatusToast component
  }, [needsOnboarding, loading, hasWorkingKeys]);

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    setShowCriticalModal(false);
    // Reload the page to fetch fresh data
    window.location.reload();
  };

  if (loading) {
    return <>{children}</>;
  }

  return (
    <>
      {children}
      
      {/* Toast notification for non-critical key issues */}
      <KeyStatusToast
        primaryKeyExhausted={primaryKeyExhausted}
        hasWorkingKeys={hasWorkingKeys}
        primaryKey={primaryKey}
        activeKeys={activeKeys}
      />

      {/* Modal for first-time users */}
      {showOnboarding && (
        <APIKeySetup 
          open={showOnboarding} 
          onComplete={handleOnboardingComplete}
          title="Welcome to DreamOps!"
          description="To get started, please add your LLM API key. This allows DreamOps to analyze and respond to incidents using AI."
        />
      )}

      {/* Modal for critical situations (all keys exhausted) */}
      {showCriticalModal && (
        <APIKeySetup 
          open={showCriticalModal} 
          onComplete={handleOnboardingComplete}
          title="API Keys Required"
          description="All your API keys have been exhausted or are invalid. Please add a working API key to continue using DreamOps."
          urgent={true}
        />
      )}
    </>
  );
}