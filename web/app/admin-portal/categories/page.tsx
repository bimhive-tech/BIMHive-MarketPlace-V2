"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
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

  function load() {
    categoriesApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  // Only a top-level category can be picked as a parent — the storefront
  // renders exactly two levels, and the API rejects deeper nesting.
  const parentOptions = (rows ?? []).filter((row) => !row.parent && row.id !== editingId);

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

  async function onDelete(id: number) {
    if (!window.confirm("Delete this category? Products in it are not deleted.")) return;
    try {
      await categoriesApi.remove(id);
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

      {showForm && (
        <div className={styles.formPanel}>
          <div className={styles.formGrid}>
            <input
              className={styles.searchInput}
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
            <select
              className={styles.select}
              value={form.parent}
              onChange={(e) => setForm((f) => ({ ...f, parent: e.target.value }))}
            >
              <option value="">Top-level category</option>
              {parentOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  Subcategory of {option.name}
                </option>
              ))}
            </select>
            <input
              className={styles.searchInput}
              placeholder="Icon name (optional)"
              value={form.icon}
              onChange={(e) => setForm((f) => ({ ...f, icon: e.target.value }))}
            />
            <input
              className={styles.searchInput}
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
          <div className={styles.formActions}>
            <button className={styles.primaryBtn} disabled={saving} onClick={onSave}>
              {editingId ? "Save" : "Create"}
            </button>
            <button className={styles.actionBtn} onClick={() => setShowForm(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

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
        {rows === null && <p className={styles.state}>Loading categories…</p>}
        {rows?.length === 0 && <p className={styles.state}>No categories yet.</p>}
      </div>
    </div>
  );
}
