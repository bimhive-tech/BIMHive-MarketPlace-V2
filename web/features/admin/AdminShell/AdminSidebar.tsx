"use client";

import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { Logo } from "@/components/Logo/Logo";
import { SidebarNav, type SidebarNavGroup } from "@/components/SidebarNav/SidebarNav";
import type { User } from "@/lib/types";

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
      { label: "Memberships", href: "/admin-portal/memberships", icon: "wallet", ready: true },
    ],
  },
  {
    heading: "Products & Content",
    items: [
      { label: "Products", href: "/admin-portal/products", icon: "puzzle", ready: true },
      { label: "Promotions", href: "/admin-portal/promotions", icon: "bolt", ready: true },
      { label: "Membership Plans", href: "/admin-portal/membership-plans", icon: "wallet", ready: true },
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

// Maps a real, backed sidebar item to the granular permission that gates it
// (see api/accounts/permissions.py::ADMIN_PERMISSIONS) — kept in sync by
// convention, same as ADMIN_PERMISSIONS itself mirrors the backend catalog.
// An item with no entry here (Analytics, Support Tickets, Knowledge Base —
// none has a backing admin API yet) is always shown; real enforcement is
// server-side regardless, this only avoids linking to a section the API
// would reject.
const ITEM_PERMISSION: Record<string, string> = {
  "/admin-portal": "dashboard.view",
  "/admin-portal/activity": "activity.view",
  "/admin-portal/orders": "orders.manage",
  "/admin-portal/customers": "customers.view",
  "/admin-portal/reviews": "reviews.moderate",
  "/admin-portal/licenses": "licenses.manage",
  "/admin-portal/memberships": "memberships.manage",
  "/admin-portal/products": "products.manage",
  "/admin-portal/promotions": "promotions.manage",
  "/admin-portal/membership-plans": "membership_plans.manage",
  "/admin-portal/categories": "categories.manage",
  "/admin-portal/tags": "tags.manage",
  "/admin-portal/partners": "partners.manage",
};

export function AdminSidebar({ user }: { user: User }) {
  const groups = GROUPS.map((group) => ({
    ...group,
    items:
      group.heading === "Settings"
        ? user.is_superuser
          ? group.items
          : []
        : group.items.filter((item) => {
            const required = ITEM_PERMISSION[item.href];
            return !required || user.is_superuser || user.permissions.includes(required);
          }),
  })).filter((group) => group.items.length > 0);

  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarBrand}>
        <Logo />
      </div>
      <SidebarNav groups={groups} rootPath="/admin-portal" className={styles.navFlex} />
      <Link href="/" className={styles.viewSite}>
        <Icon name="arrow-right" size={16} />
        View Marketplace
      </Link>
    </aside>
  );
}
