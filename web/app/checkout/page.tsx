"use client";

import { useEffect, useState } from "react";

import { AccountApiError, checkout } from "@/lib/accountApi";
import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { Button } from "@/components/Button/Button";
import { BillingToggle } from "@/components/BillingToggle/BillingToggle";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { formatPrice } from "@/config/site";
import { type CartItem, useCart } from "@/lib/cart";
import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./page.module.css";

// Mirrors Product.yearly_savings_percent's formula server-side (see
// catalog/models/product.py) so the checkout badge and the product page's
// own BillingToggle always agree — null (no badge) whenever yearly isn't
// actually the cheaper option, never a misleading 0%/negative discount.
function yearlySavingsPercent(item: CartItem): number | null {
  if (!item.monthlyPrice || !item.yearlyPrice) return null;
  const yearlyEquivalentOfMonthly = item.monthlyPrice * 12;
  if (item.yearlyPrice >= yearlyEquivalentOfMonthly) return null;
  return Math.round((1 - item.yearlyPrice / yearlyEquivalentOfMonthly) * 100);
}

function subscriptionSummaryLabel(items: CartItem[]): string {
  const subscriptionItems = items.filter((i) => i.billingPeriod);
  const periods = new Set(subscriptionItems.map((i) => i.billingPeriod));
  const noun = subscriptionItems.length === 1 ? "subscription item" : "subscription items";
  if (periods.size === 1) {
    const period = periods.has("yearly") ? "yearly" : "monthly";
    return `Includes ${subscriptionItems.length} ${period} ${noun}`;
  }
  return `Includes ${subscriptionItems.length} ${noun} (mixed monthly/yearly)`;
}

export default function CheckoutPage() {
  const { items, subtotal, setBillingPeriod } = useCart();
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState("");
  const hasSubscriptionItems = items.some((i) => i.billingPeriod);

  useEffect(() => {
    me().then(setUser);
  }, []);

  // Cart is deliberately NOT cleared here — the customer isn't done yet,
  // they're about to be sent to Paymob's hosted checkout to actually pay.
  // It only clears once /checkout/confirmation sees the payment actually
  // confirmed, so an abandoned/failed Paymob attempt doesn't lose the cart.
  async function onCompletePurchase() {
    setError("");
    setPlacing(true);
    try {
      const { checkoutUrl } = await checkout(
        items.map((i) => ({ slug: i.slug, qty: i.qty, billingPeriod: i.billingPeriod })),
      );
      window.location.href = checkoutUrl;
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Could not start payment.");
      setPlacing(false);
    }
  }

  if (items.length === 0) {
    return (
      <div className={`container ${styles.page}`}>
        <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Cart", href: "/cart" }, { label: "Checkout" }]} />
        <EmptyState
          icon="cart"
          title="Your cart is empty"
          text="Add something from the marketplace before checking out."
          actionLabel="Browse the marketplace"
          actionHref="/catalog"
        />
      </div>
    );
  }

  if (user === null) {
    return (
      <div className={`container ${styles.page}`}>
        <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Cart", href: "/cart" }, { label: "Checkout" }]} />
        <EmptyState
          icon="lock"
          title="Log in to check out"
          text="Your cart is saved — sign in to complete the purchase."
          actionLabel="Log in"
          actionHref="/login?next=/checkout"
        />
      </div>
    );
  }

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Cart", href: "/cart" }, { label: "Checkout" }]} />
      <h1 className={styles.title}>Checkout</h1>

      <div className={styles.layout}>
        <ul className={styles.items}>
          {items.map((item) => {
            const canSwitchInterval = item.monthlyPrice != null && item.yearlyPrice != null;
            return (
              <li key={item.key} className={styles.item}>
                <div className={styles.itemTop}>
                  <div className={styles.itemInfo}>
                    <span className={styles.itemNameRow}>
                      <span className={styles.itemName}>{item.name}</span>
                      {item.billingPeriod && (
                        <Pill tone="gold">{item.billingPeriod === "yearly" ? "Yearly subscription" : "Monthly subscription"}</Pill>
                      )}
                    </span>
                    <span className={styles.itemQty}>Qty {item.qty}</span>
                  </div>
                  <span className={styles.lineTotal}>
                    {formatPrice(item.unitPrice * item.qty, item.currency)}
                    {item.billingPeriod && (
                      <span className={styles.interval}>/{item.billingPeriod === "yearly" ? "yr" : "mo"}</span>
                    )}
                  </span>
                </div>

                {item.billingPeriod && (
                  <div className={styles.itemBilling}>
                    {canSwitchInterval && (
                      <BillingToggle
                        value={item.billingPeriod}
                        onChange={(period) => setBillingPeriod(item.key, period)}
                        yearlySavingsPercent={yearlySavingsPercent(item)}
                      />
                    )}
                    <span className={styles.recurringNote}>
                      <Icon name="clock" size={13} /> This payment covers your first{" "}
                      {item.billingPeriod === "yearly" ? "year" : "month"}. Renewals aren't automatic yet
                      — you'll need to check out again before it expires to keep your access active.
                    </span>
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        <aside className={styles.summary}>
          <h2 className={styles.summaryTitle}>Order Summary</h2>
          <div className={`${styles.summaryRow} ${styles.summaryTotal}`}>
            <span>Total</span>
            <span>{formatPrice(subtotal, items[0]?.currency ?? "USD")}</span>
          </div>
          {hasSubscriptionItems && (
            <p className={styles.summarySub}>
              {subscriptionSummaryLabel(items)} — covers the period selected above; renewal isn't
              automatic yet.
            </p>
          )}

          <div className={styles.testNotice}>
            <Icon name="help" size={16} className={styles.testNoticeIcon} />
            <p>You&apos;ll be taken to Paymob&apos;s secure checkout to pay — card details never touch this site.</p>
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <Button size="lg" fullWidth onClick={onCompletePurchase} disabled={placing || user === undefined}>
            {placing ? "Redirecting to payment…" : "Continue to Payment"}
          </Button>
        </aside>
      </div>
    </div>
  );
}
