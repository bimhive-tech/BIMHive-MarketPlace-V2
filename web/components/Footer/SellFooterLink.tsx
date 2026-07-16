"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./Footer.module.css";

/** Hidden for staff — they already have unrestricted admin access and must
 * never also be a partner (see catalog.partner_api.BecomeSellerView). The
 * rest of the footer stays a server component; only this one link needs to
 * know who's looking at it. */
export function SellFooterLink() {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    me().then(setUser);
  }, []);

  if (user?.is_staff) return null;

  return (
    <Link href="/sell" className={styles.link}>
      Become a Seller
    </Link>
  );
}
