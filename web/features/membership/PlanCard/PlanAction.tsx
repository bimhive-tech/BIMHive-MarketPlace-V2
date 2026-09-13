"use client";

import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { AccountApiError, startMembershipCheckout } from "@/lib/accountApi";
import type { MembershipPlan, User } from "@/lib/types";
import { PlanRequestModal } from "@/features/membership/PlanRequestModal/PlanRequestModal";

import styles from "./PlanCard.module.css";

interface PlanActionProps {
  plan: MembershipPlan;
  interval: "monthly" | "yearly";
  /** undefined while the session is still loading, null when signed out. */
  user: User | null | undefined;
  isCurrent: boolean;
}

/** The card's button, which depends on how the plan is joined (see
 * MembershipPlan.Enrollment): browse for the everyone-has-it tier, a
 * "Contact us" form for a by-request tier, or checkout for the rest. */
export function PlanAction({ plan, interval, user, isCurrent }: PlanActionProps) {
  const [starting, setStarting] = useState(false);
  const [requestOpen, setRequestOpen] = useState(false);
  const [error, setError] = useState("");
  const variant = plan.is_featured ? "primary" : "secondary";

  if (plan.enrollment === "included") {
    return user === null ? (
      <Button href="/signup" fullWidth size="lg" variant={variant}>
        Create a free account
      </Button>
    ) : (
      <Button href="/catalog" fullWidth size="lg" variant={variant}>
        Browse plugins
      </Button>
    );
  }

  if (plan.enrollment === "request") {
    if (user === null) {
      return (
        <Button href="/login?next=/membership" fullWidth size="lg" variant={variant}>
          Sign in to contact us
        </Button>
      );
    }
    return (
      <>
        <Button
          fullWidth
          size="lg"
          variant={variant}
          disabled={user === undefined}
          onClick={() => setRequestOpen(true)}
        >
          Contact us
        </Button>
        <PlanRequestModal plan={plan} open={requestOpen} onClose={() => setRequestOpen(false)} />
      </>
    );
  }

  if (isCurrent) {
    return (
      <Button href="/account/membership" variant="secondary" fullWidth size="lg">
        Your current plan
      </Button>
    );
  }
  if (user === null) {
    return (
      <Button href="/login?next=/membership" fullWidth size="lg">
        Sign in to join
      </Button>
    );
  }

  const listPrice = interval === "yearly" ? plan.yearly_price : plan.monthly_price;
  const salePrice = interval === "yearly" ? plan.promotion?.yearly_price : plan.promotion?.monthly_price;
  const isFree = Number(salePrice ?? listPrice ?? 0) === 0;
  const idleLabel = isFree ? `Join ${plan.name} free` : `Get ${plan.name}`;
  const busyLabel = isFree ? "Joining…" : "Starting checkout…";

  async function handleJoin() {
    setError("");
    setStarting(true);
    try {
      // A paid plan returns Paymob's URL; a $0 one is activated on the spot
      // and returns the account page instead — the redirect is the same.
      const { checkoutUrl } = await startMembershipCheckout(plan.slug, interval);
      window.location.href = checkoutUrl;
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't start checkout.");
      setStarting(false);
    }
  }

  return (
    <>
      {error && <p className={styles.error}>{error}</p>}
      <Button
        fullWidth
        size="lg"
        onClick={handleJoin}
        disabled={starting || listPrice == null || user === undefined}
        variant={variant}
      >
        {starting ? busyLabel : idleLabel}
      </Button>
    </>
  );
}
