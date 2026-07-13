"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { rolesApi, type AdminRole } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const EMPTY = { name: "", description: "", grants_staff_access: false };

export default function AdminRolesPage() {
  const [rows, setRows] = useState<AdminRole[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);

  function load() {
    rolesApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  async function onCreate() {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await rolesApi.create(form);
      setForm(EMPTY);
      setShowForm(false);
      load();
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm("Delete this role? Users with it keep their account but lose the role.")) return;
    await rolesApi.remove(id);
    load();
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Roles &amp; Permissions</h1>
          <p className={styles.sub}>Define the roles assignable to users on the Users page.</p>
        </div>
        <button className={styles.primaryBtn} onClick={() => setShowForm((s) => !s)}>
          <Icon name="plus" size={16} />
          Add Role
        </button>
      </header>

      {showForm && (
        <div className={styles.tableWrap} style={{ padding: "var(--space-5)" }}>
          <div style={{ display: "flex", gap: "var(--space-3)", flexWrap: "wrap", alignItems: "center" }}>
            <input
              className={styles.searchInput}
              placeholder="Role name, e.g. Support Agent"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
            <input
              className={styles.searchInput}
              placeholder="Description"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
            <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontSize: "var(--fs-sm)" }}>
              <input
                type="checkbox"
                checked={form.grants_staff_access}
                onChange={(e) => setForm((f) => ({ ...f, grants_staff_access: e.target.checked }))}
              />
              Grants admin portal access
            </label>
            <button className={styles.primaryBtn} disabled={saving} onClick={onCreate}>
              Create
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
              <th>Role</th>
              <th>Description</th>
              <th>Admin Access</th>
              <th>Users</th>
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
                <td>
                  <Pill tone={row.grants_staff_access ? "gold" : "neutral"}>
                    {row.grants_staff_access ? "Yes" : "No"}
                  </Pill>
                </td>
                <td className={styles.muted}>{row.user_count}</td>
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
        {rows === null && <p className={styles.state}>Loading roles…</p>}
        {rows?.length === 0 && <p className={styles.state}>No roles yet.</p>}
      </div>
    </div>
  );
}
