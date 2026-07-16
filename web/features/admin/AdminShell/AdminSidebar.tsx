"use client";

import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { Logo } from "@/components/Logo/Logo";
import { SidebarNav, type SidebarNavGroup } from "@/components/SidebarNav/SidebarNav";

import styles from "./AdminShell.module.css";

const GROUPS: SidebarNavGroup[] = [
  {
    heading: "Overview",
    items: [
      { label: "Dashboard", href: "/admin-portal", icon: "grid", ready: true },
      { label: "Activity", href: "/admin-portal/activity", icon: "eye", ready: true },
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
  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarBrand}>
        <Logo />
      </div>
      <SidebarNav groups={GROUPS} rootPath="/admin-portal" className={styles.navFlex} />
      <Link href="/" className={styles.viewSite}>
        <Icon name="arrow-right" size={16} />
        View Marketplace
      </Link>
    </aside>
  );
}
