"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { logout, me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./AuthNav.module.css";

export function AuthNav() {
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    me().then(setUser);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEscape);
    };
  }, [open]);

  async function onLogout() {
    setOpen(false);
    await logout();
    setUser(null);
    router.push("/");
    router.refresh();
  }

  // While loading, render nothing to avoid a flash of the wrong state.
  if (user === undefined) return <span className={styles.placeholder} aria-hidden="true" />;

  if (user) {
    return (
      <div className={styles.authed} ref={rootRef}>
        <button
          className={styles.trigger}
          onClick={() => setOpen((v) => !v)}
          aria-haspopup="menu"
          aria-expanded={open}
        >
          <span className={styles.avatar}>
            <Icon name="users" size={16} />
          </span>
          <span className={styles.name}>{user.full_name}</span>
          <Icon name="chevron-down" size={14} className={styles.chevron} />
        </button>

        {open && (
          <div className={styles.menu} role="menu">
            <Link href="/account" role="menuitem" className={styles.menuItem} onClick={() => setOpen(false)}>
              <Icon name="grid" size={16} />
              Overview
            </Link>
            <Link
              href="/account/profile"
              role="menuitem"
              className={styles.menuItem}
              onClick={() => setOpen(false)}
            >
              <Icon name="users" size={16} />
              Profile
            </Link>
            <div className={styles.menuDivider} />
            <button role="menuitem" className={styles.menuItem} onClick={onLogout}>
              <Icon name="logout" size={16} />
              Log out
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={styles.guest}>
      <Link href="/login" className={styles.login}>
        Log in
      </Link>
      <Button href="/signup" size="md">
        Sign up
      </Button>
    </div>
  );
}
