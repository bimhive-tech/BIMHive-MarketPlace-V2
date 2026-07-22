import { SubscriptionsList } from "@/features/account/SubscriptionsList/SubscriptionsList";

import styles from "../section.module.css";

export default function SubscriptionsPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>Subscriptions</h1>
      <p className={styles.sub}>Your monthly and yearly plans, with renewal dates and status.</p>
      <SubscriptionsList />
    </div>
  );
}
