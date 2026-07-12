"use client";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { RequireAuth } from "@/features/auth/RequireAuth/RequireAuth";

import styles from "../section.module.css";

export default function LicensesPage() {
  return (
    <RequireAuth>
      {() => (
        <div className={`container ${styles.section}`}>
          <h1 className={styles.title}>Licenses</h1>
          <p className={styles.sub}>Manage your active products, renew licenses, and access downloads.</p>
          <EmptyState
            icon="library"
            title="No licenses yet"
            text="Your license keys, seats, and renewal dates will appear here after your first purchase."
            actionLabel="Browse the marketplace"
            actionHref="/catalog"
          />
        </div>
      )}
    </RequireAuth>
  );
}
