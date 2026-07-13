import type { ReactNode } from "react";

import { AccountSidebar } from "@/features/account/AccountShell/AccountSidebar";

import styles from "./AccountShell.module.css";

export function AccountShell({ children }: { children: ReactNode }) {
  return (
    <div className={`container ${styles.shell}`}>
      <AccountSidebar />
      <div className={styles.content}>{children}</div>
    </div>
  );
}
