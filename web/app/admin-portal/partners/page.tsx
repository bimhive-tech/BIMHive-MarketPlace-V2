"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { AdminApiError, partnersApi, setPartnerLogin, type AdminPartner } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const EMPTY = { name: "", tagline: "", bio: "", logo_url: "", website: "", is_verified: false };

export default function AdminPartnersPage() {
  const [rows, setRows] = useState<AdminPartner[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const [loginEmail, setLoginEmail] = useState("");
  const [issuing, setIssuing] = useState(false);
  const [issueError, setIssueError] = useState("");
  const [issuedLogin, setIssuedLogin] = useState<{ email: string; password: string } | null>(null);

  function load() {
    partnersApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  function startEdit(row: AdminPartner) {
    setEditingId(row.id);
    setForm({
      name: row.name, tagline: row.tagline, bio: row.bio, logo_url: row.logo_url,
      website: row.website, is_verified: row.is_verified,
    });
    setLoginEmail(row.owner_email);
    setIssuedLogin(null);
    setIssueError("");
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
      if (editingId) await partnersApi.update(editingId, form);
      else await partnersApi.create(form);
      setShowForm(false);
      load();
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: number) {
    if (!window.confirm("Delete this partner? Products from them are not deleted.")) return;
    await partnersApi.remove(id);
    load();
  }

  async function onIssueLogin() {
    if (!editingId || !loginEmail.trim()) return;
    setIssueError("");
    setIssuing(true);
    try {
      const result = await setPartnerLogin(editingId, loginEmail.trim());
      setIssuedLogin(result);
      load();
    } catch (err) {
      setIssueError(err instanceof AdminApiError ? err.detail : "Could not issue a login.");
    } finally {
      setIssuing(false);
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Partners</h1>
          <p className={styles.sub}>Sellers and publishers products are listed under.</p>
        </div>
        <button className={styles.primaryBtn} onClick={startNew}>
          <Icon name="plus" size={16} />
          Add Partner
        </button>
      </header>

      {showForm && (
        <div className={styles.tableWrap}>
          <div className={styles.formPanel}>
            <div className={styles.formGrid}>
              <input
                className={styles.searchInput}
                placeholder="Name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
              <input
                className={styles.searchInput}
                placeholder="Tagline"
                value={form.tagline}
                onChange={(e) => setForm((f) => ({ ...f, tagline: e.target.value }))}
              />
              <input
                className={styles.searchInput}
                placeholder="Logo URL"
                value={form.logo_url}
                onChange={(e) => setForm((f) => ({ ...f, logo_url: e.target.value }))}
              />
              <input
                className={styles.searchInput}
                placeholder="Website"
                value={form.website}
                onChange={(e) => setForm((f) => ({ ...f, website: e.target.value }))}
              />
              <textarea
                className={styles.textarea}
                rows={3}
                placeholder="Bio"
                value={form.bio}
                onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))}
              />
            </div>
            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={form.is_verified}
                onChange={(e) => setForm((f) => ({ ...f, is_verified: e.target.checked }))}
              />
              Verified
            </label>
            <div className={styles.formActions}>
              <button className={styles.primaryBtn} disabled={saving} onClick={onSave}>
                {editingId ? "Save" : "Create"}
              </button>
              <button className={styles.actionBtn} onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>

            {editingId && (
              <div className={styles.loginPanel}>
                <p className={styles.loginPanelTitle}>Partner Portal Login</p>
                <p className={styles.muted}>
                  {issuedLogin
                    ? "Relay this password to the partner — it won't be shown again."
                    : "Give this partner their own login to manage products in the partner portal."}
                </p>
                {issuedLogin ? (
                  <div className={styles.passwordReveal}>
                    <span>Email: <strong>{issuedLogin.email}</strong></span>
                    <span>Temporary password: <strong className={styles.mono}>{issuedLogin.password}</strong></span>
                  </div>
                ) : (
                  <div className={styles.formGrid}>
                    <input
                      className={styles.searchInput}
                      type="email"
                      placeholder="Login email"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                    />
                    <button className={styles.actionBtn} disabled={issuing || !loginEmail.trim()} onClick={onIssueLogin}>
                      {issuing ? "Issuing…" : "Issue Login"}
                    </button>
                  </div>
                )}
                {issueError && <p className={styles.error}>{issueError}</p>}
              </div>
            )}
          </div>
        </div>
      )}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Tagline</th>
              <th>Verified</th>
              <th>Products</th>
              <th>Portal Login</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.name}</strong>
                </td>
                <td className={styles.muted}>{row.tagline || "—"}</td>
                <td>{row.is_verified && <Pill tone="success">Verified</Pill>}</td>
                <td className={styles.muted}>{row.product_count}</td>
                <td className={styles.muted}>{row.owner_email || "Not set"}</td>
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
        {rows === null && <p className={styles.state}>Loading partners…</p>}
        {rows?.length === 0 && <p className={styles.state}>No partners yet.</p>}
      </div>
    </div>
  );
}
