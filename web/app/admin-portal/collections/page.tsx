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
  AdminTextarea,
} from "@/features/admin/AdminForm/AdminForm";
import { collectionsApi, type AdminCollection } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const EMPTY = { name: "", description: "", is_featured: false };

type CollectionForm = typeof EMPTY;

export default function AdminCollectionsPage() {
  const [rows, setRows] = useState<AdminCollection[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CollectionForm>(EMPTY);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { confirm, dialog } = useConfirm();

  function load() {
    collectionsApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  function set<K extends keyof CollectionForm>(key: K, value: CollectionForm[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function startEdit(row: AdminCollection) {
    setEditingId(row.id);
    setForm({ name: row.name, description: row.description, is_featured: row.is_featured });
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
      if (editingId) await collectionsApi.update(editingId, form);
      else await collectionsApi.create(form);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save this collection.");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(row: AdminCollection) {
    const confirmed = await confirm({
      title: `Delete ${row.name}?`,
      message: "Products in it are not deleted.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await collectionsApi.remove(row.id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this collection.");
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Collections</h1>
          <p className={styles.sub}>Curated product bundles shown on the storefront.</p>
        </div>
        <button className={styles.primaryBtn} onClick={startNew}>
          <Icon name="plus" size={16} />
          Add Collection
        </button>
      </header>

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editingId ? `Edit ${form.name || "collection"}` : "New collection"}
        description="Products are added to a collection from Django admin for now."
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
          <AdminField label="Name" wide>
            <AdminInput placeholder="e.g. Documentation essentials" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </AdminField>
          <AdminField label="Description" hint="Optional." wide>
            <AdminTextarea value={form.description} onChange={(e) => set("description", e.target.value)} />
          </AdminField>
          <AdminCheckbox
            label="Featured"
            hint="Shown prominently on the storefront."
            checked={form.is_featured}
            onChange={(v) => set("is_featured", v)}
          />
        </AdminFormGrid>
      </Modal>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Featured</th>
              <th>Products</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.name}</strong>
                </td>
                <td className={styles.muted}>{row.description || "—"}</td>
                <td>{row.is_featured && <Pill tone="gold">Featured</Pill>}</td>
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
        {rows === null && <p className={styles.state}>Loading collections…</p>}
        {rows?.length === 0 && <p className={styles.state}>No collections yet.</p>}
      </div>

      {dialog}
    </div>
  );
}
