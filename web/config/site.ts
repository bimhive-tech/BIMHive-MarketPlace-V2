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

/** Plain (non-dropdown) top-nav links — Solutions/Resources are mega menus, handled directly in Header.tsx. */
export const NAV_LINKS = [{ label: "Categories", href: "/catalog" }] as const;

/** Category slug → icon, shared between /catalog's filter sidebar and the header's Solutions mega menu. */
export const CATEGORY_ICON_BY_SLUG: Record<string, IconName> = {
  "revit-plugins": "puzzle",
  "automation-tools": "bolt",
  "dynamo-scripts": "workflow",
  "bim-libraries": "library",
  templates: "template",
  "training-courses": "graduation-cap",
  integrations: "plug",
  "other-tools": "wrench",
};

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

/** The /resources hub — shared between the header's Resources mega menu and the
 * full /resources page. href: null renders as a "Soon" state instead of a link;
 * only add a page here once it actually exists (see CLAUDE.md — no dead links). */
export const RESOURCE_LINKS: {
  title: string;
  description: string;
  icon: IconName;
  href: string | null;
}[] = [
  {
    title: "Documentation",
    description: "Setup guides and references for every product.",
    icon: "document",
    href: "/docs",
  },
  {
    title: "Knowledge Base",
    description: "General guides not tied to a single product.",
    icon: "help",
    href: null,
  },
  {
    title: "Blog",
    description: "News, tips, and product updates.",
    icon: "layers",
    href: null,
  },
];

/** The /sell landing page's "why sell with us" row. */
export const SELL_BENEFITS: { icon: IconName; title: string; text: string }[] = [
  {
    icon: "users",
    title: "Reach thousands of AEC professionals",
    text: "Your tools land in front of BIMHIVE's existing audience of Revit and BIM users.",
  },
  {
    icon: "shield",
    title: "Every product is reviewed",
    text: "BIMHive staff review each submission before it goes live, so buyers trust what they download.",
  },
  {
    icon: "chart",
    title: "Track your sales",
    text: "The partner dashboard shows your revenue and order history alongside your product catalog.",
  },
];

export const CURRENCY_SYMBOL: Record<string, string> = { USD: "$", EUR: "€", GBP: "£" };

export function formatPrice(amount: number | string, currency = "USD"): string {
  const value = typeof amount === "string" ? parseFloat(amount) : amount;
  if (!value || value <= 0) return "Free";
  return `${CURRENCY_SYMBOL[currency] ?? "$"}${value.toFixed(2)}`;
}
