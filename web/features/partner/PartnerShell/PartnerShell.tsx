import type { ReactNode } from "react";

import { UserMenu } from "@/components/UserMenu/UserMenu";
import { PartnerSidebar } from "@/features/partner/PartnerShell/PartnerSidebar";
import type { User } from "@/lib/types";

import styles from "./PartnerShell.module.css";

export function PartnerShell({ user, children }: { user: User; children: ReactNode }) {
  const approved = user.partner?.status === "approved";
  return (
    <div className={styles.shell}>
      <PartnerSidebar approved={approved} />
      <div className={styles.body}>
        <header className={styles.topbar}>
          <div>
            <p className={styles.partnerName}>{user.partner?.name}</p>
          </div>
          <UserMenu user={user} roleLabel="Partner" />
        </header>
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
