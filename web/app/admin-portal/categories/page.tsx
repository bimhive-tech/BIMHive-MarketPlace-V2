"use client";

import { useEffect, useState } from "react";

import { useConfirm } from "@/components/ConfirmDialog/useConfirm";
import { Icon } from "@/components/Icon/Icon";
import { Modal } from "@/components/Modal/Modal";
import {
  AdminField,
  AdminFormGrid,
  AdminInput,
  AdminSelect,
} from "@/features/admin/AdminForm/AdminForm";
import { categoriesApi, type AdminCategory } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";
import tree from "./categories.module.css";

const EMPTY = { name: "", description: "", icon: "", parent: "" };

type CategoryForm = typeof EMPTY;

export default function AdminCategoriesPage() {
  const [rows, setRows] = useState<AdminCategory[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CategoryForm>(EMPTY);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { confirm, dialog } = useConfirm();

  function load() {
    categoriesApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  // Only a top-level category can be picked as a parent — the storefront
  // renders exactly two levels, and the API rejects deeper nesting.
  const parentOptions = (rows ?? []).filter((row) => !row.parent && row.id !== editingId);

  function set<K extends keyof CategoryForm>(key: K, value: CategoryForm[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function startEdit(row: AdminCategory) {
    setEditingId(row.id);
    setForm({
      name: row.name,
      description: row.description,
      icon: row.icon,
      parent: row.parent ? String(row.parent) : "",
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
    const payload = { ...form, parent: form.parent ? Number(form.parent) : null };
    try {
      if (editingId) await categoriesApi.update(editingId, payload);
      else await categoriesApi.create(payload);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save this category.");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(row: AdminCategory) {
    const confirmed = await confirm({
      title: `Delete ${row.name}?`,
      message: "Products in it are not deleted.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await categoriesApi.remove(row.id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this category.");
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Categories</h1>
          <p className={styles.sub}>
            One top-level category with subcategories beneath it — that tree is what the storefront
            sidebar renders.
          </p>
        </div>
        <button className={styles.primaryBtn} onClick={startNew}>
          <Icon name="plus" size={16} />
          Add Category
        </button>
      </header>

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editingId ? `Edit ${form.name || "category"}` : "New category"}
        description="The storefront sidebar shows two levels: top-level categories and their subcategories."
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
            <AdminInput placeholder="e.g. Modelling" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </AdminField>
          <AdminField label="Level" hint="A subcategory sits under a top-level category.">
            <AdminSelect value={form.parent} onChange={(e) => set("parent", e.target.value)}>
              <option value="">Top-level category</option>
              {parentOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  Subcategory of {option.name}
                </option>
              ))}
            </AdminSelect>
          </AdminField>
          <AdminField label="Icon" hint="A line-icon name from the site's icon set. Optional.">
            <AdminInput placeholder="e.g. layers" value={form.icon} onChange={(e) => set("icon", e.target.value)} />
          </AdminField>
          <AdminField label="Description" hint="Optional.">
            <AdminInput value={form.description} onChange={(e) => set("description", e.target.value)} />
          </AdminField>
        </AdminFormGrid>
      </Modal>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Products</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  {row.parent ? (
                    <span className={tree.childName}>
                      <span className={tree.branch} aria-hidden="true">
                        └
                      </span>
                      {row.name}
                    </span>
                  ) : (
                    <>
                      <strong>{row.name}</strong>
                      <span className={tree.rootBadge}>Top level</span>
                    </>
                  )}
                </td>
                <td className={styles.muted}>{row.description || "—"}</td>
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
        {rows === null && <p className={styles.state}>Loading categories…</p>}
        {rows?.length === 0 && <p className={styles.state}>No categories yet.</p>}
      </div>

      {dialog}
    </div>
  );
}
