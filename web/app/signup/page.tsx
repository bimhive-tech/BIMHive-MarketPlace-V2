import type { Metadata } from "next";
import Link from "next/link";

import { AuthShell } from "@/features/auth/AuthShell/AuthShell";
import { SignUpForm } from "@/features/auth/AuthForm/SignUpForm";

export const metadata: Metadata = { title: "Sign up" };

export default function SignupPage() {
  return (
    <AuthShell
      title="Create your account"
      subtitle="Start using premium AEC tools in minutes."
      footer={
        <>
          Already have an account? <Link href="/login" style={{ color: "var(--color-link)", fontWeight: 600 }}>Sign in</Link>
        </>
      }
    >
      <SignUpForm />
    </AuthShell>
  );
}
