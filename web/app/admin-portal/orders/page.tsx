"use client";

import { useEffect, useState } from "react";

import { Pill } from "@/components/Pill/Pill";
import { formatPrice } from "@/config/site";
import { getAdminOrders, setOrderStatus, type AdminOrder } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const TABS = [
  { key: "all", label: "All Orders" },
  { key: "paid", label: "Paid" },
  { key: "pending", label: "Pending" },
  { key: "refunded", label: "Refunded" },
  { key: "revoked", label: "Revoked" },
];

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  paid: "success",
  pending: "warning",
  failed: "error",
  refunded: "error",
  cancelled: "error",
  revoked: "error",
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function AdminOrdersPage() {
  const [tab, setTab] = useState("all");
  const [rows, setRows] = useState<AdminOrder[] | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    setRows(null);
    getAdminOrders(tab).then(setRows).catch(() => setRows([]));
  }, [tab]);

  async function onAction(id: string, action: "restore" | "revoke" | "refund") {
    setBusyId(id);
    try {
      const updated = await setOrderStatus(id, action);
      setRows((list) => list?.map((r) => (r.id === id ? updated : r)) ?? null);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Orders</h1>
          <p className={styles.sub}>Purchases across the marketplace and their payment state.</p>
        </div>
      </header>

      <div className={styles.tabs} role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            className={`${styles.tab} ${tab === t.key ? styles.tabActive : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>License Key</th>
              <th>Product</th>
              <th>Customer</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Requested</th>
              <th>Paid</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td className={styles.mono}>{row.license_key}</td>
                <td>
                  <strong>{row.product_name}</strong>
                </td>
                <td className={styles.muted}>{row.user_email}</td>
                <td>{formatPrice(row.amount, row.currency)}</td>
                <td>
                  <Pill tone={STATUS_TONE[row.payment_status] ?? "neutral"}>{row.payment_status}</Pill>
                </td>
                <td className={styles.muted}>{formatDate(row.requested_at)}</td>
                <td className={styles.muted}>{formatDate(row.paid_at)}</td>
                <td>
                  <div className={styles.actionRow}>
                    {row.payment_status !== "paid" && (
                      <button
                        className={styles.actionBtn}
                        disabled={busyId === row.id}
                        onClick={() => onAction(row.id, "restore")}
                      >
                        Mark Paid
                      </button>
                    )}
                    {row.payment_status === "paid" && (
                      <button
                        className={styles.actionBtn}
                        disabled={busyId === row.id}
                        onClick={() => onAction(row.id, "refund")}
                      >
                        Refund
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {rows === null && <p className={styles.state}>Loading orders…</p>}
        {rows?.length === 0 && (
          <p className={styles.state}>
            No orders yet — orders appear here once checkout is wired to Stripe/PayPal.
          </p>
        )}
      </div>

      {rows && rows.length > 0 && (
        <p className={styles.count}>
          Showing {rows.length} {rows.length === 1 ? "order" : "orders"}
        </p>
      )}
    </div>
  );
}
