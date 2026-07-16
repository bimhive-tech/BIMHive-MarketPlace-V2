"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon, type IconName } from "@/components/Icon/Icon";

import styles from "./SidebarNav.module.css";

export interface SidebarNavItem {
  label: string;
  href: string;
  icon: IconName;
  /** false → shown but not yet built (disabled, no dead link, "soon" badge) */
  ready?: boolean;
}

export interface SidebarNavGroup {
  heading: string;
  items: SidebarNavItem[];
}

interface SidebarNavProps {
  groups: SidebarNavGroup[];
  /** The area's own landing route (e.g. "/account", "/admin-portal") — only this
   * item requires an exact pathname match to be "active"; every other item is a
   * prefix match. Without this, the landing link would show active on every
   * subpage too, since its href is a prefix of all of them. */
  rootPath: string;
  /** Extra class on the outer <nav> — e.g. a shell that pins something below
   * the nav needs it to grow (flex: 1) to push that element to the bottom. */
  className?: string;
}

/** Shared nav-groups renderer for the dashboard-style areas (account, admin
 * portal, partner portal) — each area still owns its own GROUPS data and outer
 * shell chrome, this only renders the repeated group/item/active/disabled
 * structure that was previously copy-pasted per area. */
export function SidebarNav({ groups, rootPath, className = "" }: SidebarNavProps) {
  const pathname = usePathname();

  return (
    <nav className={`${styles.nav} ${className}`}>
      {groups.map((group) => (
        <div key={group.heading} className={styles.group}>
          <p className={styles.groupHeading}>{group.heading}</p>
          {group.items.map((item) => {
            const active = item.href === rootPath ? pathname === rootPath : pathname?.startsWith(item.href);
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
  );
}
