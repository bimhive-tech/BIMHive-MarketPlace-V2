"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import {
  createAdminLicenseCode,
  getAdminLicenseCodes,
  getAdminLicenseOptions,
  revokeAdminLicenseCode,
  type AdminLicenseCode,
  type AdminLicenseProductOption,
} from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  unredeemed: "warning",
  redeemed: "success",
  revoked: "error",
};

const EMPTY_FORM = { product: "", seats: "1", duration_days: "365", lifetime: false, note: "" };

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function LicenseCodesPanel() {
  const [codes, setCodes] = useState<AdminLicenseCode[] | null>(null);
  const [products, setProducts] = useState<AdminLicenseProductOption[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  function load() {
    setCodes(null);
    getAdminLicenseCodes().then(setCodes).catch(() => setCodes([]));
  }

  useEffect(() => {
    load();
    getAdminLicenseOptions().then((o) => setProducts(o.products)).catch(() => setProducts([]));
  }, []);

  async function onGenerate() {
    setError("");
    if (!form.product) {
      setError("Choose which product this code is for.");
      return;
    }
    setSaving(true);
    try {
      await createAdminLicenseCode({
        product: form.product,
        seats: Number(form.seats) || 1,
        duration_days: form.lifetime ? null : Number(form.duration_days) || null,
        note: form.note.trim(),
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      load();
    } catch {
      setError("Could not generate a code — please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function onRevoke(id: string) {
    setBusyId(id);
    try {
      const updated = await revokeAdminLicenseCode(id);
      setCodes((list) => list?.map((c) => (c.id === id ? updated : c)) ?? null);
    } finally {
      setBusyId(null);
    }
  }

  async function onCopy(code: string, id: string) {
    await navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId((current) => (current === id ? null : current)), 1500);
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <p className={styles.sub}>
          Generate a single-use code for one product with its own seat count and duration — hand it to
          anyone, and whoever redeems it on their account gets a real license for exactly that long.
        </p>
        <button className={styles.primaryBtn} onClick={() => setShowForm((s) => !s)}>
          <Icon name="plus" size={16} />
          Generate Code
        </button>
      </div>

      {showForm && (
        <div className={styles.tableWrap}>
          <div className={styles.formPanel}>
            {error && <p className={styles.error}>{error}</p>}
            <div className={styles.formGrid}>
              <select
                className={styles.searchInput}
                value={form.product}
                onChange={(e) => setForm((f) => ({ ...f, product: e.target.value }))}
              >
                <option value="">Select a product</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code})
                  </option>
                ))}
              </select>
              <input
                className={styles.searchInput}
                type="number"
                min={1}
                placeholder="Seats"
                value={form.seats}
                onChange={(e) => setForm((f) => ({ ...f, seats: e.target.value }))}
              />
              <input
                className={styles.searchInput}
                type="number"
                min={1}
                placeholder="Duration (days)"
                disabled={form.lifetime}
                value={form.duration_days}
                onChange={(e) => setForm((f) => ({ ...f, duration_days: e.target.value }))}
              />
              <label className={styles.checkboxRow}>
                <input
                  type="checkbox"
                  checked={form.lifetime}
                  onChange={(e) => setForm((f) => ({ ...f, lifetime: e.target.checked }))}
                />
                Lifetime (never expires)
              </label>
              <input
                className={styles.searchInput}
                placeholder="Note (e.g. who this is for) — staff-only"
                value={form.note}
                onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
              />
            </div>
            <div className={styles.formActions}>
              <button className={styles.primaryBtn} disabled={saving} onClick={onGenerate}>
                {saving ? "Generating…" : "Generate"}
              </button>
              <button className={styles.actionBtn} onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Code</th>
              <th>Product</th>
              <th>Seats</th>
              <th>Duration</th>
              <th>Status</th>
              <th>Redeemed by</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {codes?.map((c) => (
              <tr key={c.id}>
                <td>
                  <span className={styles.mono}>{c.code}</span>
                  {c.note && <div className={styles.muted}>{c.note}</div>}
                </td>
                <td>
                  <strong>{c.product_name}</strong>
                  <div className={`${styles.muted} ${styles.mono}`}>{c.product_code}</div>
                </td>
                <td className={styles.muted}>{c.seats}</td>
                <td className={styles.muted}>{c.duration_days ? `${c.duration_days} days` : "Lifetime"}</td>
                <td>
                  <Pill tone={STATUS_TONE[c.status] ?? "neutral"}>{c.status}</Pill>
                </td>
                <td className={styles.muted}>{c.redeemed_by_email || "—"}</td>
                <td className={styles.muted}>{formatDate(c.created_at)}</td>
                <td>
                  <div className={styles.actionRow}>
                    <button className={styles.iconBtn} aria-label="Copy code" onClick={() => onCopy(c.code, c.id)}>
                      <Icon name={copiedId === c.id ? "check" : "copy"} size={16} />
                    </button>
                    {c.status === "unredeemed" && (
                      <button
                        className={styles.actionBtn}
                        disabled={busyId === c.id}
                        onClick={() => onRevoke(c.id)}
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {codes === null && <p className={styles.state}>Loading license codes…</p>}
        {codes?.length === 0 && <p className={styles.state}>No license codes generated yet.</p>}
      </div>

      {codes && codes.length > 0 && (
        <p className={styles.count}>
          Showing {codes.length} {codes.length === 1 ? "code" : "codes"}
        </p>
      )}
    </div>
  );
}
