"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/Button/Button";
import { Icon, type IconName } from "@/components/Icon/Icon";

import styles from "./AccountShell.module.css";

interface NavItem {
  label: string;
  href: string;
  icon: IconName;
  ready?: boolean;
}

interface NavGroup {
  heading: string;
  items: NavItem[];
}

const GROUPS: NavGroup[] = [
  {
    heading: "Account",
    items: [
      { label: "Overview", href: "/account", icon: "grid", ready: true },
      { label: "Licenses", href: "/account/licenses", icon: "library", ready: true },
      { label: "Subscriptions", href: "/account/subscriptions", icon: "refresh" },
      { label: "Orders & Invoices", href: "/account/orders", icon: "document", ready: true },
      { label: "Payment Methods", href: "/account/payment-methods", icon: "lock" },
      { label: "Profile", href: "/account/profile", icon: "users", ready: true },
      { label: "My Reviews", href: "/account/reviews", icon: "star", ready: true },
      { label: "Security", href: "/account/security", icon: "shield" },
      { label: "Notifications", href: "/account/notifications", icon: "bell" },
    ],
  },
  {
    heading: "Support",
    items: [
      { label: "Support Tickets", href: "/account/support", icon: "help" },
      { label: "Downloads", href: "/account/downloads", icon: "download", ready: true },
    ],
  },
];

export function AccountSidebar() {
  const pathname = usePathname();

  return (
    <aside className={styles.sidebar}>
      <nav className={styles.nav}>
        {GROUPS.map((group) => (
          <div key={group.heading} className={styles.group}>
            <p className={styles.groupHeading}>{group.heading}</p>
            {group.items.map((item) => {
              const active =
                item.href === "/account" ? pathname === "/account" : pathname?.startsWith(item.href);
              if (!item.ready) {
                return (
                  <span key={item.label} className={`${styles.item} ${styles.itemDisabled}`}>
                    <Icon name={item.icon} size={18} />
                    {item.label}
                    <span className={styles.soon}>soon</span>
                  </span>
                );
              }
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={`${styles.item} ${active ? styles.itemActive : ""}`}
                >
                  <Icon name={item.icon} size={18} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

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
