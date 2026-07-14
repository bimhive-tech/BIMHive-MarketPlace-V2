"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { getAccountLicenses, type AccountLicense } from "@/lib/accountApi";
import { paymentStatusTone } from "@/features/account/paymentStatusTone";

import styles from "./LicensesList.module.css";

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function machineTone(status: string): "success" | "error" | "neutral" {
  if (status === "active") return "success";
  if (status === "blocked" || status === "expired") return "error";
  return "neutral";
}

export function LicensesList() {
  const [licenses, setLicenses] = useState<AccountLicense[] | null>(null);

  useEffect(() => {
    getAccountLicenses()
      .then(setLicenses)
      .catch(() => setLicenses([]));
  }, []);

  if (licenses === null) return <p className={styles.loading}>Loading your licenses…</p>;

  if (licenses.length === 0) {
    return (
      <EmptyState
        icon="library"
        title="No licenses yet"
        text="Your license keys and renewal dates will appear here after your first purchase."
        actionLabel="Browse the marketplace"
        actionHref="/catalog"
      />
    );
  }

  return (
    <div className={styles.list}>
      {licenses.map((license) => (
        <div key={license.id} className={styles.card}>
          <div className={styles.head}>
            <div>
              <span className={styles.product}>{license.product_name}</span>
              <span className={styles.code}>{license.product_code}</span>
            </div>
            <Pill tone={paymentStatusTone(license.payment_status)}>{license.payment_status}</Pill>
          </div>

          <div className={styles.meta}>
            <span>
              <Icon name="lock" size={14} /> {license.license_key || "No key issued"}
            </span>
            <span>Purchased {formatDate(license.paid_at ?? license.requested_at)}</span>
          </div>

          {license.machines.length > 0 && (
            <div className={styles.machines}>
              {license.machines.map((machine) => (
                <div key={machine.fingerprint_preview} className={styles.machine}>
                  <Icon name="windows" size={14} className={styles.machineIcon} />
                  <span className={styles.fingerprint}>{machine.fingerprint_preview}</span>
                  <span className={styles.lastSeen}>Last seen {formatDate(machine.last_seen_at)}</span>
                  <Pill tone={machineTone(machine.status)}>{machine.status}</Pill>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
