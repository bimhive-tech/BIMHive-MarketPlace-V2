import { MembershipPanel } from "@/features/account/MembershipPanel/MembershipPanel";

import styles from "../section.module.css";

export default function AccountMembershipPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>All-Access</h1>
      <p className={styles.sub}>
        Your membership, your universal license key, and everything that key unlocks.
      </p>
      <MembershipPanel />
    </div>
  );
}
