"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { getAccountPaymentMethods, type AccountPaymentMethod } from "@/lib/accountApi";

import styles from "./PaymentMethodsList.module.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function PaymentMethodsList() {
  const [methods, setMethods] = useState<AccountPaymentMethod[] | null>(null);

  useEffect(() => {
    getAccountPaymentMethods()
      .then(setMethods)
      .catch(() => setMethods([]));
  }, []);

  return (
    <div className={styles.wrap}>
      <div className={styles.notice}>
        <Icon name="lock" size={16} className={styles.noticeIcon} />
        <p>
          Card details are entered directly on Paymob&apos;s secure checkout and never touch this
          site — there&apos;s nothing here to add or remove, just a record of which cards you&apos;ve
          used to pay.
        </p>
      </div>

      {methods === null ? (
        <p className={styles.loading}>Loading payment methods…</p>
      ) : methods.length === 0 ? (
        <EmptyState
          icon="wallet"
          title="No payment methods yet"
          text="Cards you use at checkout will be listed here once you complete a purchase."
        />
      ) : (
        <div className={styles.list}>
          {methods.map((m) => (
            <div key={`${m.card_brand}-${m.card_last4}`} className={styles.card}>
              <span className={styles.icon}>
                <Icon name="wallet" size={20} />
              </span>
              <div className={styles.info}>
                <span className={styles.brand}>
                  {m.card_brand || "Card"} •••• {m.card_last4}
                </span>
                <span className={styles.meta}>
                  Used {m.times_used} time{m.times_used === 1 ? "" : "s"} · last on {formatDate(m.last_used)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
