import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Setup - DreamOps',
  description: 'Configure your AI-powered incident response platform',
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      {children}
    </div>
  );
}