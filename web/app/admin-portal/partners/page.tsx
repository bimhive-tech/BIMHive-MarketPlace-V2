"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { partnersApi, type AdminPartner } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

type PartnerFormState = Omit<AdminPartner, "id" | "slug" | "product_count" | "owner_email">;

// Staff creating a partner directly (as opposed to a self-service seller
// application) is implicitly vetted — no separate review step for those.
const EMPTY: PartnerFormState = {
  name: "", tagline: "", bio: "", logo_url: "", website: "", is_verified: false,
  status: "approved", rejection_note: "",
};

const TABS = [
  { key: "all", label: "All" },
  { key: "pending", label: "Pending Review" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
];

const STATUS_TONE: Record<string, "success" | "warning" | "error"> = {
  approved: "success",
  pending: "warning",
  rejected: "error",
};

export default function AdminPartnersPage() {
  const [tab, setTab] = useState("all");
  const [rows, setRows] = useState<AdminPartner[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  function load() {
    partnersApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  const visibleRows = rows?.filter((row) => tab === "all" || row.status === tab);

  function startEdit(row: AdminPartner) {
    setEditingId(row.id);
    setForm({
      name: row.name, tagline: row.tagline, bio: row.bio, logo_url: row.logo_url,
      website: row.website, is_verified: row.is_verified,
      status: row.status, rejection_note: row.rejection_note,
    });
    setShowForm(true);
  }

  function startNew() {
    setEditingId(null);
    setForm(EMPTY);
    setShowForm(true);
  }

  async function onSave() {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      if (editingId) await partnersApi.update(editingId, form);
      else await partnersApi.create(form);
      setShowForm(false);
      load();
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm("Delete this partner? Products from them are not deleted.")) return;
    await partnersApi.remove(id);
    load();
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Partners</h1>
          <p className={styles.sub}>
            Sellers and publishers products are listed under. Seller applications submitted via
            "Become a Seller" land here as Pending Review.
          </p>
        </div>
        <button className={styles.primaryBtn} onClick={startNew}>
          <Icon name="plus" size={16} />
          Add Partner
        </button>
      </header>

      <div className={styles.tabs} role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            className={`${styles.tab} ${tab === t.key ? styles.tabActive : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {showForm && (
        <div className={styles.tableWrap}>
          <div className={styles.formPanel}>
            <div className={styles.formGrid}>
              <input
                className={styles.searchInput}
                placeholder="Name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
              <input
                className={styles.searchInput}
                placeholder="Tagline"
                value={form.tagline}
                onChange={(e) => setForm((f) => ({ ...f, tagline: e.target.value }))}
              />
              <input
                className={styles.searchInput}
                placeholder="Logo URL"
                value={form.logo_url}
                onChange={(e) => setForm((f) => ({ ...f, logo_url: e.target.value }))}
              />
              <input
                className={styles.searchInput}
                placeholder="Website"
                value={form.website}
                onChange={(e) => setForm((f) => ({ ...f, website: e.target.value }))}
              />
              <textarea
                className={styles.textarea}
                rows={3}
                placeholder="Bio"
                value={form.bio}
                onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
              />
            </div>
            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={form.is_verified}
                onChange={(e) => setForm((f) => ({ ...f, is_verified: e.target.checked }))}
              />
              Verified
            </label>

            {editingId && (
              <div className={styles.loginPanel}>
                <p className={styles.loginPanelTitle}>Seller Application</p>
                <div className={styles.formGrid}>
                  <select
                    className={styles.searchInput}
                    value={form.status}
                    onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as typeof f.status }))}
                  >
                    <option value="pending">Pending Review</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
                {form.status === "rejected" && (
                  <textarea
                    className={styles.textarea}
                    rows={2}
                    placeholder="Let the applicant know what to fix before reapplying."
                    value={form.rejection_note}
                    onChange={(e) => setForm((f) => ({ ...f, rejection_note: e.target.value }))}
                  />
                )}
              </div>
            )}

            <div className={styles.formActions}>
              <button className={styles.primaryBtn} disabled={saving} onClick={onSave}>
                {editingId ? "Save" : "Create"}
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
              <th>Name</th>
              <th>Applicant</th>
              <th>Status</th>
              <th>Verified</th>
              <th>Products</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visibleRows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.name}</strong>
                </td>
                <td className={styles.muted}>{row.owner_email || "—"}</td>
                <td>
                  <Pill tone={STATUS_TONE[row.status]}>{row.status}</Pill>
                </td>
                <td>{row.is_verified && <Pill tone="success">Verified</Pill>}</td>
                <td className={styles.muted}>{row.product_count}</td>
                <td>
                  <div className={styles.actionRow}>
                    <button className={styles.iconBtn} aria-label="Edit" onClick={() => startEdit(row)}>
                      <Icon name="edit" size={16} />
                    </button>
                    <button
                      className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                      aria-label="Delete"
                      onClick={() => onDelete(row.id)}
                    >
                      <Icon name="trash" size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows === null && <p className={styles.state}>Loading partners…</p>}
        {visibleRows?.length === 0 && <p className={styles.state}>No partners in this view.</p>}
      </div>
    </div>
  );
}
