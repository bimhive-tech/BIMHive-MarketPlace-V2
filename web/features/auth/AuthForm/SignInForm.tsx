"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { AuthError, login } from "@/lib/auth";

import styles from "./AuthForm.module.css";

export function SignInForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setPending(true);
    const form = new FormData(e.currentTarget);
    try {
      await login(String(form.get("email")), String(form.get("password")));
      router.push("/account");
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
