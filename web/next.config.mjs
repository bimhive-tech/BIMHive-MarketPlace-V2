/** @type {import('next').NextConfig} */

// In dev, proxy /api/* to the Django backend so the whole app is one origin
// (mirrors the single-service production topology). See ARCHITECTURE §3.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  // DRF router URLs (categories/, tags/, etc.) require a trailing slash. Without
  // this, Next's own trailing-slash redirect fires before the rewrite below can
  // forward the request, stripping the slash and breaking those endpoints.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_INTERNAL_URL}/api/:path*` },
      { source: "/admin/:path*", destination: `${API_INTERNAL_URL}/admin/:path*` },
    ];
  },
};

export default nextConfig;
