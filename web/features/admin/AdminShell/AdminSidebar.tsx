"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon, type IconName } from "@/components/Icon/Icon";
import { Logo } from "@/components/Logo/Logo";

import styles from "./AdminShell.module.css";

interface NavItem {
  label: string;
  href: string;
  icon: IconName;
  ready?: boolean; // false → shown but not yet built (disabled, no dead link)
}

interface NavGroup {
  heading: string;
  items: NavItem[];
}

const GROUPS: NavGroup[] = [
  {
    heading: "Overview",
    items: [
      { label: "Dashboard", href: "/admin-portal", icon: "grid", ready: true },
      { label: "Analytics", href: "/admin-portal/analytics", icon: "chart" },
      { label: "Orders", href: "/admin-portal/orders", icon: "document" },
      { label: "Customers", href: "/admin-portal/customers", icon: "users" },
      { label: "Reviews", href: "/admin-portal/reviews", icon: "star" },
    ],
  },
  {
    heading: "Products & Content",
    items: [
      { label: "Products", href: "/admin-portal/products", icon: "puzzle", ready: true },
      { label: "Collections", href: "/admin-portal/collections", icon: "layers" },
      { label: "Categories", href: "/admin-portal/categories", icon: "grid" },
      { label: "Tags", href: "/admin-portal/tags", icon: "hash" },
      { label: "Partners", href: "/admin-portal/partners", icon: "library" },
    ],
  },
  {
    heading: "Support",
    items: [
      { label: "Support Tickets", href: "/admin-portal/tickets", icon: "help" },
      { label: "Knowledge Base", href: "/admin-portal/kb", icon: "document" },
    ],
  },
  {
    heading: "Settings",
    items: [
      { label: "General", href: "/admin-portal/settings", icon: "wrench" },
      { label: "Payments", href: "/admin-portal/settings/payments", icon: "shield" },
      { label: "Users", href: "/admin-portal/settings/users", icon: "users" },
      { label: "Roles & Permissions", href: "/admin-portal/settings/roles", icon: "lock" },
    ],
  },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarBrand}>
        <Logo />
      </div>
      <nav className={styles.nav}>
        {GROUPS.map((group) => (
          <div key={group.heading} className={styles.group}>
            <p className={styles.groupHeading}>{group.heading}</p>
            {group.items.map((item) => {
              const active =
                item.href === "/admin-portal"
                  ? pathname === "/admin-portal"
                  : pathname?.startsWith(item.href);
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
      <Link href="/" className={styles.viewSite}>
        <Icon name="arrow-right" size={16} />
        View Marketplace
      </Link>
    </aside>
  );
}
