"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { categoriesApi, type AdminCategory } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const EMPTY = { name: "", description: "", icon: "" };

export default function AdminCategoriesPage() {
  const [rows, setRows] = useState<AdminCategory[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  function load() {
    categoriesApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  function startEdit(row: AdminCategory) {
    setEditingId(row.id);
    setForm({ name: row.name, description: row.description, icon: row.icon });
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
      if (editingId) await categoriesApi.update(editingId, form);
      else await categoriesApi.create(form);
      setShowForm(false);
      load();
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm("Delete this category? Products in it are not deleted.")) return;
    await categoriesApi.remove(id);
    load();
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Categories</h1>
          <p className={styles.sub}>The primary groupings shown in the storefront sidebar.</p>
        </div>
        <button className={styles.primaryBtn} onClick={startNew}>
          <Icon name="plus" size={16} />
          Add Category
        </button>
      </header>

      {showForm && (
        <div className={styles.tableWrap} style={{ padding: "var(--space-5)" }}>
          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap" }}>
            <input
              className={styles.searchInput}
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
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
            <button className={styles.primaryBtn} disabled={saving} onClick={onSave}>
              {editingId ? "Save" : "Create"}
            </button>
            <button className={styles.actionBtn} onClick={() => setShowForm(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

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
                  <strong>{row.name}</strong>
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
