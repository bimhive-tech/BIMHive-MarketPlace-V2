"use client";

import { Button } from "@/components/Button/Button";
import { SidebarNav, type SidebarNavGroup } from "@/components/SidebarNav/SidebarNav";

import styles from "./AccountShell.module.css";

const GROUPS: SidebarNavGroup[] = [
  {
    heading: "Account",
    items: [
      { label: "Overview", href: "/account", icon: "grid", ready: true },
      { label: "Licenses", href: "/account/licenses", icon: "library", ready: true },
      { label: "Subscriptions", href: "/account/subscriptions", icon: "refresh", ready: true },
      { label: "Orders & Invoices", href: "/account/orders", icon: "document", ready: true },
      { label: "Payment Methods", href: "/account/payment-methods", icon: "lock", ready: true },
      { label: "Profile", href: "/account/profile", icon: "users", ready: true },
      { label: "My Reviews", href: "/account/reviews", icon: "star", ready: true },
      { label: "Security", href: "/account/security", icon: "shield", ready: true },
      { label: "Notifications", href: "/account/notifications", icon: "bell", ready: true },
    ],
  },
  {
    heading: "Support",
    items: [
      { label: "Support Tickets", href: "/account/support", icon: "help", ready: true },
      { label: "Downloads", href: "/account/downloads", icon: "download", ready: true },
    ],
  },
];

export function AccountSidebar() {
  return (
    <aside className={styles.sidebar}>
      <SidebarNav groups={GROUPS} rootPath="/account" />

      <div className={styles.helpCard}>
        <h3 className={styles.helpTitle}>Need help?</h3>
        <p className={styles.helpText}>Our support team is here to help with any questions or issues.</p>
        <Button href="/support" variant="secondary" fullWidth>
          Contact Support
        </Button>
      </div>
    </aside>
  );
}
