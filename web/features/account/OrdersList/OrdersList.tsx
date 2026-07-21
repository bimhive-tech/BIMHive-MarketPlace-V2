"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Pill } from "@/components/Pill/Pill";
import { AccountApiError, getAccountOrders, refundOrder, type AccountOrder } from "@/lib/accountApi";
import { paymentStatusTone } from "@/features/account/paymentStatusTone";

import styles from "./OrdersList.module.css";

const REFUND_WINDOW_DAYS = 30;

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function isWithinRefundWindow(order: AccountOrder): boolean {
  if (!order.paid_at) return false;
  const daysSincePaid = (Date.now() - new Date(order.paid_at).getTime()) / (1000 * 60 * 60 * 24);
  return daysSincePaid <= REFUND_WINDOW_DAYS;
}

export function OrdersList() {
  const [orders, setOrders] = useState<AccountOrder[] | null>(null);
  const [refundingId, setRefundingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getAccountOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  async function onRefund(order: AccountOrder) {
    const confirmed = window.confirm(
      `Cancel and refund ${order.product_name}? This immediately ends the license — any machine already activated on it will lose access.`,
    );
    if (!confirmed) return;
    setError("");
    setRefundingId(order.id);
    try {
      const updated = await refundOrder(order.id);
      setOrders((list) => (list ?? []).map((o) => (o.id === updated.id ? updated : o)));
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Could not refund this order.");
    } finally {
      setRefundingId(null);
    }
  }

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
      {error && <p className={styles.error}>{error}</p>}
      {orders.map((order) => (
        <div key={order.id} className={styles.row}>
          <div className={styles.main}>
            <span className={styles.product}>{order.product_name}</span>
            <span className={styles.code}>{order.product_code}</span>
          </div>
          <span className={styles.date}>{formatDate(order.paid_at ?? order.requested_at)}</span>
          <span className={styles.amount}>
            {order.amount} {order.currency}
            {order.billing_period && <span className={styles.interval}>/{order.billing_period === "yearly" ? "yr" : "mo"}</span>}
          </span>
          {order.is_trial && <Pill tone="gold">Trial</Pill>}
          <Pill tone={paymentStatusTone(order.payment_status)}>{order.payment_status}</Pill>
          {!order.is_trial && order.payment_status === "paid" && isWithinRefundWindow(order) && (
            <button
              type="button"
              className={styles.refundBtn}
              disabled={refundingId === order.id}
              onClick={() => onRefund(order)}
            >
              {refundingId === order.id ? "Refunding…" : "Cancel & Refund"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
