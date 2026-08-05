"use client";

import { useEffect, useState } from "react";

import { Pill } from "@/components/Pill/Pill";
import {
  getAdminMemberships,
  reinstateMembership,
  revokeMembership,
  type AdminMembership,
} from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  active: "success",
  pending: "warning",
  expired: "error",
  cancelled: "neutral",
  refunded: "neutral",
  revoked: "error",
};

export default function AdminMembershipsPage() {
  const [rows, setRows] = useState<AdminMembership[] | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");

  function load() {
    getAdminMemberships().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  async function onRevoke(row: AdminMembership) {
    if (
      !window.confirm(
        `Revoke ${row.user_email}'s ${row.plan_name} membership? Its universal key will stop activating all ${row.granted_count} product(s) it opened.`,
      )
    )
      return;
    setError("");
    setBusyId(row.id);
    try {
      await revokeMembership(row.id, "revoked");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not revoke this membership.");
    } finally {
      setBusyId(null);
    }
  }

  async function onReinstate(row: AdminMembership) {
    setError("");
    setBusyId(row.id);
    try {
      await reinstateMembership(row.id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reinstate this membership.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Memberships</h1>
          <p className={styles.sub}>
            One row per customer&apos;s All-Access subscription. Revoking ends the membership and pulls
            every license its universal key granted, in one action.
          </p>
        </div>
      </header>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Customer</th>
              <th>Plan</th>
              <th>Status</th>
              <th>Key</th>
              <th>Activated on</th>
              <th>Expires</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>{row.user_email}</td>
                <td className={styles.muted}>{row.plan_name}</td>
                <td>
                  <Pill tone={STATUS_TONE[row.display_status] ?? "neutral"}>{row.display_status}</Pill>
                </td>
                <td className={styles.mono}>{row.license_key}</td>
                <td className={styles.muted}>{row.granted_count} product(s)</td>
                <td className={styles.muted}>
                  {row.expires_at ? new Date(row.expires_at).toLocaleDateString() : "—"}
                </td>
                <td>
                  <div className={styles.actionRow}>
                    {row.display_status === "active" ? (
                      <button
                        className={styles.actionBtn}
                        disabled={busyId === row.id}
                        onClick={() => onRevoke(row)}
                      >
                        Revoke
                      </button>
                    ) : (
                      <button
                        className={styles.actionBtn}
                        disabled={busyId === row.id}
                        onClick={() => onReinstate(row)}
                      >
                        Reinstate
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows === null && <p className={styles.state}>Loading memberships…</p>}
        {rows?.length === 0 && <p className={styles.state}>No memberships yet.</p>}
      </div>
    </div>
  );
}
