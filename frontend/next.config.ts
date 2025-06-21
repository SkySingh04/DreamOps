import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  experimental: {
    // ppr: true, // Requires Next.js canary version
    clientSegmentCache: true,
    nodeMiddleware: true
  }
};

export default nextConfig;
