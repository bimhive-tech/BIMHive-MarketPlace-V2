"use client";

import { AccountShell } from "@/features/account/AccountShell/AccountShell";
import { RequireAuth } from "@/features/auth/RequireAuth/RequireAuth";

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      {() => <AccountShell>{children}</AccountShell>}
    </RequireAuth>
  );
}
