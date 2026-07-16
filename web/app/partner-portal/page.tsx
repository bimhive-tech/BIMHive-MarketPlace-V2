"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon, type IconName } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { getAdminProducts, type AdminProductRow } from "@/lib/adminApi";

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

  useEffect(() => {
    // The backend auto-scopes this to the caller's own partner for a
    // non-staff user (see IsStaffOrPartner + AdminProductListCreateView).
    getAdminProducts("all").then(setProducts).catch(() => setProducts([]));
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
