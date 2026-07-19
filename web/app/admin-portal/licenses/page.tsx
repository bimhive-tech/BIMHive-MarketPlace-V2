"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import {
  extendLicense,
  getAdminLicenses,
  restoreLicense,
  revokeLicense,
  type AdminLicense,
} from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  active: "success",
  paid: "success",
  expired: "warning",
  blocked: "error",
  cancelled: "error",
};

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function AdminLicensesPage() {
  const [rows, setRows] = useState<AdminLicense[] | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [busyId, setBusyId] = useState<string | null>(null);

  function load() {
    setRows(null);
    getAdminLicenses({ search, status }).then(setRows).catch(() => setRows([]));
  }

  useEffect(() => {
    const timer = setTimeout(load, 250); // debounce search
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, status]);

  async function onRevoke(id: string) {
    setBusyId(id);
    try {
      const updated = await revokeLicense(id);
      setRows((list) => list?.map((r) => (r.id === id ? updated : r)) ?? null);
    } finally {
      setBusyId(null);
    }
  }

  async function onRestore(id: string) {
    setBusyId(id);
    try {
      const updated = await restoreLicense(id);
      setRows((list) => list?.map((r) => (r.id === id ? updated : r)) ?? null);
    } finally {
      setBusyId(null);
    }
  }

  async function onExtend(id: string) {
    const days = window.prompt("Extend how many days?", "30");
    if (!days) return;
    setBusyId(id);
    try {
      const updated = await extendLicense(id, Number(days));
      setRows((list) => list?.map((r) => (r.id === id ? updated : r)) ?? null);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Licenses</h1>
          <p className={styles.sub}>
            Look up an activation, see its fingerprint and trial state, and revoke, restore, or
            extend it.
          </p>
        </div>
      </header>

      <div className={styles.toolbar}>
        <input
          className={styles.searchInput}
          placeholder="Search by product, email, or license key…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className={styles.select} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="active">Active</option>
          <option value="paid">Paid</option>
          <option value="expired">Expired</option>
          <option value="blocked">Blocked</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Product</th>
              <th>User</th>
              <th>Fingerprint</th>
              <th>Seats</th>
              <th>Status</th>
              <th>Started</th>
              <th>Expires</th>
              <th>Installs</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.product_name}</strong>
                  <div className={`${styles.muted} ${styles.mono}`}>{row.product_code}</div>
                </td>
                <td className={styles.muted}>{row.user_email || "—"}</td>
                <td className={styles.mono}>{row.fingerprint_preview}</td>
                <td className={styles.muted}>{row.seats}</td>
                <td>
                  <Pill tone={STATUS_TONE[row.status] ?? "neutral"}>{row.status}</Pill>
                </td>
                <td className={styles.muted}>{formatDate(row.started_at)}</td>
                <td className={styles.muted}>{formatDate(row.expires_at)}</td>
                <td className={styles.muted}>{row.install_count}</td>
                <td>
                  <div className={styles.actionRow}>
                    {row.status === "blocked" || row.status === "expired" ? (
                      <button
                        className={styles.actionBtn}
                        disabled={busyId === row.id}
                        onClick={() => onRestore(row.id)}
                      >
                        Restore
                      </button>
                    ) : (
                      <button
                        className={styles.actionBtn}
                        disabled={busyId === row.id}
                        onClick={() => onRevoke(row.id)}
                      >
                        Revoke
                      </button>
                    )}
                    <button
                      className={styles.iconBtn}
                      aria-label="Extend"
                      disabled={busyId === row.id}
                      onClick={() => onExtend(row.id)}
                    >
                      <Icon name="refresh" size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {rows === null && <p className={styles.state}>Loading licenses…</p>}
        {rows?.length === 0 && <p className={styles.state}>No licenses match this filter.</p>}
      </div>

      {rows && rows.length > 0 && (
        <p className={styles.count}>
          Showing {rows.length} {rows.length === 1 ? "license" : "licenses"}
        </p>
      )}
    </div>
  );
}
