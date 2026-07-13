"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Pill } from "@/components/Pill/Pill";
import { getAccountOrders, type AccountOrder } from "@/lib/accountApi";
import { paymentStatusTone } from "@/features/account/paymentStatusTone";

import styles from "./OrdersList.module.css";

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function OrdersList() {
  const [orders, setOrders] = useState<AccountOrder[] | null>(null);

  useEffect(() => {
    getAccountOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  if (orders === null) return <p className={styles.loading}>Loading your orders…</p>;

  if (orders.length === 0) {
    return (
      <EmptyState
        icon="document"
        title="No orders yet"
        text="Once you complete a purchase, your orders and invoices will be listed here."
        actionLabel="Browse the marketplace"
        actionHref="/catalog"
      />
    );
  }

  return (
    <div className={styles.list}>
      {orders.map((order) => (
        <div key={order.id} className={styles.row}>
          <div className={styles.main}>
            <span className={styles.product}>{order.product_name}</span>
            <span className={styles.code}>{order.product_code}</span>
          </div>
          <span className={styles.date}>{formatDate(order.paid_at ?? order.requested_at)}</span>
          <span className={styles.amount}>
            {order.amount} {order.currency}
          </span>
          <Pill tone={paymentStatusTone(order.payment_status)}>{order.payment_status}</Pill>
        </div>
      ))}
    </div>
  );
}
