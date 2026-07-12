"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { logout, me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./AuthNav.module.css";

export function AuthNav() {
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    me().then(setUser);
  }, []);

  async function onLogout() {
    await logout();
    setUser(null);
    router.push("/");
    router.refresh();
  }

  // While loading, render nothing to avoid a flash of the wrong state.
  if (user === undefined) return <span className={styles.placeholder} aria-hidden="true" />;

  if (user) {
    return (
      <div className={styles.authed}>
        <Link href="/account" className={styles.account}>
          <span className={styles.avatar}>
            <Icon name="users" size={16} />
          </span>
          <span className={styles.name}>{user.full_name}</span>
        </Link>
        <button className={styles.logout} onClick={onLogout}>
          Log out
        </button>
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
