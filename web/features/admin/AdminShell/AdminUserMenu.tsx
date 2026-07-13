"use client";

import { useRouter } from "next/navigation";

import { Icon } from "@/components/Icon/Icon";
import { logout } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./AdminShell.module.css";

export function AdminUserMenu({ user }: { user: User }) {
  const router = useRouter();

  async function onLogout() {
    await logout();
    router.push("/");
    router.refresh();
  }

  return (
    <div className={styles.userMenu}>
      <span className={styles.userAvatar}>
        <Icon name="users" size={16} />
      </span>
      <span className={styles.userText}>
        <span className={styles.userName}>{user.full_name}</span>
        <span className={styles.userRole}>Administrator</span>
      </span>
      <button className={styles.logout} onClick={onLogout} aria-label="Sign out">
        <Icon name="logout" size={16} />
      </button>
    </div>
  );
}
