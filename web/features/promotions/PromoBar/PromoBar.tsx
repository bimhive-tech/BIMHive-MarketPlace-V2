"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { padUnit, useCountdown } from "@/features/promotions/useCountdown";
import type { PromotionBanner } from "@/lib/types";

import styles from "./PromoBar.module.css";

// Dismissal lives in sessionStorage, not localStorage, on purpose: closing the
// bar should stop it nagging for this visit without permanently hiding a
// limited-time offer the customer may want on their next one.
const DISMISSED_KEY = "bimhive:promo-dismissed";

/**
 * The countdown strip above the nav: what's on offer and how long is left.
 *
 * Fetched client-side rather than as layout data so it never runs during
 * `next build`'s prerender pass — this sits on every page, and the Django API
 * isn't reachable at that point in the Docker build (same reason as
 * SolutionsPanel).
 */
export function PromoBar() {
  const [promotion, setPromotion] = useState<PromotionBanner | null>(null);
  const [dismissedId, setDismissedId] = useState<string | null>(null);
  const countdown = useCountdown(promotion?.ends_at);

  useEffect(() => {
    setDismissedId(sessionStorage.getItem(DISMISSED_KEY));
    fetch("/api/promotions/banner")
      .then((res) => res.json())
      .then((body) => setPromotion(body?.promotion ?? null))
      .catch(() => setPromotion(null));
  }, []);

  if (!promotion || dismissedId === String(promotion.id)) return null;
  // Nothing until the first client tick (see useCountdown), then nothing again
  // once the clock runs out — at which point the server has already stopped
  // discounting, so leaving the bar up would advertise a price that's gone.
  if (!countdown || countdown.expired) return null;

  function dismiss() {
    if (!promotion) return;
    sessionStorage.setItem(DISMISSED_KEY, String(promotion.id));
    setDismissedId(String(promotion.id));
  }

  return (
    <aside className={styles.bar} aria-label="Limited-time offer">
      <div className={`container ${styles.inner}`}>
        <span className={styles.badge}>{promotion.badge_label}</span>

        <div className={styles.copy}>
          {/* Structural, not part of the free-text headline — guarantees the
              discount and the plan it applies to are always stated correctly,
              regardless of how staff word the headline itself. */}
          <p className={styles.discountLine}>
            <strong>{promotion.discount_percent}% off</strong> {promotion.plan_name}
          </p>
          <p className={styles.headline}>{promotion.headline}</p>
        </div>

        <div className={styles.clock}>
          {countdown.days > 0 && <TimeUnit value={countdown.days} label="days" />}
          <TimeUnit value={countdown.hours} label="hours" />
          <TimeUnit value={countdown.minutes} label="mins" />
          <TimeUnit value={countdown.seconds} label="secs" />
        </div>

        {/* Always links somewhere useful — /membership by default — since
            this bar only ever advertises a plan. */}
        <Link href={promotion.cta_url || "/membership"} className={styles.cta}>
          {promotion.cta_label || "View Plan"}
        </Link>

        <button type="button" className={styles.close} onClick={dismiss} aria-label="Dismiss this offer">
          <Icon name="x" size={16} />
        </button>
      </div>
    </aside>
  );
}

function TimeUnit({ value, label }: { value: number; label: string }) {
  return (
    <span className={styles.unit}>
      <span className={styles.value}>{padUnit(value)}</span>
      <span className={styles.unitLabel}>{label}</span>
    </span>
  );
}
