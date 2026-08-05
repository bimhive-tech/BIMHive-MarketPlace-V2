import type { ProductCard, ProductPromotion } from "@/lib/types";

type PricedProduct = Pick<ProductCard, "price" | "monthly_price" | "yearly_price" | "promotion">;

/** Billing interval a cart line is priced on — "" is a one-time purchase. */
export type BillingPeriod = "" | "monthly" | "yearly";

/**
 * What one unit costs right now, discount included.
 *
 * Display and cart maths only. Checkout re-derives this server-side from the
 * same promotion (see catalog/pricing.py), so a stale or edited cart price can
 * never be what's actually charged.
 */
export function unitPrice(product: PricedProduct, billingPeriod: BillingPeriod = ""): number {
  const source: PricedProduct | ProductPromotion = product.promotion ?? product;
  if (billingPeriod === "monthly") return Number(source.monthly_price ?? 0);
  if (billingPeriod === "yearly") return Number(source.yearly_price ?? 0);
  return Number(source.price ?? 0);
}

/** The pre-discount price, for the struck-through figure. Null when nothing is
 * on offer, so callers can skip rendering it. */
export function listPrice(product: PricedProduct, billingPeriod: BillingPeriod = ""): number | null {
  if (!product.promotion) return null;
  if (billingPeriod === "monthly") return Number(product.monthly_price ?? 0);
  if (billingPeriod === "yearly") return Number(product.yearly_price ?? 0);
  return Number(product.price ?? 0);
}
