import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  env: {
    POSTGRES_URL: 'postgresql://placeholder:placeholder@localhost:5432/placeholder',
  },
  // Remove rewrites for static export
};

export default nextConfig;