"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BillingToggle } from "@/components/BillingToggle/BillingToggle";
import { Button } from "@/components/Button/Button";
import { Icon, type IconName } from "@/components/Icon/Icon";
import { QtyStepper } from "@/components/QtyStepper/QtyStepper";
import { AccountApiError, claimFreeProduct, getAccountLicenses } from "@/lib/accountApi";
import { me } from "@/lib/auth";
import { formatPrice } from "@/config/site";
import { type BillingPeriod, useCart } from "@/lib/cart";
import { listPrice, unitPrice as priceForPeriod } from "@/lib/pricing";
import { MembershipCallout } from "@/features/product/MembershipCallout/MembershipCallout";
import { TrialDownloadCard } from "@/features/product/TrialDownloadCard/TrialDownloadCard";
import type { ProductDetail, User } from "@/lib/types";

import styles from "./BuyBox.module.css";

const ASSURANCES: { icon: IconName; title: string; sub: string }[] = [
  { icon: "download", title: "Instant Download", sub: "Get started right away" },
  { icon: "shield", title: "30-Day Money Back Guarantee", sub: "Risk-free and hassle-free" },
  { icon: "lock", title: "Secure Checkout", sub: "Your data is protected" },
];

function Assurances({ items }: { items: typeof ASSURANCES }) {
  return (
    <ul className={styles.assurances}>
      {items.map((a) => (
        <li key={a.title} className={styles.assurance}>
          <Icon name={a.icon} size={20} className={styles.assuranceIcon} />
          <div>
            <p className={styles.assuranceTitle}>{a.title}</p>
            <p className={styles.assuranceSub}>{a.sub}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Whether the viewer already holds a real, active, non-trial license for a
 * product — a claimed free product or a real purchase, never a lapsed trial
 * (see fetchOwnership). Null while loading or when there's no active one. */
type Ownership = { billingPeriod: "" | "monthly" | "yearly" } | null;

/** Client-side only, on purpose: the product detail page itself is fetched
 * server-side with no session cookie and is cached for a minute (see
 * lib/api.ts), so it can never know who's viewing — the same reason
 * FreeBuyBox already checks auth state (`me()`) this way instead of via the
 * product prop. Reuses the account's own licenses list rather than a new
 * endpoint; a 401 (logged out) just resolves to "not owned". */
async function fetchOwnership(productSlug: string): Promise<Ownership> {
  try {
    const licenses = await getAccountLicenses();
    const active = licenses.find(
      (l) => l.product_slug === productSlug && !l.is_trial && l.license_status === "active",
    );
    return active ? { billingPeriod: active.billing_period } : null;
  } catch {
    return null;
  }
}

/** Swaps in for the buy actions once the viewer already holds this product —
 * there's nothing to add to cart, so don't offer to sell it to them again. */
function OwnedNotice({ billingPeriod }: { billingPeriod: "" | "monthly" | "yearly" }) {
  const label = billingPeriod ? `Current Plan — ${billingPeriod === "yearly" ? "Yearly" : "Monthly"}` : "Owned";
  return (
    <div className={styles.actions}>
      <p className={styles.ownedNote}>
        <Icon name="check-circle" size={18} className={styles.ownedIcon} />
        {label}
      </p>
      <Button size="lg" fullWidth href="/account/downloads">
        <Icon name="download" size={18} />
        Go to Downloads
      </Button>
    </div>
  );
}

export function BuyBox({ product }: { product: ProductDetail }) {
  const [ownership, setOwnership] = useState<Ownership>(null);

  useEffect(() => {
    fetchOwnership(product.slug).then(setOwnership);
  }, [product.slug]);

  if (product.is_free) return <FreeBuyBox product={product} ownership={ownership} setOwnership={setOwnership} />;
  return <PaidBuyBox product={product} ownership={ownership} />;
}

/** Checkout isn't built yet — free products skip it entirely via a direct claim. */
function FreeBuyBox({
  product,
  ownership,
  setOwnership,
}: {
  product: ProductDetail;
  ownership: Ownership;
  setOwnership: (o: Ownership) => void;
}) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [claiming, setClaiming] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    me().then(setUser);
  }, []);

  async function handleClaim() {
    setError("");
    setClaiming(true);
    try {
      await claimFreeProduct(product.slug);
      setOwnership({ billingPeriod: "" });
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't add this to your account.");
    } finally {
      setClaiming(false);
    }
  }

  return (
    <aside className={styles.box}>
      <div className={styles.price}>Free</div>

      {ownership ? (
        <OwnedNotice billingPeriod={ownership.billingPeriod} />
      ) : user === null ? (
        <div className={styles.actions}>
          <Button size="lg" fullWidth href={`/login?next=/products/${product.slug}`}>
            Log in to get this for free
          </Button>
        </div>
      ) : (
        <div className={styles.actions}>
          {error && <p className={styles.claimError}>{error}</p>}
          <Button size="lg" fullWidth onClick={handleClaim} disabled={claiming || user === undefined}>
            <Icon name="download" size={18} />
            {claiming ? "Adding to your account…" : "Get for Free"}
          </Button>
        </div>
      )}

      <Assurances items={ASSURANCES.filter((a) => a.title !== "Secure Checkout")} />
    </aside>
  );
}

/** A subscription interval's price for the cart, discount included — undefined
 * when this product isn't sold on that interval at all. */
function subscriptionPrice(product: ProductDetail, interval: "monthly" | "yearly"): number | undefined {
  const listed = interval === "monthly" ? product.monthly_price : product.yearly_price;
  if (!product.is_subscription || listed == null) return undefined;
  return priceForPeriod(product, interval);
}

function PaidBuyBox({ product, ownership }: { product: ProductDetail; ownership: Ownership }) {
  const router = useRouter();
  const { items, addItem, setQty } = useCart();
  // Defaults to yearly — the better-value plan is what gets led with, same
  // as most subscription pricing pages. Named billingInterval, not
  // "interval", so it doesn't shadow window.setInterval. Already-owned:
  // shows the interval actually on the account, not the upsell default.
  const [billingInterval, setBillingInterval] = useState<"monthly" | "yearly">(
    ownership?.billingPeriod === "monthly" ? "monthly" : "yearly",
  );
  // Ownership resolves after mount (see fetchOwnership) — sync once it does,
  // so the price display never disagrees with the "Current Plan" label.
  useEffect(() => {
    if (ownership?.billingPeriod === "monthly" || ownership?.billingPeriod === "yearly") {
      setBillingInterval(ownership.billingPeriod);
    }
  }, [ownership]);

  const billingPeriod: BillingPeriod = product.is_subscription ? billingInterval : "";
  // Discount included when a promotion is live — the same figure checkout
  // recomputes server-side (see lib/pricing.ts).
  const unitPrice = priceForPeriod(product, billingPeriod);
  const wasPrice = listPrice(product, billingPeriod);
  const cartItem = items.find((i) => i.productId === product.id && (i.billingPeriod ?? "") === billingPeriod);

  function handleAddToCart() {
    addItem({
      productId: product.id,
      slug: product.slug,
      name: product.name,
      coverImageUrl: product.cover_image_url,
      unitPrice,
      currency: product.currency,
      billingPeriod,
      // Only set for a subscription — and only when that interval actually
      // has a price (a monthly-only or yearly-only subscription leaves the
      // other one null) — lets the cart/checkout switch monthly<->yearly
      // later without a fresh API call (see lib/cart.tsx). Discounted, so
      // switching interval in the cart doesn't jump back to list price.
      monthlyPrice: subscriptionPrice(product, "monthly"),
      yearlyPrice: subscriptionPrice(product, "yearly"),
    });
  }

  function handleBuyNow() {
    if (!cartItem) handleAddToCart();
    router.push("/cart");
  }

  return (
    <aside className={styles.box}>
      {!ownership && product.is_subscription && (
        <BillingToggle
          value={billingInterval}
          onChange={setBillingInterval}
          yearlySavingsPercent={product.yearly_savings_percent}
        />
      )}

      <div className={styles.price}>
        <span className={product.promotion ? styles.priceSale : undefined}>
          {formatPrice(unitPrice, product.currency)}
        </span>
        {product.is_subscription && (
          <span className={styles.priceInterval}>/{billingInterval === "yearly" ? "yr" : "mo"}</span>
        )}
        {wasPrice !== null && (
          <s className={styles.priceWas}>{formatPrice(wasPrice, product.currency)}</s>
        )}
      </div>
      {!ownership && product.promotion && (
        <p className={styles.promoNote}>
          {product.promotion.discount_percent}% off — {product.promotion.headline}
        </p>
      )}
      {!ownership && product.is_subscription && billingInterval === "yearly" && unitPrice > 0 && (
        <p className={styles.priceEquivalent}>
          {formatPrice(unitPrice / 12, product.currency)}/mo billed annually
        </p>
      )}

      {ownership ? (
        <OwnedNotice billingPeriod={ownership.billingPeriod} />
      ) : (
        <div className={styles.actions}>
          {cartItem ? (
            <QtyStepper
              qty={cartItem.qty}
              onDecrease={() => setQty(cartItem.key, cartItem.qty - 1)}
              onIncrease={() => setQty(cartItem.key, cartItem.qty + 1)}
              ariaLabel={`${product.name} quantity in cart`}
              variant="full"
            />
          ) : (
            <Button size="lg" fullWidth onClick={handleAddToCart}>
              <Icon name="cart" size={18} />
              Add to Cart
            </Button>
          )}
          <Button size="lg" variant="secondary" fullWidth onClick={handleBuyNow}>
            Buy Now
          </Button>
        </div>
      )}

      <MembershipCallout product={product} />

      {product.has_trial && <TrialDownloadCard product={product} />}

      <Assurances items={ASSURANCES} />
    </aside>
  );
}
