"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon, type IconName } from "@/components/Icon/Icon";
import { getAccountActivity, type AccountActivityEntry } from "@/lib/accountApi";

import styles from "./NotificationsFeed.module.css";

// Mirrors activity.account_api.CUSTOMER_VERBS on the backend — keep in sync.
const VERB_ICON: Record<string, IconName> = {
  signed_in: "lock",
  signed_up: "users",
  claimed_free_product: "download",
  order_placed: "cart",
  order_refund_requested: "refresh",
  downloaded_file: "download",
  posted_review: "star",
  redeemed_license_code: "library",
};

function describe(entry: AccountActivityEntry): string {
  const target = entry.target_label;
  switch (entry.verb) {
    case "signed_in":
      return "You signed in";
    case "signed_up":
      return "You created your account";
    case "claimed_free_product":
      return target ? `You claimed ${target}` : "You claimed a free product";
    case "order_placed":
      return target ? `You purchased ${target}` : "You placed an order";
    case "order_refund_requested":
      return target ? `You requested a refund for ${target}` : "You requested a refund";
    case "downloaded_file":
      return target ? `You downloaded ${target}` : "You downloaded a file";
    case "posted_review":
      return target ? `You posted a review for ${target}` : "You posted a review";
    case "redeemed_license_code":
      return target ? `You redeemed a license code for ${target}` : "You redeemed a license code";
    default:
      return target || entry.verb;
  }
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export function NotificationsFeed() {
  const [entries, setEntries] = useState<AccountActivityEntry[] | null>(null);

  useEffect(() => {
    getAccountActivity()
      .then(setEntries)
      .catch(() => setEntries([]));
  }, []);

  if (entries === null) return <p className={styles.loading}>Loading your activity…</p>;

  if (entries.length === 0) {
    return (
      <EmptyState
        icon="bell"
        title="Nothing here yet"
        text="Sign-ins, purchases, downloads, and reviews on this account will show up here."
      />
    );
  }

  return (
    <div className={styles.list}>
      {entries.map((entry) => (
        <div key={entry.id} className={styles.row}>
          <span className={styles.icon}>
            <Icon name={VERB_ICON[entry.verb] ?? "bell"} size={16} />
          </span>
          <div className={styles.info}>
            <span className={styles.message}>{describe(entry)}</span>
            <span className={styles.time}>{formatDateTime(entry.created_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
