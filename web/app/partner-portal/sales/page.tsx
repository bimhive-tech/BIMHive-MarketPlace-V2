"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { formatPrice } from "@/config/site";
import { getPartnerSales, type PartnerSalesSummary } from "@/lib/partnerApi";

import styles from "./sales.module.css";

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  paid: "success",
  pending: "warning",
  failed: "error",
  refunded: "neutral",
  cancelled: "neutral",
  revoked: "error",
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function PartnerSalesPage() {
  const [sales, setSales] = useState<PartnerSalesSummary | null>(null);

  useEffect(() => {
    getPartnerSales()
      .then(setSales)
      .catch(() => setSales({ total_revenue: "0", order_count: 0, orders: [] }));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Sales</h1>
          <p className={styles.sub}>Every order placed for your products.</p>
        </div>
        <div className={styles.summary}>
          <span className={styles.summaryIcon}>
            <Icon name="wallet" size={20} />
          </span>
          <div>
            <span className={styles.summaryValue}>{sales ? formatPrice(sales.total_revenue) : "—"}</span>
            <span className={styles.summaryLabel}>
              Total revenue · {sales ? sales.order_count : "—"} orders
            </span>
          </div>
        </div>
      </header>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Product</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Requested</th>
              <th>Paid</th>
            </tr>
          </thead>
          <tbody>
            {sales?.orders.map((sale) => (
              <tr key={sale.id}>
                <td className={styles.product}>{sale.product_name}</td>
                <td className={styles.price}>{formatPrice(sale.amount, sale.currency)}</td>
                <td>
                  <Pill tone={STATUS_TONE[sale.payment_status] ?? "neutral"}>{sale.payment_status}</Pill>
                </td>
                <td className={styles.muted}>{formatDate(sale.requested_at)}</td>
                <td className={styles.muted}>{formatDate(sale.paid_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {sales === null && <p className={styles.state}>Loading sales…</p>}
        {sales?.orders.length === 0 && <p className={styles.state}>No sales yet.</p>}
      </div>
    </div>
  );
}
