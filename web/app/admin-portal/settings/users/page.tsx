"use client";

import { useEffect, useState } from "react";

import { Pill } from "@/components/Pill/Pill";
import { getAdminUsers, rolesApi, updateAdminUser, type AdminRole, type AdminUser } from "@/lib/adminApi";
import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function AdminUsersSettingsPage() {
  const [rows, setRows] = useState<AdminUser[] | null>(null);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [search, setSearch] = useState("");
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [error, setError] = useState("");

  function load() {
    getAdminUsers(search).then(setRows).catch(() => setRows([]));
  }

  useEffect(() => {
    rolesApi.list().then(setRoles).catch(() => setRoles([]));
    me().then(setCurrentUser);
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

  async function onToggleAdmin(user: AdminUser) {
    setError("");
    try {
      const updated = await updateAdminUser(user.id, { is_superuser: !user.is_superuser });
      setRows((list) => list?.map((u) => (u.id === user.id ? updated : u)) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change Admin status.");
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Users</h1>
          <p className={styles.sub}>
            Assign roles and manage access for every account. Admin is the top tier — only an Admin can
            reach this page, manage other Admins/Staff, or change Settings.
          </p>
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

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Access</th>
              <th>Status</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => {
              const isSelf = row.id === currentUser?.id;
              const level = row.is_superuser ? "Admin" : row.is_staff ? "Staff" : "Customer";
              return (
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
                    <div className={styles.actionRow}>
                      <Pill tone={level === "Admin" ? "gold" : level === "Staff" ? "success" : "neutral"}>
                        {level}
                      </Pill>
                      {row.is_staff && (
                        <button
                          className={styles.actionBtn}
                          disabled={isSelf && row.is_superuser}
                          title={isSelf && row.is_superuser ? "You can't remove your own Admin access." : undefined}
                          onClick={() => onToggleAdmin(row)}
                        >
                          {row.is_superuser ? "Remove Admin" : "Make Admin"}
                        </button>
                      )}
                    </div>
                  </td>
                  <td>
                    <button
                      className={styles.actionBtn}
                      disabled={isSelf}
                      title={isSelf ? "You can't deactivate your own account." : undefined}
                      onClick={() => onToggleActive(row)}
                    >
                      {row.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                  <td className={styles.muted}>{formatDate(row.date_joined)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows === null && <p className={styles.state}>Loading users…</p>}
        {rows?.length === 0 && <p className={styles.state}>No users found.</p>}
      </div>
    </div>
  );
}
