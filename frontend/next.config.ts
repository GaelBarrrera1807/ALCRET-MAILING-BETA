import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  output: "standalone",
  trailingSlash: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*/',
        destination: `${process.env.API_PROXY_URL || 'http://backend:8000'}/api/:path*/`,
      },
    ]
  },
}

export default nextConfig
