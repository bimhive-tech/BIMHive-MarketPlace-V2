import { NotificationsFeed } from "@/features/account/NotificationsFeed/NotificationsFeed";

import styles from "../section.module.css";

export default function NotificationsPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>Notifications</h1>
      <p className={styles.sub}>Recent activity on your account — sign-ins, purchases, downloads, and reviews.</p>
      <NotificationsFeed />
    </div>
  );
}
