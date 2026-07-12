"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

/**
 * Client auth gate: renders children only for a signed-in user, otherwise sends
 * them to /login. Use to protect account pages. `staffOnly` also gates on is_staff.
 */
export function RequireAuth({
  children,
  staffOnly = false,
}: {
  children: (user: User) => React.ReactNode;
  staffOnly?: boolean;
}) {
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    me().then((u) => {
      if (!u) router.replace("/login");
      else if (staffOnly && !u.is_staff) router.replace("/account");
      else setUser(u);
    });
  }, [router, staffOnly]);

  if (!user) {
    return <div style={{ padding: "80px 24px", color: "var(--color-muted)" }}>Loading…</div>;
  }
  return <>{children(user)}</>;
}
