"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon, type IconName } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./page.module.css";

const QUICK_LINKS: { icon: IconName; title: string; text: string; href: string }[] = [
  { icon: "download", title: "Downloads", text: "Access your purchased files", href: "/account/downloads" },
  { icon: "library", title: "Licenses", text: "View and manage license keys", href: "/account/licenses" },
  { icon: "document", title: "Orders & Invoices", text: "Purchase history and receipts", href: "/account/orders" },
  { icon: "users", title: "Profile", text: "Update your personal details", href: "/account/profile" },
];

export default function AccountOverviewPage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    me().then(setUser);
  }, []);

  if (!user) return <div className={styles.loading}>Loading your account…</div>;

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Welcome back, {user.first_name || user.full_name}</h1>
          <p className={styles.sub}>Manage your licenses, downloads, and account details.</p>
        </div>
        <Pill tone="success">Active</Pill>
      </header>

      <section className={styles.summary}>
        <div className={styles.summaryRow}>
          <Icon name="users" size={18} className={styles.summaryIcon} />
          <span className={styles.summaryLabel}>Email</span>
          <span className={styles.summaryValue}>{user.email}</span>
        </div>
        <div className={styles.summaryRow}>
          <Icon name="award" size={18} className={styles.summaryIcon} />
          <span className={styles.summaryLabel}>Account type</span>
          <span className={styles.summaryValue}>
            {user.profile?.account_type === "team" ? "Team" : "Individual"}
          </span>
        </div>
        {user.is_staff && (
          <div className={styles.summaryRow}>
            <Icon name="shield" size={18} className={styles.summaryIcon} />
            <span className={styles.summaryLabel}>Role</span>
            <span className={styles.summaryValue}>
              Administrator — <Link href="/admin-portal" className={styles.inlineLink}>open admin portal →</Link>
            </span>
          </div>
        )}
      </section>

      <div className={styles.quickGrid}>
        {QUICK_LINKS.map((q) => (
          <Link key={q.title} href={q.href} className={styles.quickCard}>
            <span className={styles.quickIcon}>
              <Icon name={q.icon} size={20} />
            </span>
            <span className={styles.quickText}>
              <span className={styles.quickTitle}>{q.title}</span>
              <span className={styles.quickSub}>{q.text}</span>
            </span>
            <Icon name="chevron-right" size={16} className={styles.quickArrow} />
          </Link>
        ))}
      </div>

      <section className={styles.empty}>
        <Icon name="library" size={28} className={styles.emptyIcon} />
        <h2 className={styles.emptyTitle}>No licenses yet</h2>
        <p className={styles.emptyText}>
          When you purchase a product, your licenses and downloads will appear here.
        </p>
        <Button href="/catalog" variant="secondary">
          Browse the marketplace
        </Button>
      </section>
    </div>
  );
}
