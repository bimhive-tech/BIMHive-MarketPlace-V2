"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { ProductCard } from "@/components/ProductCard/ProductCard";
import { formatPrice } from "@/config/site";
import {
  AccountApiError,
  cancelMembership,
  getAccountMembership,
  type AccountMembershipData,
} from "@/lib/accountApi";

import styles from "./MembershipPanel.module.css";

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  active: "success",
  pending: "warning",
  expired: "error",
  cancelled: "neutral",
  refunded: "neutral",
  revoked: "error",
};

export function MembershipPanel() {
  const [data, setData] = useState<AccountMembershipData | null | undefined>(undefined);
  const [copied, setCopied] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getAccountMembership()
      .then(setData)
      .catch(() => setData(null));
  }, []);

  async function onCopyKey(key: string) {
    try {
      await navigator.clipboard.writeText(key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Couldn't copy — select the key and copy it manually.");
    }
  }

  async function onCancel() {
    if (!window.confirm("Cancel your membership? The universal key stops working right away.")) return;
    setError("");
    setCancelling(true);
    try {
      const membership = await cancelMembership();
      setData((current) => (current ? { membership, products: [] } : current));
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't cancel your membership.");
    } finally {
      setCancelling(false);
    }
  }

  if (data === undefined) return <p className={styles.state}>Loading your membership…</p>;

  const membership = data?.membership ?? null;
  if (!membership) {
    return (
      <EmptyState
        icon="wallet"
        title="You're not on All-Access"
        text="One subscription and one universal key unlock the products in your plan, instead of buying them one at a time."
        actionLabel="See the plans"
        actionHref="/membership"
      />
    );
  }

  return (
    <div className={styles.panel}>
      <div className={styles.card}>
        <div className={styles.cardHead}>
          <div>
            <h2 className={styles.planName}>{membership.plan_name}</h2>
            <p className={styles.planMeta}>
              {formatPrice(membership.amount, membership.currency)}
              {membership.billing_period === "yearly" ? "/yr" : "/mo"}
            </p>
          </div>
          <Pill tone={STATUS_TONE[membership.display_status] ?? "neutral"}>
            {membership.display_status}
          </Pill>
        </div>

        {membership.is_usable ? (
          <>
            <div className={styles.keyBlock}>
              <p className={styles.keyLabel}>Your universal license key</p>
              <p className={styles.keyHint}>
                Paste this into any product your plan covers — it&apos;s the same key for all of them.
              </p>
              <div className={styles.keyRow}>
                <code className={styles.key}>{membership.license_key}</code>
                <button
                  type="button"
                  className={styles.copyBtn}
                  aria-label="Copy universal license key"
                  onClick={() => onCopyKey(membership.license_key)}
                >
                  <Icon name={copied ? "check" : "copy"} size={14} />
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
            </div>

            <dl className={styles.facts}>
              <Fact label="Machines per product">{membership.seats_per_product}</Fact>
              <Fact label="Renews">
                {membership.expires_at
                  ? new Date(membership.expires_at).toLocaleDateString()
                  : "Never — this membership doesn't expire"}
              </Fact>
              <Fact label="Products unlocked">{data?.products.length ?? 0}</Fact>
            </dl>

            {error && <p className={styles.error}>{error}</p>}

            <div className={styles.actions}>
              <Button href="/account/downloads" variant="secondary">
                <Icon name="download" size={16} />
                Go to Downloads
              </Button>
              <button type="button" className={styles.cancel} onClick={onCancel} disabled={cancelling}>
                {cancelling ? "Cancelling…" : "Cancel membership"}
              </button>
            </div>
          </>
        ) : (
          <div className={styles.endedBlock}>
            <p className={styles.endedText}>
              This membership is no longer active, so its universal key won&apos;t activate anything.
              Anything you bought outright is unaffected.
            </p>
            <Button href="/membership">Resubscribe</Button>
          </div>
        )}
      </div>

      {membership.is_usable && (data?.products.length ?? 0) > 0 && (
        <section className={styles.included}>
          <h3 className={styles.includedTitle}>What your key unlocks</h3>
          <div className={styles.grid}>
            {data?.products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className={styles.fact}>
      <dt className={styles.factLabel}>{label}</dt>
      <dd className={styles.factValue}>{children}</dd>
    </div>
  );
}
