"use client";

import { useRouter } from "next/navigation";

import { Icon } from "@/components/Icon/Icon";
import { logout } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./UserMenu.module.css";

/** Avatar + name/role + sign-out, shared by the admin and partner portal
 * topbars (each shell just supplies its own roleLabel). */
export function UserMenu({ user, roleLabel }: { user: User; roleLabel: string }) {
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
        <span className={styles.userRole}>{roleLabel}</span>
      </span>
      <button className={styles.logout} onClick={onLogout} aria-label="Sign out">
        <Icon name="logout" size={16} />
      </button>
    </div>
  );
}
