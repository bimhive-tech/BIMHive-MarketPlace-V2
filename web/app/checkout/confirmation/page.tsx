"use client";

import { useEffect, useState } from "react";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { Button } from "@/components/Button/Button";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import type { AccountOrder } from "@/lib/accountApi";

import styles from "./page.module.css";

const CONFIRMATION_STORAGE_KEY = "bimhive.checkout.confirmation";

export default function CheckoutConfirmationPage() {
  const [purchases, setPurchases] = useState<AccountOrder[] | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem(CONFIRMATION_STORAGE_KEY);
    setPurchases(raw ? (JSON.parse(raw) as AccountOrder[]) : []);
    sessionStorage.removeItem(CONFIRMATION_STORAGE_KEY);
  }, []);

  if (purchases === null) return null;

  if (purchases.length === 0) {
    return (
      <div className={`container ${styles.page}`}>
        <EmptyState
          icon="check-circle"
          title="Nothing to confirm"
          text="Looks like you didn't just come from checkout — your recent orders are on your account page."
          actionLabel="View my orders"
          actionHref="/account/orders"
        />
      </div>
    );
  }

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Checkout" }]} />

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
    </div>
  );
}
