"use client";

import { useEffect, useMemo, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { ADMIN_PERMISSIONS, rolesApi, type AdminRole } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const EMPTY = { name: "", description: "", grants_staff_access: false, permissions: [] as string[] };
type RoleForm = typeof EMPTY;

export default function AdminRolesPage() {
  const [rows, setRows] = useState<AdminRole[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<RoleForm>(EMPTY);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Grouped once, not per render — ADMIN_PERMISSIONS is a fixed constant.
  const groups = useMemo(() => {
    const byGroup = new Map<string, typeof ADMIN_PERMISSIONS>();
    for (const perm of ADMIN_PERMISSIONS) {
      byGroup.set(perm.group, [...(byGroup.get(perm.group) ?? []), perm]);
    }
    return [...byGroup.entries()];
  }, []);

  function load() {
    rolesApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  function startNew() {
    setEditingId(null);
    setForm(EMPTY);
    setError("");
    setShowForm(true);
  }

  function startEdit(row: AdminRole) {
    setEditingId(row.id);
    setForm({
      name: row.name,
      description: row.description,
      grants_staff_access: row.grants_staff_access,
      permissions: row.permissions,
    });
    setError("");
    setShowForm(true);
  }

  function togglePermission(key: string) {
    setForm((f) => ({
      ...f,
      permissions: f.permissions.includes(key)
        ? f.permissions.filter((p) => p !== key)
        : [...f.permissions, key],
    }));
  }

  async function onSave() {
    if (!form.name.trim()) return;
    setSaving(true);
    setError("");
    try {
      if (editingId) await rolesApi.update(editingId, form);
      else await rolesApi.create(form);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save this role.");
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
          <p className={styles.sub}>
            Define what a Staff account can do in the admin portal. Users, Roles &amp; Permissions, and
            Settings are never grantable here — only an Admin account can reach those.
          </p>
        </div>
        <button className={styles.primaryBtn} onClick={startNew}>
          <Icon name="plus" size={16} />
          Add Role
        </button>
      </header>

      {showForm && (
        <div className={styles.formPanel}>
          <div className={styles.formGrid}>
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
          </div>
          <label className={styles.checkboxRow}>
            <input
              type="checkbox"
              checked={form.grants_staff_access}
              onChange={(e) => setForm((f) => ({ ...f, grants_staff_access: e.target.checked }))}
            />
            Grants admin portal access (this role makes a user Staff)
          </label>

          {form.grants_staff_access && (
            <div>
              <p className={styles.loginPanelTitle}>Permissions</p>
              {groups.map(([group, perms]) => (
                <div key={group} style={{ marginTop: "var(--space-3)" }}>
                  <p className={styles.muted} style={{ marginBottom: "var(--space-2)" }}>
                    {group}
                  </p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)" }}>
                    {perms.map((perm) => (
                      <label key={perm.key} className={styles.checkboxRow}>
                        <input
                          type="checkbox"
                          checked={form.permissions.includes(perm.key)}
                          onChange={() => togglePermission(perm.key)}
                        />
                        {perm.label}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
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
      )}

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Role</th>
              <th>Description</th>
              <th>Admin Access</th>
              <th>Permissions</th>
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
                <td className={styles.muted}>
                  {row.permissions.length > 0 ? `${row.permissions.length} granted` : "None"}
                </td>
                <td className={styles.muted}>{row.user_count}</td>
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
        {rows === null && <p className={styles.state}>Loading roles…</p>}
        {rows?.length === 0 && <p className={styles.state}>No roles yet.</p>}
      </div>
    </div>
  );
}
