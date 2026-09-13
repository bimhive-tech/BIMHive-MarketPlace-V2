"use client";

import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { useConfirm } from "@/components/ConfirmDialog/useConfirm";
import { PartnerApiError, resubmitPartnerApplication } from "@/lib/partnerApi";

import styles from "./ResubmitApplicationButton.module.css";

/**
 * Sends a rejected seller application back to BIMHive for another look.
 * Reloads afterwards: the portal's gate reads the application status from the
 * signed-in user, so a full reload is what makes the "under review" screen
 * replace the rejection one.
 */
export function ResubmitApplicationButton() {
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const { confirm, dialog } = useConfirm();

  async function onResubmit() {
    const confirmed = await confirm({
      title: "Resubmit your application?",
      message: "Make sure you've updated your profile first — staff will review it again as it is now.",
      confirmLabel: "Resubmit",
    });
    if (!confirmed) return;
    setError("");
    setSending(true);
    try {
      await resubmitPartnerApplication();
      window.location.reload();
    } catch (err) {
      setError(err instanceof PartnerApiError ? err.detail : "Couldn't resubmit. Please try again.");
      setSending(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <Button onClick={onResubmit} disabled={sending}>
        {sending ? "Resubmitting…" : "Resubmit application"}
      </Button>
      {error && <p className={styles.error}>{error}</p>}
      {dialog}
    </div>
  );
}
