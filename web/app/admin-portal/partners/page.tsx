"use client";

import { useEffect, useState } from "react";

import { useConfirm } from "@/components/ConfirmDialog/useConfirm";
import { Icon } from "@/components/Icon/Icon";
import { Modal } from "@/components/Modal/Modal";
import { Pill } from "@/components/Pill/Pill";
import {
  AdminCheckbox,
  AdminField,
  AdminFormGrid,
  AdminInput,
  AdminSelect,
  AdminTextarea,
} from "@/features/admin/AdminForm/AdminForm";
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
  const [error, setError] = useState("");
  const { confirm, dialog } = useConfirm();

  function load() {
    partnersApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  const visibleRows = rows?.filter((row) => tab === "all" || row.status === tab);

  function set<K extends keyof PartnerFormState>(key: K, value: PartnerFormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function startEdit(row: AdminPartner) {
    setEditingId(row.id);
    setForm({
      name: row.name, tagline: row.tagline, bio: row.bio, logo_url: row.logo_url,
      website: row.website, is_verified: row.is_verified,
      status: row.status, rejection_note: row.rejection_note,
    });
    setError("");
    setShowForm(true);
  }

  function startNew() {
    setEditingId(null);
    setForm(EMPTY);
    setError("");
    setShowForm(true);
  }

  async function onSave() {
    if (!form.name.trim()) return;
    setSaving(true);
    setError("");
    try {
      if (editingId) await partnersApi.update(editingId, form);
      else await partnersApi.create(form);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save this partner.");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(row: AdminPartner) {
    const confirmed = await confirm({
      title: `Delete ${row.name}?`,
      message: "Products from them are not deleted.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await partnersApi.remove(row.id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this partner.");
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Partners</h1>
          <p className={styles.sub}>
            Sellers and publishers products are listed under. Seller applications submitted via
            &quot;Become a Seller&quot; land here as Pending Review.
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

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editingId ? `Edit ${form.name || "partner"}` : "New partner"}
        description={
          editingId
            ? "Approving or rejecting the seller application is at the bottom."
            : "A partner you add here is approved straight away."
        }
        footer={
          <>
            <button className={styles.actionBtn} onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button className={styles.primaryBtn} disabled={saving || !form.name.trim()} onClick={onSave}>
              {saving ? "Saving…" : editingId ? "Save" : "Create"}
            </button>
          </>
        }
      >
        <AdminFormGrid>
          <AdminField label="Name">
            <AdminInput value={form.name} onChange={(e) => set("name", e.target.value)} />
          </AdminField>
          <AdminField label="Tagline" hint="Optional.">
            <AdminInput value={form.tagline} onChange={(e) => set("tagline", e.target.value)} />
          </AdminField>
          <AdminField label="Logo URL" hint="Optional.">
            <AdminInput type="url" value={form.logo_url} onChange={(e) => set("logo_url", e.target.value)} />
          </AdminField>
          <AdminField label="Website" hint="Optional.">
            <AdminInput type="url" value={form.website} onChange={(e) => set("website", e.target.value)} />
          </AdminField>
          <AdminField label="Bio" hint="Shown on their public seller page." wide>
            <AdminTextarea value={form.bio} onChange={(e) => set("bio", e.target.value)} />
          </AdminField>
          <AdminCheckbox
            label="Verified"
            hint="A badge customers see on their products."
            checked={form.is_verified}
            onChange={(v) => set("is_verified", v)}
          />

          {editingId && (
            <AdminField label="Seller application" hint="Approving gives them partner-portal access." wide>
              <AdminSelect
                value={form.status}
                onChange={(e) => set("status", e.target.value as PartnerFormState["status"])}
              >
                <option value="pending">Pending Review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </AdminSelect>
            </AdminField>
          )}
          {editingId && form.status === "rejected" && (
            <AdminField label="Rejection note" hint="Tell the applicant what to fix before re-applying." wide>
              <AdminTextarea
                rows={2}
                value={form.rejection_note}
                onChange={(e) => set("rejection_note", e.target.value)}
              />
            </AdminField>
          )}
        </AdminFormGrid>
      </Modal>

      {error && <p className={styles.error}>{error}</p>}

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
                      onClick={() => onDelete(row)}
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

      {dialog}
    </div>
  );
}
