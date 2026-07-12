"use client";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { RequireAuth } from "@/features/auth/RequireAuth/RequireAuth";

import styles from "../section.module.css";

export default function DownloadsPage() {
  return (
    <RequireAuth>
      {() => (
        <div className={`container ${styles.section}`}>
          <h1 className={styles.title}>Downloads</h1>
          <p className={styles.sub}>Purchased products and their files, by version.</p>
          <EmptyState
            icon="download"
            title="Nothing to download yet"
            text="Files for products you own will appear here, served over secure, expiring links."
            actionLabel="Browse the marketplace"
            actionHref="/catalog"
          />
        </div>
      )}
    </RequireAuth>
  );
}
