/** Site-wide constants and navigation config (no magic strings in components). */
import type { IconName } from "@/components/Icon/Icon";

const DEFAULT_SITE_URL = "http://localhost:3000";

// NEXT_PUBLIC_SITE_URL is often templated from a platform-provided domain (e.g.
// Railway's ${{RAILWAY_PUBLIC_DOMAIN}}) that isn't assigned yet on a service's
// first build, leaving a truthy-but-incomplete value like "https://" — which
// `||` doesn't catch, but a real URL parse does. metadataBase (app/layout.tsx)
// depends on this always being well-formed.
function resolveSiteUrl(): string {
  const raw = process.env.NEXT_PUBLIC_SITE_URL;
  if (!raw) return DEFAULT_SITE_URL;
  try {
    return new URL(raw).toString();
  } catch {
    return DEFAULT_SITE_URL;
  }
}

export const SITE = {
  name: "BIMHIVE",
  tagline: "Digital tools for smarter construction.",
  description:
    "Explore plugins, automation tools, and digital solutions designed for the AEC industry.",
  url: resolveSiteUrl(),
  support: { usersWorldwide: "10,000+" },
} as const;

/** Top-nav dropdown groups. */
export const NAV_LINKS = [
  { label: "Categories", href: "/catalog" },
  { label: "Solutions", href: "/solutions" },
  { label: "Resources", href: "/resources" },
] as const;

/** Trust badges shown under the hero. */
export const TRUST_BADGES = [
  { icon: "users", title: "Trusted by AEC Professionals", subtitle: "10,000+ users worldwide" },
  { icon: "award", title: "Premium Digital Products", subtitle: "Quality tools you can rely on" },
  { icon: "shield", title: "Secure Payments", subtitle: "Safe & encrypted checkout" },
  { icon: "download", title: "Instant Downloads", subtitle: "Get started right away" },
] as const;

/** Collection slug → icon, shared between the home page's CollectionsRow teaser and the full /collections index. */
export const COLLECTION_ICON_BY_SLUG: Record<string, IconName> = {
  "revit-essentials": "template",
  "automation-suite": "workflow",
  "bim-management": "library",
  "data-analytics": "chart",
};

export const CURRENCY_SYMBOL: Record<string, string> = { USD: "$", EUR: "€", GBP: "£" };

export function formatPrice(amount: number | string, currency = "USD"): string {
  const value = typeof amount === "string" ? parseFloat(amount) : amount;
  if (!value || value <= 0) return "Free";
  return `${CURRENCY_SYMBOL[currency] ?? "$"}${value.toFixed(2)}`;
}
