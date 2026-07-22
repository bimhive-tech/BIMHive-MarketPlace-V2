"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { formatPrice } from "@/config/site";
import { getAccountSubscriptions, type AccountSubscription } from "@/lib/accountApi";

import styles from "./SubscriptionsList.module.css";

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function statusTone(status: AccountSubscription["license_status"]): "success" | "warning" | "error" {
  if (status === "active") return "success";
  if (status === "expired") return "error";
  return "warning";
}

export function SubscriptionsList() {
  const [subscriptions, setSubscriptions] = useState<AccountSubscription[] | null>(null);

  useEffect(() => {
    getAccountSubscriptions()
      .then(setSubscriptions)
      .catch(() => setSubscriptions([]));
  }, []);

  if (subscriptions === null) return <p className={styles.loading}>Loading your subscriptions…</p>;

  if (subscriptions.length === 0) {
    return (
      <EmptyState
        icon="refresh"
        title="No subscriptions yet"
        text="Monthly or yearly plans you buy will appear here with their renewal date."
        actionLabel="Browse the marketplace"
        actionHref="/catalog"
      />
    );
  }

  return (
    <div className={styles.list}>
      {subscriptions.map((sub) => (
        <div key={sub.id} className={styles.card}>
          <div className={styles.head}>
            <div>
              <span className={styles.product}>{sub.product_name}</span>
              <span className={styles.code}>{sub.product_code}</span>
            </div>
            <div className={styles.headPills}>
              <Pill tone="gold">{sub.billing_period === "yearly" ? "Yearly" : "Monthly"}</Pill>
              <Pill tone={statusTone(sub.license_status)}>{sub.license_status}</Pill>
            </div>
          </div>

          <div className={styles.meta}>
            <span>
              {formatPrice(Number(sub.amount), sub.currency)}/{sub.billing_period === "yearly" ? "yr" : "mo"}
            </span>
            {sub.expires_at && (
              <span className={sub.is_expiring_soon ? styles.expiringSoon : undefined}>
                <Icon name="clock" size={14} />
                {sub.license_status === "expired" ? "Expired" : "Renews or expires"} {formatDate(sub.expires_at)}
              </span>
            )}
          </div>

          {(sub.is_expiring_soon || sub.license_status === "expired") && (
            <div className={styles.renewRow}>
              <p className={styles.renewNote}>
                {sub.license_status === "expired"
                  ? "This subscription has expired. Renewals aren't automatic — buy another period to keep using it."
                  : "Expiring soon. Renewals aren't automatic — buy another period before it lapses."}
              </p>
              {sub.product_slug && (
                <a className={styles.renewLink} href={`/products/${sub.product_slug}`}>
                  Renew now <Icon name="chevron-right" size={14} />
                </a>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
