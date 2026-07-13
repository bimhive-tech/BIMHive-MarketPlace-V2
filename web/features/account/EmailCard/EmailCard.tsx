"use client";

import { useState } from "react";

import { AuthError, updateProfile } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./EmailCard.module.css";

export function EmailCard({ user, onSaved }: { user: User; onSaved: (user: User) => void }) {
  const [editing, setEditing] = useState(false);
  const [email, setEmail] = useState(user.email);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const updated = await updateProfile({ email: email.trim().toLowerCase() });
      onSaved(updated);
      setEditing(false);
    } catch (err) {
      setError(err instanceof AuthError ? err.detail : "Could not update your email.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.card}>
      <h2 className={styles.title}>Email Address</h2>
      <p className={styles.sub}>Update the email address used for your account.</p>

      {!editing ? (
        <div className={styles.row}>
          <div>
            <p className={styles.label}>Current Email</p>
            <p className={styles.value}>{user.email}</p>
          </div>
          <button className={styles.changeBtn} onClick={() => setEditing(true)}>
            Change Email
          </button>
        </div>
      ) : (
        <form className={styles.form} onSubmit={onSubmit}>
          <input
            type="email"
            className={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {error && <p className={styles.error}>{error}</p>}
          <div className={styles.formActions}>
            <button type="submit" className={styles.saveBtn} disabled={saving}>
              {saving ? "Saving…" : "Save Email"}
            </button>
            <button
              type="button"
              className={styles.cancelBtn}
              onClick={() => {
                setEditing(false);
                setEmail(user.email);
                setError("");
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
