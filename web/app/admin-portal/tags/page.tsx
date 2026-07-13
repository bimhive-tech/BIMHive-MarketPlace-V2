"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { tagsApi, type AdminTag } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

export default function AdminTagsPage() {
  const [rows, setRows] = useState<AdminTag[] | null>(null);
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);

  function load() {
    tagsApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  async function onCreate() {
    if (!newName.trim()) return;
    setSaving(true);
    try {
      await tagsApi.create({ name: newName.trim() });
      setNewName("");
      load();
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm("Delete this tag? It will be removed from all products.")) return;
    await tagsApi.remove(id);
    load();
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Tags</h1>
          <p className={styles.sub}>Fine-grained labels used to filter and describe products.</p>
        </div>
      </header>

      <div className={styles.toolbar}>
        <input
          className={styles.searchInput}
          placeholder="New tag name…"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onCreate()}
        />
        <button className={styles.primaryBtn} disabled={saving} onClick={onCreate}>
          <Icon name="plus" size={16} />
          Add Tag
        </button>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
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
                <td className={styles.muted}>{row.product_count}</td>
                <td>
                  <button
                    className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                    aria-label="Delete"
                    onClick={() => onDelete(row.id)}
                  >
                    <Icon name="trash" size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows === null && <p className={styles.state}>Loading tags…</p>}
        {rows?.length === 0 && <p className={styles.state}>No tags yet.</p>}
      </div>
    </div>
  );
}
