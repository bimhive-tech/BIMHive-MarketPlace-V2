"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BillingToggle } from "@/components/BillingToggle/BillingToggle";
import { Button } from "@/components/Button/Button";
import { Icon, type IconName } from "@/components/Icon/Icon";
import { QtyStepper } from "@/components/QtyStepper/QtyStepper";
import { AccountApiError, claimFreeProduct } from "@/lib/accountApi";
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

export function BuyBox({ product }: { product: ProductDetail }) {
  if (product.is_free) return <FreeBuyBox product={product} />;
  return <PaidBuyBox product={product} />;
}

/** Checkout isn't built yet — free products skip it entirely via a direct claim. */
function FreeBuyBox({ product }: { product: ProductDetail }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [claiming, setClaiming] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    me().then(setUser);
  }, []);

  async function handleClaim() {
    setError("");
    setClaiming(true);
    try {
      await claimFreeProduct(product.slug);
      setClaimed(true);
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't add this to your account.");
    } finally {
      setClaiming(false);
    }
  }

  return (
    <aside className={styles.box}>
      <div className={styles.price}>Free</div>

      {claimed ? (
        <div className={styles.actions}>
          <p className={styles.claimedNote}>It&apos;s in your account.</p>
          <Button size="lg" fullWidth href="/account/downloads">
            <Icon name="download" size={18} />
            Go to Downloads
          </Button>
        </div>
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

      <ul className={styles.assurances}>
        {ASSURANCES.filter((a) => a.title !== "Secure Checkout").map((a) => (
          <li key={a.title} className={styles.assurance}>
            <Icon name={a.icon} size={20} className={styles.assuranceIcon} />
            <div>
              <p className={styles.assuranceTitle}>{a.title}</p>
              <p className={styles.assuranceSub}>{a.sub}</p>
            </div>
          </li>
        ))}
      </ul>
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

function PaidBuyBox({ product }: { product: ProductDetail }) {
  const router = useRouter();
  const { items, addItem, setQty } = useCart();
  // Defaults to yearly — the better-value plan is what gets led with, same
  // as most subscription pricing pages. Named billingInterval, not
  // "interval", so it doesn't shadow window.setInterval.
  const [billingInterval, setBillingInterval] = useState<"monthly" | "yearly">("yearly");

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
      {product.is_subscription && (
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
      {product.promotion && (
        <p className={styles.promoNote}>
          {product.promotion.discount_percent}% off — {product.promotion.headline}
        </p>
      )}
      {product.is_subscription && billingInterval === "yearly" && unitPrice > 0 && (
        <p className={styles.priceEquivalent}>
          {formatPrice(unitPrice / 12, product.currency)}/mo billed annually
        </p>
      )}

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

      <MembershipCallout product={product} />

      {product.has_trial && <TrialDownloadCard product={product} />}

      <ul className={styles.assurances}>
        {ASSURANCES.map((a) => (
          <li key={a.title} className={styles.assurance}>
            <Icon name={a.icon} size={20} className={styles.assuranceIcon} />
            <div>
              <p className={styles.assuranceTitle}>{a.title}</p>
              <p className={styles.assuranceSub}>{a.sub}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
