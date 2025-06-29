'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from 'sonner';
import { useState } from 'react';
import { AuthProvider } from './firebase/auth-context';
import { DemoProvider } from './demo/DemoContext';
import { DemoOverlay } from '@/components/demo/DemoOverlay';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
            retry: 3,
          },
        },
      })
  );

  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <DemoProvider>
          {children}
          <DemoOverlay />
          <Toaster 
            richColors 
            position="top-right"
            toastOptions={{
              style: {
                background: 'var(--background)',
                color: 'var(--foreground)',
                border: '1px solid var(--border)',
              },
            }}
          />
          <ReactQueryDevtools initialIsOpen={false} />
        </DemoProvider>
      </QueryClientProvider>
    </AuthProvider>
  );
}