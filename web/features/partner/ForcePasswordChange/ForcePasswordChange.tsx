"use client";

import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { Logo } from "@/components/Logo/Logo";
import { AuthError, changePassword } from "@/lib/auth";

import styles from "./ForcePasswordChange.module.css";

/** Blocks the partner portal until a partner-issued (admin-set) password is
 * replaced with one only the partner knows — see catalog.admin_api's
 * AdminPartnerViewSet.set_login, which sets must_change_password=True. */
export function ForcePasswordChange() {
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setPending(true);
    const form = new FormData(e.currentTarget);
    const newPassword = String(form.get("new_password"));
    if (newPassword !== String(form.get("confirm_password"))) {
      setError("Passwords don't match.");
      setPending(false);
      return;
    }
    try {
      await changePassword(String(form.get("current_password")), newPassword);
      window.location.reload(); // re-fetch /api/auth/me so the layout re-evaluates must_change_password
    } catch (err) {
      setError(err instanceof AuthError ? err.detail : "Could not update your password.");
      setPending(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <Logo />
        <h1 className={styles.title}>Set your password</h1>
        <p className={styles.subtitle}>
          Your BIMHIVE partner login was set up with a temporary password. Choose your own before
          continuing to the partner portal.
        </p>
        <form className={styles.form} onSubmit={onSubmit} noValidate>
          {error && <div className={styles.alert}>{error}</div>}
          <Field
            label="Temporary password"
            name="current_password"
            type="password"
            placeholder="The password BIMHIVE gave you"
            required
            autoComplete="current-password"
          />
          <Field
            label="New password"
            name="new_password"
            type="password"
            placeholder="••••••••"
            required
            autoComplete="new-password"
          />
          <Field
            label="Confirm new password"
            name="confirm_password"
            type="password"
            placeholder="••••••••"
            required
            autoComplete="new-password"
          />
          <Button type="submit" size="lg" fullWidth disabled={pending}>
            {pending ? "Setting password…" : "Set password & continue"}
          </Button>
        </form>
      </div>
    </div>
  );
}
