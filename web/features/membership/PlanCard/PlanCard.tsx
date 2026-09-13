import { Icon } from "@/components/Icon/Icon";
import type { MembershipPlan, User } from "@/lib/types";
import { PlanAction } from "@/features/membership/PlanCard/PlanAction";
import { PlanPrice, planPriceNote } from "@/features/membership/PlanCard/PlanPrice";

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
  const note = planPriceNote(plan, interval);
  const joinsOnline = plan.enrollment === "self_serve";

  return (
    <article className={`${styles.card} ${plan.is_featured ? styles.featured : ""}`}>
      {plan.is_featured && <span className={styles.ribbon}>Most popular</span>}

      <h2 className={styles.name}>{plan.name}</h2>
      {plan.tagline && <p className={styles.tagline}>{plan.tagline}</p>}

      <PlanPrice plan={plan} interval={interval} />
      {note && <p className={styles.saving}>{note}</p>}

      {/* Facts the server computes come first, then what staff wrote for the
          plan — so a checklist line can never contradict the real numbers. */}
      <ul className={styles.perks}>
        {plan.product_count > 0 && (
          <Perk>
            <strong>{plan.product_count}</strong> plugin{plan.product_count === 1 ? "" : "s"} included
          </Perk>
        )}
        {joinsOnline && <Perk>One universal license key for all of them</Perk>}
        {joinsOnline && (
          <Perk>
            Up to <strong>{plan.seats_per_product}</strong> machines per plugin
          </Perk>
        )}
        {plan.features.map((feature) => (
          <Perk key={feature}>{feature}</Perk>
        ))}
      </ul>

      {plan.description && <p className={styles.description}>{plan.description}</p>}

      <PlanAction plan={plan} interval={interval} user={user} isCurrent={currentPlanSlug === plan.slug} />
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
