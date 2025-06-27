import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  experimental: {
    // ppr: true, // Requires Next.js canary version
    clientSegmentCache: true,
    // nodeMiddleware: true  // Disabled due to Next.js version compatibility
  },
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: true,
  },
  env: {
    // Make sure environment variables are available during build
    POSTGRES_URL: process.env.POSTGRES_URL || 'postgresql://placeholder:placeholder@localhost:5432/placeholder',
  },
  async rewrites() {
    return [
      // Note: API key management is handled by frontend database, not backend
      // This excludes /api/v1/api-keys/* from being proxied to backend
      {
        source: '/api/v1/alerts/:path*',
        destination: 'http://localhost:8000/api/v1/alerts/:path*', // Backend API server
      },
      {
        source: '/api/v1/integrations/:path*',
        destination: 'http://localhost:8000/api/v1/integrations/:path*', // Backend API server
      },
      {
        source: '/api/v1/webhook/:path*',
        destination: 'http://localhost:8000/api/v1/webhook/:path*', // Backend API server
      },
      {
        source: '/api/v1/settings/:path*',
        destination: 'http://localhost:8000/api/v1/settings/:path*', // Backend API server
      },
    ];
  },
};

export default nextConfig;
