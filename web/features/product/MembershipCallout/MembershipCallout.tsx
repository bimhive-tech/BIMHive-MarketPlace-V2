import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { formatPrice } from "@/config/site";
import type { ProductDetail } from "@/lib/types";

import styles from "./MembershipCallout.module.css";

/**
 * The All-Access cross-sell inside the buy box — the moment a customer is
 * looking at one price is exactly when "or get this and everything else for
 * £X/mo" lands.
 *
 * Renders nothing for a product outside All-Access, and flips to a plain
 * confirmation for someone whose plan already covers it (no point selling them
 * what they have).
 */
export function MembershipCallout({ product }: { product: ProductDetail }) {
  const { membership } = product;
  if (!membership) return null;

  if (membership.included_in_my_plan) {
    return (
      <div className={`${styles.callout} ${styles.owned}`}>
        <Icon name="check-circle" size={20} className={styles.icon} />
        <div>
          <p className={styles.title}>Included in your {membership.plan_name} plan</p>
          <p className={styles.text}>
            Activate it with your universal key —{" "}
            <Link href="/account/membership" className={styles.link}>
              find it on your account
            </Link>
            .
          </p>
        </div>
      </div>
    );
  }

  return (
    <Link href="/membership" className={styles.callout}>
      <Icon name="wallet" size={20} className={styles.icon} />
      <div>
        <p className={styles.title}>
          Or get it with {membership.plan_name}
          {membership.monthly_price && <> from {formatPrice(membership.monthly_price)}/mo</>}
        </p>
        <p className={styles.text}>
          One subscription unlocks this and every other product in the plan.
        </p>
      </div>
      <Icon name="chevron-right" size={16} className={styles.chevron} />
    </Link>
  );
}
