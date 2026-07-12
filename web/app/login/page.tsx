import type { Metadata } from "next";
import Link from "next/link";

import { AuthShell } from "@/features/auth/AuthShell/AuthShell";
import { SignInForm } from "@/features/auth/AuthForm/SignInForm";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to access your licenses, downloads, and orders."
      footer={
        <>
          Don&apos;t have an account? <Link href="/signup" style={{ color: "var(--color-link)", fontWeight: 600 }}>Sign up</Link>
        </>
      }
    >
      <SignInForm />
    </AuthShell>
  );
}
