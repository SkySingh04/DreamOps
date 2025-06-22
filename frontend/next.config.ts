import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
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
  // Note: rewrites are not supported in static export mode
};

export default nextConfig;
