"use client";

import { useEffect, useState } from "react";

import { AccountSummaryCard } from "@/features/account/AccountSummaryCard/AccountSummaryCard";
import { DeleteAccountCard } from "@/features/account/DeleteAccountCard/DeleteAccountCard";
import { EmailCard } from "@/features/account/EmailCard/EmailCard";
import { PasswordCard } from "@/features/account/PasswordCard/PasswordCard";
import { ProfileForm } from "@/features/account/ProfileForm/ProfileForm";
import { QuickLinksCard } from "@/features/account/QuickLinksCard/QuickLinksCard";
import { SellerTab } from "@/features/account/SellerTab/SellerTab";
import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./page.module.css";

type Tab = "info" | "preferences" | "connected" | "seller";

function sellerTabLabel(user: User): string {
  return user.partner ? "Partner" : "Become a Seller";
}

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("info");

  useEffect(() => {
    me().then(setUser);
  }, []);

  if (!user) return <div className={styles.loading}>Loading your profile…</div>;

  const TABS: { id: Tab; label: string }[] = [
    { id: "info", label: "Profile Information" },
    { id: "preferences", label: "Preferences" },
    { id: "connected", label: "Connected Accounts" },
    { id: "seller", label: sellerTabLabel(user) },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <h1 className={styles.title}>Profile</h1>
        <p className={styles.sub}>Manage your personal information and account preferences.</p>
      </header>

      <div className={styles.tabs} role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            className={`${styles.tab} ${tab === t.id ? styles.tabActive : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "info" && (
        <div className={styles.layout}>
          <div className={styles.main}>
            <ProfileForm user={user} onSaved={setUser} />
            <EmailCard user={user} onSaved={setUser} />
            <PasswordCard />
          </div>
          <div className={styles.side}>
            <AccountSummaryCard user={user} />
            <QuickLinksCard />
            <DeleteAccountCard />
          </div>
        </div>
      )}

      {tab === "preferences" && (
        <p className={styles.comingSoon}>Preferences (language, currency, email digests) are coming soon.</p>
      )}

      {tab === "connected" && (
        <p className={styles.comingSoon}>Connected accounts (Google, Microsoft SSO) are coming soon.</p>
      )}

      {tab === "seller" && <SellerTab user={user} />}
    </div>
  );
}
