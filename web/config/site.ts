/** Site-wide constants and navigation config (no magic strings in components). */

export const SITE = {
  name: "BIMHIVE",
  tagline: "Digital tools for smarter construction.",
  description:
    "Explore plugins, automation tools, and digital solutions designed for the AEC industry.",
  url: process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000",
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

export const CURRENCY_SYMBOL: Record<string, string> = { USD: "$", EUR: "€", GBP: "£" };

export function formatPrice(amount: number | string, currency = "USD"): string {
  const value = typeof amount === "string" ? parseFloat(amount) : amount;
  if (!value || value <= 0) return "Free";
  return `${CURRENCY_SYMBOL[currency] ?? "$"}${value.toFixed(2)}`;
}
