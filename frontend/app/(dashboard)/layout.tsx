import { Suspense } from 'react';
import { Navigation } from '@/components/navigation';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <section className="flex flex-col min-h-screen">
      <Suspense fallback={<div className="h-16 border-b border-gray-200" />}>
        <Navigation />
      </Suspense>
      <main className="flex-1 bg-gray-50">
        {children}
      </main>
    </section>
  );
}
