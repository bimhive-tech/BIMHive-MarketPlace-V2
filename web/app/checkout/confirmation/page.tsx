"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { Button } from "@/components/Button/Button";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { AccountApiError, getCheckoutStatus, type AccountOrder } from "@/lib/accountApi";
import { useCart } from "@/lib/cart";

import styles from "./page.module.css";

// Paymob's webhook usually lands within a couple of seconds of the redirect,
// but never trust that — poll instead of assuming, and give up with a clear
// "check your orders" message rather than spinning forever if it's slow.
const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 60000;

function ConfirmationContent() {
  const reference = useSearchParams().get("reference");
  const { clear } = useCart();
  const [purchases, setPurchases] = useState<AccountOrder[] | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const [error, setError] = useState("");
  const startedAt = useRef(Date.now());

  useEffect(() => {
    if (!reference) {
      setError("Missing order reference.");
      return;
    }
    let cancelled = false;

    async function poll() {
      try {
        const status = await getCheckoutStatus(reference!);
        if (cancelled) return;
        if (!status.pending) {
          setPurchases(status.purchases);
          // Only now — payment is actually confirmed, not just attempted.
          clear();
          return;
        }
        if (Date.now() - startedAt.current > POLL_TIMEOUT_MS) {
          setTimedOut(true);
          return;
        }
        setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof AccountApiError ? err.detail : "Could not confirm your order.");
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, [reference]);

  if (error) {
    return (
      <EmptyState
        icon="x"
        title="Couldn't confirm this order"
        text={error}
        actionLabel="View my orders"
        actionHref="/account/orders"
      />
    );
  }

  if (timedOut) {
    return (
      <EmptyState
        icon="clock"
        title="Still confirming your payment"
        text="This is taking longer than usual — your order will show up on your orders page as soon as it's confirmed."
        actionLabel="View my orders"
        actionHref="/account/orders"
      />
    );
  }

  if (purchases === null) {
    return (
      <div className={styles.hero}>
        <Icon name="clock" size={40} className={styles.heroIcon} />
        <h1 className={styles.title}>Confirming your payment…</h1>
        <p className={styles.sub}>This only takes a moment.</p>
      </div>
    );
  }

  return (
    <>
      <div className={styles.hero}>
        <Icon name="check-circle" size={40} className={styles.heroIcon} />
        <h1 className={styles.title}>Thanks for your purchase</h1>
        <p className={styles.sub}>Your license keys are ready — no need to redownload anything you already have.</p>
      </div>

      <ul className={styles.orders}>
        {purchases.map((purchase) => (
          <li key={purchase.id} className={styles.order}>
            <div className={styles.orderInfo}>
              <span className={styles.orderName}>{purchase.product_name}</span>
              <span className={styles.orderMeta}>
                {purchase.seats > 1 ? `${purchase.seats} seats · ` : ""}
                <Icon name="lock" size={12} /> {purchase.license_key}
              </span>
            </div>
            <span className={styles.orderAmount}>
              {purchase.amount === "0.00" ? "Free" : `${purchase.currency} ${purchase.amount}`}
            </span>
          </li>
        ))}
      </ul>

      <div className={styles.actions}>
        <Button size="lg" href="/account/downloads">
          Go to Downloads
        </Button>
        <Button size="lg" variant="secondary" href="/account/licenses">
          View My Licenses
        </Button>
      </div>
    </>
  );
}

export default function CheckoutConfirmationPage() {
  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Checkout" }]} />
      <Suspense fallback={null}>
        <ConfirmationContent />
      </Suspense>
    </div>
  );
}
