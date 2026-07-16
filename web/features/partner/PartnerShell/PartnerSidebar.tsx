"use client";

import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { Logo } from "@/components/Logo/Logo";
import { SidebarNav, type SidebarNavGroup } from "@/components/SidebarNav/SidebarNav";

import styles from "./PartnerShell.module.css";

/** Dashboard/My Products/Sales all depend on real partner-portal access, which
 * a pending/rejected application doesn't have yet (see catalog.permissions.
 * IsStaffOrPartner/IsApprovedPartner) — hiding them avoids linking into pages
 * that would just 403. Partner Profile always shows, since it's the one page
 * reachable regardless of status (see partner-portal/layout.tsx). */
function groupsFor(approved: boolean): SidebarNavGroup[] {
  const catalogAndSales: SidebarNavGroup[] = approved
    ? [
        {
          heading: "Overview",
          items: [{ label: "Dashboard", href: "/partner-portal", icon: "grid", ready: true }],
        },
        {
          heading: "Catalog",
          items: [
            { label: "My Products", href: "/partner-portal/products", icon: "puzzle", ready: true },
            { label: "Sales", href: "/partner-portal/sales", icon: "chart", ready: true },
          ],
        },
      ]
    : [];
  return [
    ...catalogAndSales,
    {
      heading: "Account",
      items: [{ label: "Partner Profile", href: "/partner-portal/profile", icon: "users", ready: true }],
    },
  ];
}

export function PartnerSidebar({ approved }: { approved: boolean }) {
  const GROUPS = groupsFor(approved);
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
