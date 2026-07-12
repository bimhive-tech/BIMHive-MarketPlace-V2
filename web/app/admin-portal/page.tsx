"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon, type IconName } from "@/components/Icon/Icon";
import { getAdminStats, type AdminStats } from "@/lib/adminApi";

import styles from "./dashboard.module.css";

const STAT_CARDS: { key: keyof AdminStats; label: string; icon: IconName; tone: string }[] = [
  { key: "total", label: "Total Products", icon: "grid", tone: "gold" },
  { key: "published", label: "Published", icon: "check-circle", tone: "success" },
  { key: "pending", label: "Pending Review", icon: "bell", tone: "warning" },
  { key: "draft", label: "Drafts", icon: "document", tone: "neutral" },
  { key: "rejected", label: "Rejected", icon: "lock", tone: "error" },
];

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getAdminStats().then(setStats).catch(() => setError(true));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Dashboard</h1>
          <p className={styles.sub}>Overview of your marketplace catalog.</p>
        </div>
        <Link href="/admin-portal/products/new" className={styles.primaryBtn}>
          <Icon name="arrow-right" size={16} />
          Add New Product
        </Link>
      </header>

      {error && <p className={styles.error}>Could not load stats. Check you are signed in as staff.</p>}

      <div className={styles.statGrid}>
        {STAT_CARDS.map((card) => (
          <div key={card.key} className={styles.statCard}>
            <span className={`${styles.statIcon} ${styles[card.tone]}`}>
              <Icon name={card.icon} size={20} />
            </span>
            <span className={styles.statValue}>{stats ? (stats[card.key] as number) : "—"}</span>
            <span className={styles.statLabel}>{card.label}</span>
          </div>
        ))}
      </div>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2 className={styles.panelTitle}>Top Products by Downloads</h2>
          <Link href="/admin-portal/products" className={styles.link}>
            View all products <Icon name="arrow-right" size={14} />
          </Link>
        </div>
        <ol className={styles.topList}>
          {stats?.top_products.map((p, i) => (
            <li key={p.slug} className={styles.topRow}>
              <span className={styles.rank}>{i + 1}</span>
              <Link href={`/products/${p.slug}`} className={styles.topName}>
                {p.name}
              </Link>
              <span className={styles.topCount}>{p.download_count.toLocaleString()}+ downloads</span>
            </li>
          ))}
          {!stats && <li className={styles.loading}>Loading…</li>}
        </ol>
      </section>
    </div>
  );
}
