"use client";

import { AdminShell } from "@/features/admin/AdminShell/AdminShell";
import { RequireAuth } from "@/features/auth/RequireAuth/RequireAuth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth staffOnly>
      {(user) => <AdminShell user={user}>{children}</AdminShell>}
    </RequireAuth>
  );
}
