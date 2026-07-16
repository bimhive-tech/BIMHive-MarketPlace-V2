"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon, type IconName } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { formatPrice } from "@/config/site";
import { getAdminProducts, type AdminProductRow } from "@/lib/adminApi";
import { getPartnerSales, type PartnerSalesSummary } from "@/lib/partnerApi";

import styles from "./dashboard.module.css";

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  published: "success",
  pending: "warning",
  rejected: "error",
  draft: "neutral",
};

const STAT_CARDS: { status: string; label: string; icon: IconName; tone: string }[] = [
  { status: "published", label: "Published", icon: "check-circle", tone: "success" },
  { status: "pending", label: "Pending Review", icon: "bell", tone: "warning" },
  { status: "draft", label: "Drafts", icon: "document", tone: "gold" },
  { status: "rejected", label: "Rejected", icon: "lock", tone: "error" },
];

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function PartnerDashboard() {
  const [products, setProducts] = useState<AdminProductRow[] | null>(null);
  const [sales, setSales] = useState<PartnerSalesSummary | null>(null);

  useEffect(() => {
    // asPartner=true scopes to the caller's own partner even when they're
    // also staff (see catalog.admin_api._effective_partner_id).
    getAdminProducts("all", true).then(setProducts).catch(() => setProducts([]));
    getPartnerSales()
      .then(setSales)
      .catch(() => setSales({ total_revenue: "0", order_count: 0, orders: [] }));
  }, []);

  const counts = STAT_CARDS.reduce<Record<string, number>>((acc, card) => {
    acc[card.status] = products?.filter((p) => p.status === card.status).length ?? 0;
    return acc;
  }, {});

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Dashboard</h1>
          <p className={styles.sub}>Overview of the products you sell on BIMHIVE.</p>
        </div>
        <Link href="/partner-portal/products/new" className={styles.primaryBtn}>
          <Icon name="arrow-right" size={16} />
          Add New Product
        </Link>
      </header>

      <div className={styles.statGrid}>
        <div className={styles.statCard}>
          <span className={`${styles.statIcon} ${styles.gold}`}>
            <Icon name="wallet" size={20} />
          </span>
          <span className={styles.statValue}>{sales ? formatPrice(sales.total_revenue) : "—"}</span>
          <span className={styles.statLabel}>Total Revenue</span>
        </div>
        {STAT_CARDS.map((card) => (
          <div key={card.status} className={styles.statCard}>
            <span className={`${styles.statIcon} ${styles[card.tone]}`}>
              <Icon name={card.icon} size={20} />
            </span>
            <span className={styles.statValue}>{products ? counts[card.status] : "—"}</span>
            <span className={styles.statLabel}>{card.label}</span>
          </div>
        ))}
      </div>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Recent Sales</h2>
          <Link href="/partner-portal/sales" className={styles.link}>
            View all <Icon name="arrow-right" size={14} />
          </Link>
        </div>
        <ol className={styles.topList}>
          {sales?.orders.slice(0, 5).map((sale) => (
            <li key={sale.id} className={styles.topRow}>
              <span className={styles.topName}>{sale.product_name}</span>
              <Pill tone={sale.payment_status === "paid" ? "success" : "neutral"}>{sale.payment_status}</Pill>
              <span>{formatPrice(sale.amount, sale.currency)}</span>
            </li>
          ))}
          {sales?.orders.length === 0 && <li className={styles.empty}>No sales yet.</li>}
          {!sales && <li className={styles.loading}>Loading…</li>}
        </ol>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Recent Products</h2>
          <Link href="/partner-portal/products" className={styles.link}>
            View all <Icon name="arrow-right" size={14} />
          </Link>
        </div>
        <ol className={styles.topList}>
          {products?.slice(0, 5).map((p) => (
            <li key={p.id} className={styles.topRow}>
              <Link href={`/partner-portal/products/${p.id}/edit`} className={styles.topName}>
                {p.name}
              </Link>
              <Pill tone={STATUS_TONE[p.status] ?? "neutral"}>{p.status}</Pill>
              <span>{formatDate(p.updated_at)}</span>
            </li>
          ))}
          {products?.length === 0 && (
            <li className={styles.empty}>No products yet — add your first one to get started.</li>
          )}
          {!products && <li className={styles.loading}>Loading…</li>}
        </ol>
      </section>
    </div>
  );
}
