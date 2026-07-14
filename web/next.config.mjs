/** @type {import('next').NextConfig} */

// In dev, proxy /api/* to the Django backend so the whole app is one origin
// (mirrors the single-service production topology). See ARCHITECTURE §3.
const API_INTERNAL_URL = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

// Cover images / gallery media are stored in R2 and referenced by absolute URL;
// next/image refuses to optimize a remote host it doesn't know about, so every
// host a media URL could actually use (derived from env, never hardcoded) has
// to be allow-listed. Local dev without R2 configured falls back to just
// allowing the MinIO container docker-compose already starts on a fixed local port.
const remotePatterns = [{ protocol: "http", hostname: "localhost", port: "9000" }];

// Next re-evaluates this config per page during the build; an incomplete value
// here (e.g. a placeholder still being filled in) must not fail the whole build —
// worst case is just no R2 image optimization until the value is fixed.
function addHostFromEnv(envVar) {
  const value = process.env[envVar];
  if (!value) return;
  try {
    const url = new URL(value);
    remotePatterns.push({ protocol: url.protocol.replace(":", ""), hostname: url.hostname });
  } catch {
    console.warn(`${envVar} is set but not a valid URL: "${value}"`);
  }
}

// The permanent public domain, once the bucket's public access is turned on.
addHostFromEnv("R2_PUBLIC_BASE_URL");
// R2's own API host — every media URL uses this host until R2_PUBLIC_BASE_URL is
// set, since the storage fallback (see STORAGES in api/config/settings.py) signs
// presigned URLs directly against the endpoint rather than a public domain.
addHostFromEnv("R2_ENDPOINT_URL");

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
