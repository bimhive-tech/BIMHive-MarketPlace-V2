import { DownloadsList } from "@/features/account/DownloadsList/DownloadsList";

import styles from "../section.module.css";

export default function DownloadsPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>Downloads</h1>
      <p className={styles.sub}>Purchased products and their files, by version.</p>
      <DownloadsList />
    </div>
  );
}
