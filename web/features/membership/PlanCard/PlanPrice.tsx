import { formatPrice } from "@/config/site";
import type { MembershipPlan } from "@/lib/types";

import styles from "./PlanCard.module.css";

type Interval = "monthly" | "yearly";

/** The figure a plan actually charges on `interval` right now, and the higher
 * one to strike through beside it: the list price during a promotion,
 * otherwise the plan's display-only original price. */
function planPrices(plan: MembershipPlan, interval: Interval) {
  const yearly = interval === "yearly";
  const list = yearly ? plan.yearly_price : plan.monthly_price;
  const sale = yearly ? plan.promotion?.yearly_price : plan.promotion?.monthly_price;
  const original = yearly ? plan.original_yearly_price : plan.original_monthly_price;
  const charged = sale ?? list;
  const was = sale ? list : original && Number(original) > Number(charged ?? 0) ? original : null;
  return { charged, was };
}

export function PlanPrice({ plan, interval }: { plan: MembershipPlan; interval: Interval }) {
  if (plan.enrollment === "request") {
    return (
      <p className={styles.price}>
        <span className={styles.amount}>Custom</span>
      </p>
    );
  }

  const { charged, was } = planPrices(plan, interval);
  const suffix = interval === "yearly" ? "/yr" : "/mo";

  if (charged == null && plan.enrollment === "self_serve") {
    return (
      <p className={styles.price}>
        <span className={styles.unavailable}>Not sold {interval}</span>
      </p>
    );
  }

  const isFree = charged == null || Number(charged) === 0;
  return (
    <p className={styles.price}>
      <span className={`${styles.amount} ${was ? styles.amountSale : ""}`}>
        {isFree ? "Free" : formatPrice(charged, plan.currency)}
      </span>
      {!isFree && <span className={styles.interval}>{suffix}</span>}
      {was && (
        <s className={styles.wasPrice}>
          {formatPrice(was, plan.currency)}
          {suffix}
        </s>
      )}
    </p>
  );
}

/** One line under the price explaining it: the running promotion, the yearly
 * saving, or — for a plan that's free right now but has a real price — that
 * it's free for now. Null when there's nothing to add. */
export function planPriceNote(plan: MembershipPlan, interval: Interval): string | null {
  if (plan.enrollment === "request") return "Tailored to your team";
  if (plan.promotion) return `${plan.promotion.discount_percent}% off — ${plan.promotion.headline}`;
  const { charged, was } = planPrices(plan, interval);
  if (was && Number(charged ?? 0) === 0) return "Free for now";
  if (interval === "yearly" && plan.yearly_savings_percent !== null) {
    return `Save ${plan.yearly_savings_percent}% vs. monthly`;
  }
  return null;
}
