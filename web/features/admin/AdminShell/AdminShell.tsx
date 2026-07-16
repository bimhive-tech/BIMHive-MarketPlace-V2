import type { ReactNode } from "react";

import { Icon } from "@/components/Icon/Icon";
import { UserMenu } from "@/components/UserMenu/UserMenu";
import { AdminSidebar } from "@/features/admin/AdminShell/AdminSidebar";
import type { User } from "@/lib/types";

import styles from "./AdminShell.module.css";

export function AdminShell({ user, children }: { user: User; children: ReactNode }) {
  return (
    <div className={styles.shell}>
      <AdminSidebar />
      <div className={styles.body}>
        <header className={styles.topbar}>
          <div className={styles.search}>
            <Icon name="search" size={18} className={styles.searchIcon} />
            <input className={styles.searchInput} placeholder="Search products, orders, users..." aria-label="Admin search" />
          </div>
          <div className={styles.topActions}>
            <button className={styles.iconBtn} aria-label="Notifications">
              <Icon name="bell" size={20} />
            </button>
            <button className={styles.iconBtn} aria-label="Help">
              <Icon name="help" size={20} />
            </button>
            <UserMenu user={user} roleLabel="Administrator" />
          </div>
        </header>
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
