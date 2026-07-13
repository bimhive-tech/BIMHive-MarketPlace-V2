"use client";

import { useEffect, useState } from "react";

import { Pill } from "@/components/Pill/Pill";
import { getAdminUsers, rolesApi, updateAdminUser, type AdminRole, type AdminUser } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function AdminUsersSettingsPage() {
  const [rows, setRows] = useState<AdminUser[] | null>(null);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [search, setSearch] = useState("");

  function load() {
    getAdminUsers(search).then(setRows).catch(() => setRows([]));
  }

  useEffect(() => {
    rolesApi.list().then(setRoles).catch(() => setRoles([]));
  }, []);

  useEffect(() => {
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  async function onRoleChange(userId: number, roleId: string) {
    const updated = await updateAdminUser(userId, { role: roleId ? Number(roleId) : null });
    setRows((list) => list?.map((u) => (u.id === userId ? updated : u)) ?? null);
  }

  async function onToggleActive(user: AdminUser) {
    const updated = await updateAdminUser(user.id, { is_active: !user.is_active });
    setRows((list) => list?.map((u) => (u.id === user.id ? updated : u)) ?? null);
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Users</h1>
          <p className={styles.sub}>Assign roles and manage access for every account.</p>
        </div>
      </header>

      <div className={styles.toolbar}>
        <input
          className={styles.searchInput}
          placeholder="Search by email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Admin Access</th>
              <th>Status</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.full_name}</strong>
                </td>
                <td className={styles.muted}>{row.email}</td>
                <td>
                  <select
                    className={styles.select}
                    value={row.role ?? ""}
                    onChange={(e) => onRoleChange(row.id, e.target.value)}
                  >
                    <option value="">No role</option>
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <Pill tone={row.is_staff ? "gold" : "neutral"}>{row.is_staff ? "Staff" : "Customer"}</Pill>
                </td>
                <td>
                  <button className={styles.actionBtn} onClick={() => onToggleActive(row)}>
                    {row.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
                <td className={styles.muted}>{formatDate(row.date_joined)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows === null && <p className={styles.state}>Loading users…</p>}
        {rows?.length === 0 && <p className={styles.state}>No users found.</p>}
      </div>
    </div>
  );
}
