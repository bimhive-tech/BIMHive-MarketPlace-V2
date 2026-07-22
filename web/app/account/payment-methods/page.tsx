import { PaymentMethodsList } from "@/features/account/PaymentMethodsList/PaymentMethodsList";

import styles from "../section.module.css";

export default function PaymentMethodsPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>Payment Methods</h1>
      <p className={styles.sub}>Cards you&apos;ve used to pay on BIMHIVE.</p>
      <PaymentMethodsList />
    </div>
  );
}
