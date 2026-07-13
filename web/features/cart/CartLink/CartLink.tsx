"use client";

import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { useCart } from "@/lib/cart";

import styles from "./CartLink.module.css";

export function CartLink() {
  const { count } = useCart();

  return (
    <Link href="/cart" className={styles.cart} aria-label={`Cart, ${count} item${count === 1 ? "" : "s"}`}>
      <Icon name="cart" size={22} />
      {count > 0 && <span className={styles.badge}>{count > 99 ? "99+" : count}</span>}
    </Link>
  );
}
