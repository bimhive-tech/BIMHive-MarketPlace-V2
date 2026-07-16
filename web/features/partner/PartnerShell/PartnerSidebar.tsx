"use client";

import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { Logo } from "@/components/Logo/Logo";
import { SidebarNav, type SidebarNavGroup } from "@/components/SidebarNav/SidebarNav";

import styles from "./PartnerShell.module.css";

const GROUPS: SidebarNavGroup[] = [
  {
    heading: "Overview",
    items: [{ label: "Dashboard", href: "/partner-portal", icon: "grid", ready: true }],
  },
  {
    heading: "Catalog",
    items: [{ label: "My Products", href: "/partner-portal/products", icon: "puzzle", ready: true }],
  },
  {
    heading: "Account",
    items: [{ label: "Partner Profile", href: "/partner-portal/profile", icon: "users", ready: true }],
  },
];

export function PartnerSidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.sidebarBrand}>
        <Logo />
      </div>
      <SidebarNav groups={GROUPS} rootPath="/partner-portal" className={styles.navFlex} />
      <Link href="/" className={styles.viewSite}>
        <Icon name="arrow-right" size={16} />
        View Marketplace
      </Link>
    </aside>
  );
}
