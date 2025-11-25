import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',

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
  typescript: {
    // ⚠️ Dangerously allow production builds to successfully complete even if
    // your project has type errors.
    ignoreBuildErrors: true,
  },
  env: {
    // Make sure environment variables are available during build
    POSTGRES_URL: process.env.POSTGRES_URL || 'postgresql://placeholder:placeholder@localhost:5432/placeholder',
  },
  async rewrites() {
    // Use environment variable for API URL, fallback to localhost for development
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    return [
      // Note: API key management is handled by frontend database, not backend
      // This excludes /api/v1/api-keys/* from being proxied to backend
      {
        source: '/api/v1/alerts/:path*',
        destination: `${apiUrl}/api/v1/alerts/:path*`, // Backend API server
      },
      {
        source: '/api/v1/integrations/:path*',
        destination: `${apiUrl}/api/v1/integrations/:path*`, // Backend API server
      },
      {
        source: '/api/v1/webhook/:path*',
        destination: `${apiUrl}/api/v1/webhook/:path*`, // Backend API server
      },
      {
        source: '/api/v1/settings/:path*',
        destination: `${apiUrl}/api/v1/settings/:path*`, // Backend API server
      },
      {
        source: '/api/v1/agent-logs/:path*',
        destination: `${apiUrl}/api/v1/agent-logs/:path*`, // Backend SSE stream for agent logs
      },
      {
        source: '/api/v1/agent/:path*',
        destination: `${apiUrl}/api/v1/agent/:path*`, // Backend agent endpoints
      },
      {
        source: '/api/v1/incidents/:path*',
        destination: `${apiUrl}/api/v1/incidents/:path*`, // Backend incidents endpoints
      },
    ];
  },
};

export default nextConfig;
