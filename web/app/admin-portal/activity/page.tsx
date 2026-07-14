"use client";

import { useEffect, useState } from "react";

import { Pill } from "@/components/Pill/Pill";
import { getAdminActivity, type AdminActivityEntry } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

// Mirrors activity.models.ActivityVerb on the backend — keep in sync.
const VERB_LABELS: Record<string, string> = {
  signed_in: "Signed in",
  signed_up: "Signed up",
  claimed_free_product: "Claimed a free product",
  downloaded_file: "Downloaded a file",
  posted_review: "Posted a review",
  product_created: "Created a product",
  product_updated: "Updated a product",
  product_deleted: "Deleted a product",
  license_revoked: "Revoked a license",
  license_restored: "Restored a license",
  license_extended: "Extended a license",
  order_status_changed: "Changed an order's status",
};

const VERB_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  claimed_free_product: "success",
  product_created: "success",
  license_restored: "success",
  license_extended: "success",
  product_deleted: "error",
  license_revoked: "error",
  order_status_changed: "warning",
};

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function AdminActivityPage() {
  const [rows, setRows] = useState<AdminActivityEntry[] | null>(null);
  const [actor, setActor] = useState("");
  const [verb, setVerb] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setRows(null);
      getAdminActivity({ actor, verb, date_from: dateFrom, date_to: dateTo })
        .then(setRows)
        .catch(() => setRows([]));
    }, 250); // debounce the actor search
    return () => clearTimeout(timer);
  }, [actor, verb, dateFrom, dateTo]);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Activity</h1>
          <p className={styles.sub}>Who did what, and when — sign-ins, purchases, downloads, and staff actions.</p>
        </div>
      </header>

      <div className={styles.toolbar}>
        <input
          className={styles.searchInput}
          placeholder="Search by who…"
          value={actor}
          onChange={(e) => setActor(e.target.value)}
        />
        <select className={styles.select} value={verb} onChange={(e) => setVerb(e.target.value)}>
          <option value="all">All actions</option>
          {Object.entries(VERB_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <input
          className={styles.select}
          type="date"
          aria-label="From date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />
        <input
          className={styles.select}
          type="date"
          aria-label="To date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>Action</th>
              <th>On</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td className={styles.muted}>{formatDateTime(row.created_at)}</td>
                <td>{row.actor_label || "—"}</td>
                <td>
                  <Pill tone={VERB_TONE[row.verb] ?? "neutral"}>{VERB_LABELS[row.verb] ?? row.verb}</Pill>
                </td>
                <td className={styles.muted}>{row.target_label || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {rows === null && <p className={styles.state}>Loading activity…</p>}
        {rows?.length === 0 && <p className={styles.state}>No activity matches this filter.</p>}
      </div>

      {rows && rows.length > 0 && (
        <p className={styles.count}>
          Showing {rows.length} {rows.length === 1 ? "entry" : "entries"}
          {rows.length === 300 && " (most recent 300 — narrow the filters for older activity)"}
        </p>
      )}
    </div>
  );
}
