import { OrdersList } from "@/features/account/OrdersList/OrdersList";

import styles from "../section.module.css";

export default function OrdersPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>Orders &amp; Invoices</h1>
      <p className={styles.sub}>Your purchase history and downloadable receipts.</p>
      <OrdersList />
    </div>
  );
}
