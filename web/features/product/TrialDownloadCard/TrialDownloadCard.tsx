"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { me } from "@/lib/auth";
import type { ProductDetail, User } from "@/lib/types";

import styles from "./TrialDownloadCard.module.css";

function formatTrialLength(days: number, hours: number, minutes: number): string {
  const parts: string[] = [];
  if (days > 0) parts.push(`${days} day${days === 1 ? "" : "s"}`);
  if (hours > 0) parts.push(`${hours} hour${hours === 1 ? "" : "s"}`);
  if (minutes > 0) parts.push(`${minutes} minute${minutes === 1 ? "" : "s"}`);
  return parts.join(", ");
}

/** Shown on a plugin product's buy box when staff have configured a trial
 * length above zero (Product.has_trial). Downloads the same on-demand .exe
 * the paid flow builds, minus the license-key zip wrapper — there's no
 * purchase yet, so nothing to attach. The plugin's own first activation
 * call (no license key) is what actually starts the trial clock; this
 * button just gets the installer into the customer's hands. Uses fetch+blob
 * rather than a plain link for the same reason ProductRowActions does: a
 * failed build would otherwise "download" a JSON error body. */
export function TrialDownloadCard({ product }: { product: ProductDetail }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [year, setYear] = useState(product.trial_builds[0]?.revit_year ?? "");
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    me().then(setUser);
  }, []);

  if (product.trial_builds.length === 0) return null;

  const build = product.trial_builds.find((b) => b.revit_year === year) ?? product.trial_builds[0];
  const trialLength = formatTrialLength(product.default_trial_days, product.default_trial_hours, product.default_trial_minutes);

  async function onDownload() {
    if (!build) return;
    setError("");
    setDownloading(true);
    try {
      const res = await fetch(`/api/account/downloads/plugin-builds/${build.id}/trial`, { credentials: "include" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}) as Record<string, string>);
        throw new Error(body.detail || "Could not generate the trial installer.");
      }
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") || "";
      const filename = disposition.match(/filename="?([^"]+)"?/)?.[1] || `trial-${build.revit_year}.exe`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate the trial installer.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <Icon name="clock" size={18} className={styles.icon} />
        <div>
          <p className={styles.title}>Try it free</p>
          <p className={styles.sub}>{trialLength} trial — no purchase needed to start</p>
        </div>
      </div>

      {product.trial_builds.length > 1 && (
        <select
          className={styles.select}
          value={year}
          onChange={(e) => setYear(e.target.value)}
          aria-label="Revit year for the trial download"
        >
          {product.trial_builds.map((b) => (
            <option key={b.id} value={b.revit_year}>
              Revit {b.revit_year}
            </option>
          ))}
        </select>
      )}

      {error && <p className={styles.error}>{error}</p>}

      {user === null ? (
        <Button size="md" variant="secondary" fullWidth href={`/login?next=/products/${product.slug}`}>
          Log in to download the trial
        </Button>
      ) : (
        <Button
          size="md"
          variant="secondary"
          fullWidth
          onClick={onDownload}
          disabled={downloading || user === undefined || !build}
        >
          <Icon name="download" size={16} />
          {downloading ? "Preparing…" : "Download Trial"}
        </Button>
      )}
    </div>
  );
}
