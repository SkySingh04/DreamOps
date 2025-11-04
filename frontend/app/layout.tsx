import './globals.css';
import type { Metadata, Viewport } from 'next';
import { Manrope } from 'next/font/google';
import { Providers } from '@/lib/providers';
import { DevModeIndicator } from '@/components/dev-mode-indicator';

export const metadata: Metadata = {
  title: 'DreamOps',
  description: 'Dream easy while AI takes your on-call duty. AI-powered incident response and infrastructure management platform for DevOps teams.'
};

export const viewport: Viewport = {
  maximumScale: 1
};

const manrope = Manrope({ subsets: ['latin'] });

export default async function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`bg-white dark:bg-gray-950 text-black dark:text-white ${manrope.className}`}
    >
      <body className="min-h-[100dvh] bg-gray-50" suppressHydrationWarning>
        <Providers>
          {children}
          <DevModeIndicator />
        </Providers>
      </body>
    </html>
  );
}
