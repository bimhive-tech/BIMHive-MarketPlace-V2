"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { AuthError, register } from "@/lib/auth";

import styles from "./AuthForm.module.css";

export function SignUpForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setFieldErrors({});
    setPending(true);
    const form = new FormData(e.currentTarget);
    try {
      await register(
        String(form.get("email")),
        String(form.get("password")),
        String(form.get("full_name")),
      );
      router.push("/account");
      router.refresh();
    } catch (err) {
      if (err instanceof AuthError) {
        setError(err.detail);
        const fe: Record<string, string> = {};
        for (const key of ["email", "password"]) {
          if (Array.isArray(err.fields[key])) fe[key] = err.fields[key][0];
        }
        setFieldErrors(fe);
      } else {
        setError("Sign up failed.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={onSubmit} noValidate>
      {error && !Object.keys(fieldErrors).length && <div className={styles.alert}>{error}</div>}
      <Field label="Full name" name="full_name" placeholder="Jane Doe" autoComplete="name" />
      <Field
        label="Email"
        name="email"
        type="email"
        placeholder="name@company.com"
        required
        autoComplete="email"
        error={fieldErrors.email}
      />
      <Field
        label="Password"
        name="password"
        type="password"
        placeholder="At least 8 characters"
        required
        autoComplete="new-password"
        error={fieldErrors.password}
        hint="Use 8+ characters with a mix of letters and numbers."
      />
      <Button type="submit" size="lg" fullWidth>
        {pending ? "Creating account…" : "Create account"}
      </Button>
    </form>
  );
}
