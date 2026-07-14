"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { AuthError, login } from "@/lib/auth";

import styles from "./AuthForm.module.css";

export function SignInForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setPending(true);
    const form = new FormData(e.currentTarget);
    try {
      await login(String(form.get("email")), String(form.get("password")));
      // Only ever redirect to a same-site path — never follow an absolute/external
      // URL from a query param, that's an open-redirect vector.
      const next = searchParams.get("next");
      router.push(next && next.startsWith("/") ? next : "/account");
      router.refresh();
    } catch (err) {
      setError(err instanceof AuthError ? err.detail : "Sign in failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      {error && <div className={styles.alert}>{error}</div>}
      <Field label="Email" name="email" type="email" placeholder="name@company.com" required autoComplete="email" />
      <Field label="Password" name="password" type="password" placeholder="••••••••" required autoComplete="current-password" />
      <Button type="submit" size="lg" fullWidth>
        {pending ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}
