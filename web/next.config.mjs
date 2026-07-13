/** @type {import('next').NextConfig} */

// In dev, proxy /api/* to the Django backend so the whole app is one origin
// (mirrors the single-service production topology). See ARCHITECTURE §3.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

// Cover images / gallery media are stored in R2 and referenced by absolute URL;
// next/image refuses to optimize a remote host it doesn't know about, so the
// bucket's public host (derived from env, never hardcoded) has to be allow-listed.
// Local dev without R2 configured falls back to just allowing the MinIO container
// docker-compose already starts on a fixed local port.
const remotePatterns = [{ protocol: "http", hostname: "localhost", port: "9000" }];
if (process.env.R2_PUBLIC_BASE_URL) {
  const r2 = new URL(process.env.R2_PUBLIC_BASE_URL);
  remotePatterns.push({ protocol: r2.protocol.replace(":", ""), hostname: r2.hostname });
}

const nextConfig = {
  reactStrictMode: true,
  // Standalone output is what the production Dockerfile runs (see /Dockerfile) —
  // a self-contained server bundle instead of requiring the full node_modules tree.
  output: "standalone",
  images: { remotePatterns },
  // DRF router URLs (categories/, tags/, etc.) require a trailing slash. Without
  // this, Next's own trailing-slash redirect fires before the rewrite below can
  // forward the request, stripping the slash and breaking those endpoints.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_INTERNAL_URL}/api/:path*` },
      { source: "/admin/:path*", destination: `${API_INTERNAL_URL}/admin/:path*` },
      // Django's own /admin (separate from /admin-portal) needs its static assets
      // (CSS/JS) proxied too, or its pages render unstyled.
      { source: "/static/:path*", destination: `${API_INTERNAL_URL}/static/:path*` },
    ];
  },
};

export default nextConfig;
