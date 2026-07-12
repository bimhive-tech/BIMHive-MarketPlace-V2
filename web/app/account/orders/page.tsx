"use client";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { RequireAuth } from "@/features/auth/RequireAuth/RequireAuth";

import styles from "../section.module.css";

export default function OrdersPage() {
  return (
    <RequireAuth>
      {() => (
        <div className={`container ${styles.section}`}>
          <h1 className={styles.title}>Orders &amp; Invoices</h1>
          <p className={styles.sub}>Your purchase history and downloadable receipts.</p>
          <EmptyState
            icon="document"
            title="No orders yet"
            text="Once you complete a purchase, your orders and invoices will be listed here."
            actionLabel="Browse the marketplace"
            actionHref="/catalog"
          />
        </div>
      )}
    </RequireAuth>
  );
}
