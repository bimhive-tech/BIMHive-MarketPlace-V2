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
      { label: "Orders", href: "/admin-portal/orders", icon: "document", ready: true },
      { label: "Customers", href: "/admin-portal/customers", icon: "users", ready: true },
      { label: "Reviews", href: "/admin-portal/reviews", icon: "star", ready: true },
      { label: "Licenses", href: "/admin-portal/licenses", icon: "lock", ready: true },
    ],
  },
  {
    heading: "Products & Content",
    items: [
      { label: "Products", href: "/admin-portal/products", icon: "puzzle", ready: true },
      { label: "Collections", href: "/admin-portal/collections", icon: "layers", ready: true },
      { label: "Categories", href: "/admin-portal/categories", icon: "grid", ready: true },
      { label: "Tags", href: "/admin-portal/tags", icon: "hash", ready: true },
      { label: "Partners", href: "/admin-portal/partners", icon: "library", ready: true },
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
      { label: "General", href: "/admin-portal/settings", icon: "wrench", ready: true },
      { label: "Payments", href: "/admin-portal/settings", icon: "shield", ready: true },
      { label: "Users", href: "/admin-portal/settings/users", icon: "users", ready: true },
      { label: "Roles & Permissions", href: "/admin-portal/settings/roles", icon: "lock", ready: true },
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
