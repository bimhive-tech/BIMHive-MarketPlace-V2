"use client";

import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { formatPrice } from "@/config/site";
import { AccountApiError, startMembershipCheckout } from "@/lib/accountApi";
import type { MembershipPlan, User } from "@/lib/types";

import styles from "./PlanCard.module.css";

interface PlanCardProps {
  plan: MembershipPlan;
  interval: "monthly" | "yearly";
  /** undefined while the session is still loading, null when signed out. */
  user: User | null | undefined;
  /** Slug of the plan the viewer is already on, if any. */
  currentPlanSlug?: string;
}

export function PlanCard({ plan, interval, user, currentPlanSlug }: PlanCardProps) {
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  const price = interval === "yearly" ? plan.yearly_price : plan.monthly_price;
  const isCurrent = currentPlanSlug === plan.slug;
  const unavailable = price == null;

  async function handleSubscribe() {
    setError("");
    setStarting(true);
    try {
      const { checkoutUrl } = await startMembershipCheckout(plan.slug, interval);
      window.location.href = checkoutUrl;
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't start checkout.");
      setStarting(false);
    }
  }

  return (
    <article className={`${styles.card} ${plan.is_featured ? styles.featured : ""}`}>
      {plan.is_featured && <span className={styles.ribbon}>Most popular</span>}

      <h2 className={styles.name}>{plan.name}</h2>
      {plan.tagline && <p className={styles.tagline}>{plan.tagline}</p>}

      <p className={styles.price}>
        {unavailable ? (
          <span className={styles.unavailable}>Not sold {interval}</span>
        ) : (
          <>
            <span className={styles.amount}>{formatPrice(price, plan.currency)}</span>
            <span className={styles.interval}>/{interval === "yearly" ? "yr" : "mo"}</span>
          </>
        )}
      </p>
      {interval === "yearly" && plan.yearly_savings_percent !== null && (
        <p className={styles.saving}>Save {plan.yearly_savings_percent}% vs. monthly</p>
      )}

      <ul className={styles.perks}>
        <Perk>
          <strong>{plan.product_count}</strong> product{plan.product_count === 1 ? "" : "s"} included
        </Perk>
        <Perk>One universal license key for all of them</Perk>
        <Perk>
          Up to <strong>{plan.seats_per_product}</strong> machines per product
        </Perk>
        <Perk>New releases added to your plan automatically</Perk>
        <Perk>Cancel any time</Perk>
      </ul>

      {plan.description && <p className={styles.description}>{plan.description}</p>}

      {error && <p className={styles.error}>{error}</p>}

      {isCurrent ? (
        <Button href="/account/membership" variant="secondary" fullWidth size="lg">
          Your current plan
        </Button>
      ) : user === null ? (
        <Button href="/login?next=/membership" fullWidth size="lg">
          Sign in to subscribe
        </Button>
      ) : (
        <Button
          fullWidth
          size="lg"
          onClick={handleSubscribe}
          disabled={starting || unavailable || user === undefined}
          variant={plan.is_featured ? "primary" : "secondary"}
        >
          {starting ? "Starting checkout…" : `Get ${plan.name}`}
        </Button>
      )}
    </article>
  );
}

function Perk({ children }: { children: React.ReactNode }) {
  return (
    <li className={styles.perk}>
      <Icon name="check-circle" size={18} className={styles.perkIcon} />
      <span>{children}</span>
    </li>
  );
}
