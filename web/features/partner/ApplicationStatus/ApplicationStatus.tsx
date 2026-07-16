import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import type { User } from "@/lib/types";

import styles from "./ApplicationStatus.module.css";

/** Shown in place of the dashboard/products/sales content until a seller
 * application is approved — Partner Profile stays reachable via its own nav
 * item and the link here, so the applicant can always see why and fix their
 * info (see web/app/partner-portal/layout.tsx for the routing). */
export function ApplicationStatus({ partner }: { partner: NonNullable<User["partner"]> }) {
  const pending = partner.status === "pending";

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <Icon name={pending ? "shield" : "x"} size={32} className={styles.icon} />
        <Pill tone={pending ? "warning" : "error"}>{pending ? "Pending Review" : "Rejected"}</Pill>
        <h1 className={styles.title}>
          {pending ? "Your seller application is under review" : "Your seller application was rejected"}
        </h1>
        <p className={styles.text}>
          {pending
            ? "BIMHive staff will review your application soon — you'll get full partner dashboard access once it's approved."
            : partner.rejection_note || "No reason was given."}
        </p>
        <Link href="/partner-portal/profile" className={styles.link}>
          View &amp; edit your application
          <Icon name="arrow-right" size={14} />
        </Link>
      </div>
    </div>
  );
}
