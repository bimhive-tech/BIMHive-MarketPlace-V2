"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { getSystemStatus, type AdminSystemStatus } from "@/lib/adminApi";

import styles from "./settings.module.css";

function StatusRow({ label, ok, okLabel = "Configured", missingLabel = "Not configured" }: {
  label: string;
  ok: boolean;
  okLabel?: string;
  missingLabel?: string;
}) {
  return (
    <div className={styles.row}>
      <span className={styles.rowLabel}>{label}</span>
      <Pill tone={ok ? "success" : "warning"}>{ok ? okLabel : missingLabel}</Pill>
    </div>
  );
}

export default function AdminGeneralSettingsPage() {
  const [status, setStatus] = useState<AdminSystemStatus | null>(null);

  useEffect(() => {
    getSystemStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <h1 className={styles.title}>General</h1>
        <p className={styles.sub}>Live configuration status — read from the server&apos;s environment, not editable here.</p>
      </header>

      {!status ? (
        <p className={styles.state}>Loading…</p>
      ) : (
        <div className={styles.grid}>
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <Icon name="shield" size={18} /> Environment
            </h2>
            <StatusRow label="Debug mode" ok={!status.debug_mode} okLabel="Off (production-safe)" missingLabel="On" />
            <StatusRow label="Database" ok={true} okLabel={status.database} />
          </div>

          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <Icon name="lock" size={18} /> Licensing
            </h2>
            <StatusRow label="LICENSE_PEPPER" ok={status.licensing.pepper_configured} />
            <p className={styles.hint}>
              Must match production&apos;s pepper exactly before real activations are trusted.
            </p>
          </div>

          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <Icon name="database" size={18} /> Storage (Cloudflare R2)
            </h2>
            <StatusRow label={`Bucket: ${status.storage.bucket}`} ok={status.storage.configured} />
          </div>

          <div className={styles.card}>
            <h2 className={styles.cardTitle}>
              <Icon name="cart" size={18} /> Payments
            </h2>
            <StatusRow label="Stripe" ok={status.payments.stripe_configured} />
            <StatusRow label="PayPal" ok={status.payments.paypal_configured} />
          </div>
        </div>
      )}
    </div>
  );
}
