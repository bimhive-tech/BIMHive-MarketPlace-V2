"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { AccountApiError, getAccountLicenses, reactivateLicense, type AccountLicense } from "@/lib/accountApi";
import { paymentStatusTone } from "@/features/account/paymentStatusTone";

import styles from "./LicensesList.module.css";

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function machineTone(status: string): "success" | "error" | "neutral" {
  if (status === "active" || status === "paid") return "success";
  if (status === "blocked" || status === "expired") return "error";
  return "neutral";
}

export function LicensesList() {
  const [licenses, setLicenses] = useState<AccountLicense[] | null>(null);
  const [reactivatingId, setReactivatingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getAccountLicenses()
      .then(setLicenses)
      .catch(() => setLicenses([]));
  }, []);

  async function onReactivate(machineId: string) {
    const confirmed = window.confirm(
      "This releases the license from that device so you can activate it on a new one. Continue?",
    );
    if (!confirmed) return;
    setError("");
    setReactivatingId(machineId);
    try {
      const updated = await reactivateLicense(machineId);
      setLicenses((list) => (list ?? []).map((license) => (license.id === updated.id ? updated : license)));
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Could not reactivate this license.");
    } finally {
      setReactivatingId(null);
    }
  }

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
      {error && <p className={styles.error}>{error}</p>}
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
                <div key={machine.id} className={styles.machine}>
                  <Icon name="windows" size={14} className={styles.machineIcon} />
                  <span className={styles.fingerprint}>{machine.fingerprint_preview}</span>
                  <span className={styles.lastSeen}>Last seen {formatDate(machine.last_seen_at)}</span>
                  <Pill tone={machineTone(machine.status)}>{machine.status}</Pill>
                  {license.payment_status === "paid" && machine.status !== "released" && (
                    <button
                      type="button"
                      className={styles.reactivateBtn}
                      disabled={reactivatingId === machine.id}
                      onClick={() => onReactivate(machine.id)}
                    >
                      {reactivatingId === machine.id ? "Reactivating…" : "This isn't my computer anymore"}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
