import { LicensesList } from "@/features/account/LicensesList/LicensesList";

import styles from "../section.module.css";

export default function LicensesPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>Licenses</h1>
      <p className={styles.sub}>Manage your active products, renew licenses, and access downloads.</p>
      <LicensesList />
    </div>
  );
}
