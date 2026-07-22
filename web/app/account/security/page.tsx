import { ActiveSessions } from "@/features/account/ActiveSessions/ActiveSessions";
import { PasswordCard } from "@/features/account/PasswordCard/PasswordCard";

import sectionStyles from "../section.module.css";
import styles from "./page.module.css";

export default function SecurityPage() {
  return (
    <div className={sectionStyles.section}>
      <h1 className={sectionStyles.title}>Security</h1>
      <p className={sectionStyles.sub}>Manage your password and see which devices are signed in.</p>
      <div className={styles.cards}>
        <PasswordCard />
        <ActiveSessions />
      </div>
    </div>
  );
}
