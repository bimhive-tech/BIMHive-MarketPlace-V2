import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { ApplicationStatus } from "@/features/partner/ApplicationStatus/ApplicationStatus";
import type { User } from "@/lib/types";

import styles from "./SellerTab.module.css";

/** Content for the account Profile page's "Become a Seller"/"Partner" tab —
 * branches on the user's partner-application state. Pending/rejected reuse
 * ApplicationStatus (the same status card shown inside the partner portal
 * itself) rather than duplicating that copy here. */
export function SellerTab({ user }: { user: User }) {
  const partner = user.partner;

  if (!partner) {
    return (
      <div className={styles.panel}>
        <span className={styles.icon}>
          <Icon name="bolt" size={28} />
        </span>
        <h2 className={styles.title}>Become a Seller</h2>
        <p className={styles.text}>
          Sell your Revit plugins, Dynamo scripts, and BIM tools to thousands of AEC professionals on
          BIMHIVE. Every submission is reviewed before it goes live.
        </p>
        <Button href="/sell">Get Started</Button>
      </div>
    );
  }

  if (partner.status !== "approved") {
    return <ApplicationStatus partner={partner} />;
  }

  return (
    <div className={styles.panel}>
      <span className={styles.icon}>
        <Icon name="check-circle" size={28} />
      </span>
      <h2 className={styles.title}>{partner.name}</h2>
      <p className={styles.text}>
        You&apos;re an approved BIMHIVE partner. Manage your products and track your sales from the
        partner dashboard.
      </p>
      <Button href="/partner-portal">Open Partner Dashboard</Button>
    </div>
  );
}
