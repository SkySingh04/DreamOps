'use client';

import { useState } from 'react';
import { useDevAutofill } from '@/lib/hooks/use-dev-autofill';

export function DevModeIndicator() {
  const [showDetails, setShowDetails] = useState(false);
  const { isDevMode, hasBackendConfig, isLoading, error } = useDevAutofill();
  
  if (!isDevMode) return null;
  
  return (
    <>
      <div 
        className="fixed bottom-4 left-4 bg-yellow-500 text-black px-3 py-1 rounded-md text-sm font-medium z-50 flex items-center gap-2 cursor-pointer hover:bg-yellow-400 transition-colors"
        onClick={() => setShowDetails(!showDetails)}
      >
        <span className="font-bold">DEV MODE</span>
        <span className="text-xs opacity-80">
          {isLoading ? 'Loading...' : hasBackendConfig ? 'Backend config' : 'Fallback config'}
        </span>
      </div>
      
      {showDetails && (
        <div className="fixed bottom-16 left-4 bg-white border border-yellow-500 rounded-lg shadow-lg p-4 z-50 max-w-sm">
          <h3 className="font-bold mb-2">Development Mode Active</h3>
          <p className="text-sm text-gray-600 mb-3">
            All forms will be auto-filled with test data for faster development.
          </p>
          
          <div className="mb-3 p-2 bg-gray-50 rounded text-xs">
            <p className="font-semibold mb-1">Config Source:</p>
            {isLoading ? (
              <p className="text-gray-500">Loading backend configuration...</p>
            ) : hasBackendConfig ? (
              <p className="text-green-600">✓ Using backend environment values</p>
            ) : (
              <>
                <p className="text-amber-600">✗ Using fallback values</p>
                {error && <p className="text-gray-500 mt-1">{error}</p>}
              </>
            )}
          </div>
          
          <div className="space-y-1 text-xs">
            <p>✓ PagerDuty integration</p>
            <p>✓ Kubernetes contexts</p>
            <p>✓ LLM API keys</p>
            <p>✓ Other integrations</p>
          </div>
          <button 
            className="mt-3 text-xs text-gray-500 hover:text-gray-700"
            onClick={(e) => {
              e.stopPropagation();
              setShowDetails(false);
            }}
          >
            Click to dismiss
          </button>
        </div>
      )}
    </>
  );
}