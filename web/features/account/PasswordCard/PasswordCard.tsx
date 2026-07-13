"use client";

import { useState } from "react";

import { AuthError, changePassword } from "@/lib/auth";

import styles from "./PasswordCard.module.css";

export function PasswordCard() {
  const [editing, setEditing] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  function reset() {
    setEditing(false);
    setCurrent("");
    setNext("");
    setError("");
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await changePassword(current, next);
      setDone(true);
      reset();
      window.setTimeout(() => setDone(false), 2500);
    } catch (err) {
      setError(err instanceof AuthError ? err.detail : "Could not update your password.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.card}>
      <h2 className={styles.title}>Change Password</h2>
      <p className={styles.sub}>Ensure your account is using a long, random password to stay secure.</p>

      {!editing ? (
        <div className={styles.row}>
          {done && <span className={styles.done}>Password updated</span>}
          <button className={styles.changeBtn} onClick={() => setEditing(true)}>
            Change Password
          </button>
        </div>
      ) : (
        <form className={styles.form} onSubmit={onSubmit}>
          <input
            type="password"
            className={styles.input}
            placeholder="Current password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
            autoComplete="current-password"
          />
          <input
            type="password"
            className={styles.input}
            placeholder="New password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            required
            autoComplete="new-password"
          />
          {error && <p className={styles.error}>{error}</p>}
          <div className={styles.formActions}>
            <button type="submit" className={styles.saveBtn} disabled={saving}>
              {saving ? "Updating…" : "Update Password"}
            </button>
            <button type="button" className={styles.cancelBtn} onClick={reset}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
