"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AccountApiError, checkout } from "@/lib/accountApi";
import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { Button } from "@/components/Button/Button";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { formatPrice } from "@/config/site";
import { useCart } from "@/lib/cart";
import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./page.module.css";

const CONFIRMATION_STORAGE_KEY = "bimhive.checkout.confirmation";

export default function CheckoutPage() {
  const router = useRouter();
  const { items, subtotal, clear } = useCart();
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [placing, setPlacing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    me().then(setUser);
  }, []);

  async function onCompletePurchase() {
    setError("");
    setPlacing(true);
    try {
      const { purchases } = await checkout(items.map((i) => ({ slug: i.slug, qty: i.qty })));
      sessionStorage.setItem(CONFIRMATION_STORAGE_KEY, JSON.stringify(purchases));
      clear();
      router.push("/checkout/confirmation");
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Could not complete the purchase.");
    } finally {
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
          {items.map((item) => (
            <li key={item.key} className={styles.item}>
              <div className={styles.itemInfo}>
                <span className={styles.itemName}>{item.name}</span>
                <span className={styles.itemQty}>Qty {item.qty}</span>
              </div>
              <span className={styles.lineTotal}>{formatPrice(item.unitPrice * item.qty, item.currency)}</span>
            </li>
          ))}
        </ul>

        <aside className={styles.summary}>
          <h2 className={styles.summaryTitle}>Order Summary</h2>
          <div className={`${styles.summaryRow} ${styles.summaryTotal}`}>
            <span>Total</span>
            <span>{formatPrice(subtotal, items[0]?.currency ?? "USD")}</span>
          </div>

          <div className={styles.testNotice}>
            <Icon name="help" size={16} className={styles.testNoticeIcon} />
            <p>
              No payment processor is connected yet — this completes the purchase without collecting a card, for
              testing the license flow end to end.
            </p>
          </div>

          {error && <p className={styles.error}>{error}</p>}

          <Button size="lg" fullWidth onClick={onCompletePurchase} disabled={placing || user === undefined}>
            {placing ? "Placing order…" : "Complete Purchase"}
          </Button>
        </aside>
      </div>
    </div>
  );
}
