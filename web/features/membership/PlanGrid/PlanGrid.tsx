"use client";

import { useEffect, useState } from "react";

import { BillingToggle } from "@/components/BillingToggle/BillingToggle";
import { getAccountMembership } from "@/lib/accountApi";
import { me } from "@/lib/auth";
import type { MembershipPlan, User } from "@/lib/types";
import { PlanCard } from "@/features/membership/PlanCard/PlanCard";

import styles from "./PlanGrid.module.css";

/**
 * The plan chooser on /membership.
 *
 * Client-side because the billing toggle, the session, and "you're already on
 * this plan" all only matter in the browser — the page itself stays a server
 * component so the plans render and index without JavaScript.
 */
export function PlanGrid({ plans }: { plans: MembershipPlan[] }) {
  // Yearly first: it's the better-value option, same default as the product
  // buy box.
  const [interval, setInterval] = useState<"monthly" | "yearly">("yearly");
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [currentPlanSlug, setCurrentPlanSlug] = useState<string | undefined>();

  useEffect(() => {
    me().then((signedInUser) => {
      setUser(signedInUser);
      if (!signedInUser) return;
      getAccountMembership()
        .then(({ membership }) => {
          if (membership?.is_usable) setCurrentPlanSlug(membership.plan_slug);
        })
        .catch(() => undefined);
    });
  }, []);

  // The biggest saving across the plans, so the toggle's badge reflects the
  // best deal on offer rather than an arbitrary plan's.
  const bestSaving = plans.reduce<number | null>(
    (best, plan) =>
      plan.yearly_savings_percent !== null && (best === null || plan.yearly_savings_percent > best)
        ? plan.yearly_savings_percent
        : best,
    null,
  );

  return (
    <>
      <div className={styles.toggleRow}>
        <BillingToggle value={interval} onChange={setInterval} yearlySavingsPercent={bestSaving} />
      </div>

      <div className={styles.grid}>
        {plans.map((plan) => (
          <PlanCard
            key={plan.id}
            plan={plan}
            interval={interval}
            user={user}
            currentPlanSlug={currentPlanSlug}
          />
        ))}
      </div>
    </>
  );
}
