"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import {
  AccountApiError,
  getAccountLicenses,
  redeemLicenseCode,
  type AccountLicense,
} from "@/lib/accountApi";
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
  const [error, setError] = useState("");
  const [redeemCode, setRedeemCode] = useState("");
  const [redeeming, setRedeeming] = useState(false);
  const [redeemError, setRedeemError] = useState("");
  const [redeemSuccess, setRedeemSuccess] = useState("");

  useEffect(() => {
    getAccountLicenses()
      .then(setLicenses)
      .catch(() => setLicenses([]));
  }, []);

  async function onRedeem() {
    if (!redeemCode.trim()) return;
    setRedeemError("");
    setRedeemSuccess("");
    setRedeeming(true);
    try {
      const updated = await redeemLicenseCode(redeemCode.trim());
      setLicenses((list) => {
        const existing = list ?? [];
        const withoutUpdated = existing.filter((license) => license.id !== updated.id);
        return [updated, ...withoutUpdated];
      });
      setRedeemCode("");
      setRedeemSuccess(`${updated.product_name} is now on your account.`);
    } catch (err) {
      setRedeemError(err instanceof AccountApiError ? err.detail : "Could not redeem this code.");
    } finally {
      setRedeeming(false);
    }
  }

  const redeemForm = (
    <div className={styles.redeemCard}>
      <span className={styles.redeemTitle}>Have a license code?</span>
      {redeemError && <p className={styles.error}>{redeemError}</p>}
      {redeemSuccess && <p className={styles.success}>{redeemSuccess}</p>}
      <div className={styles.redeemRow}>
        <input
          className={styles.redeemInput}
          placeholder="GIFT-XXXX-XXXX-XXXX"
          value={redeemCode}
          onChange={(e) => setRedeemCode(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onRedeem()}
        />
        <button className={styles.redeemBtn} disabled={redeeming || !redeemCode.trim()} onClick={onRedeem}>
          {redeeming ? "Redeeming…" : "Redeem"}
        </button>
      </div>
    </div>
  );

  if (licenses === null) return <p className={styles.loading}>Loading your licenses…</p>;

  if (licenses.length === 0) {
    return (
      <div className={styles.list}>
        {redeemForm}
        <EmptyState
          icon="library"
          title="No licenses yet"
          text="Your license keys and renewal dates will appear here after your first purchase."
          actionLabel="Browse the marketplace"
          actionHref="/catalog"
        />
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {redeemForm}
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
            {license.expires_at && <span>Expires {formatDate(license.expires_at)}</span>}
            {license.seats > 1 && (
              <span>
                {license.machines.filter((m) => m.status !== "released").length} of {license.seats} seats active
              </span>
            )}
          </div>

          {license.machines.length > 0 && (
            <div className={styles.machines}>
              {license.machines.map((machine) => (
                <div key={machine.id} className={styles.machine}>
                  <Icon name="windows" size={14} className={styles.machineIcon} />
                  <span className={styles.fingerprint}>{machine.fingerprint_preview}</span>
                  <span className={styles.lastSeen}>Last seen {formatDate(machine.last_seen_at)}</span>
                  <Pill tone={machineTone(machine.status)}>{machine.status}</Pill>
                </div>
              ))}
              <p className={styles.hint}>
                Each seat activates on one device, once. Installing on a different machine? Contact support.
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
