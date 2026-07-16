"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./RequireAuth.module.css";

/**
 * Client auth gate: renders children only for a signed-in user, otherwise sends
 * them to /login. Use to protect account pages. `staffOnly` also gates on
 * is_staff; `partnerOnly` also gates on the user having a linked partner
 * (partner-portal access) — real enforcement is server-side (see
 * catalog.permissions.IsStaffOrPartner/IsPartnerUser), this only avoids
 * flashing a page the API would reject anyway.
 */
export function RequireAuth({
  children,
  staffOnly = false,
  partnerOnly = false,
}: {
  children: (user: User) => React.ReactNode;
  staffOnly?: boolean;
  partnerOnly?: boolean;
}) {
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    me().then((u) => {
      if (!u) router.replace("/login");
      else if (staffOnly && !u.is_staff) router.replace("/account");
      else if (partnerOnly && !u.partner) router.replace("/account");
      else setUser(u);
    });
  }, [router, staffOnly, partnerOnly]);

  if (!user) {
    return <div className={styles.loading}>Loading…</div>;
  }
  return <>{children(user)}</>;
}
