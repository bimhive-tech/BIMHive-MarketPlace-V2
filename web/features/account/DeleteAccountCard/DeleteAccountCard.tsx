"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { deleteAccount } from "@/lib/auth";

import styles from "./DeleteAccountCard.module.css";

export function DeleteAccountCard() {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);

  async function onDelete() {
    const confirmed = window.confirm(
      "This will permanently delete your account. This cannot be undone. Continue?",
    );
    if (!confirmed) return;
    setDeleting(true);
    try {
      await deleteAccount();
      router.push("/");
      router.refresh();
    } catch {
      setDeleting(false);
    }
  }

  return (
    <div className={styles.card}>
      <h2 className={styles.title}>Delete Account</h2>
      <p className={styles.text}>Once you delete your account, there is no going back. Please be certain.</p>
      <button className={styles.deleteBtn} onClick={onDelete} disabled={deleting}>
        {deleting ? "Deleting…" : "Delete Account"}
      </button>
    </div>
  );
}
