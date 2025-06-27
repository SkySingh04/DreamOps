'use client';

import { useEffect } from 'react';
import { toast } from 'sonner';
import { AlertTriangle, Key, CheckCircle } from 'lucide-react';

interface KeyStatusToastProps {
  primaryKeyExhausted?: boolean;
  hasWorkingKeys: boolean;
  primaryKey?: any;
  activeKeys: any[];
}

export function KeyStatusToast({
  primaryKeyExhausted,
  hasWorkingKeys,
  primaryKey,
  activeKeys,
}: KeyStatusToastProps) {
  useEffect(() => {
    if (primaryKeyExhausted && hasWorkingKeys) {
      // Primary key exhausted but we have backups
      const backupKey = activeKeys.find(k => !k.is_primary);
      if (backupKey) {
        toast.warning(
          `Primary API key exhausted. Switched to backup key: ${backupKey.name}`,
          {
            icon: <AlertTriangle className="h-4 w-4" />,
            duration: 8000,
            action: {
              label: 'Manage Keys',
              onClick: () => window.location.href = '/settings',
            },
          }
        );
      }
    }
  }, [primaryKeyExhausted, hasWorkingKeys, activeKeys]);

  return null;
}