"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./CategorySidebar.module.css";

/** Client-side so it can hide once the visitor already has a seller
 * application (any status) — no point pitching "Become a Seller" to someone
 * who already applied — or is staff (staff already have unrestricted admin
 * access and must never also be a partner, see
 * catalog.partner_api.BecomeSellerView). Fetched separately from the
 * server-rendered category list above it so that list doesn't need to wait
 * on a client round trip. */
export function SellPromo() {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    me().then(setUser);
  }, []);

  if (user === undefined || user?.partner || user?.is_staff) return null;

  return (
    <div className={styles.sellCard}>
      <h3 className={styles.sellTitle}>Sell on BIMHIVE</h3>
      <p className={styles.sellText}>Reach thousands of AEC professionals.</p>
      <Button href="/sell" variant="secondary" fullWidth>
        Become a Seller
      </Button>
    </div>
  );
}
