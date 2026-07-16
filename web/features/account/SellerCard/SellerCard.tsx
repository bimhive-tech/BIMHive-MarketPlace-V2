import Link from "next/link";

import { Icon, type IconName } from "@/components/Icon/Icon";
import type { User } from "@/lib/types";

import styles from "./SellerCard.module.css";

function contentFor(partner: User["partner"]): { icon: IconName; title: string; text: string; href: string } {
  if (!partner) {
    return {
      icon: "bolt",
      title: "Become a Seller",
      text: "Sell your Revit plugins, scripts, and templates on BIMHIVE",
      href: "/sell",
    };
  }
  if (partner.status === "pending") {
    return {
      icon: "bell",
      title: "Application Under Review",
      text: "We're reviewing your seller application",
      href: "/partner-portal/profile",
    };
  }
  if (partner.status === "rejected") {
    return {
      icon: "lock",
      title: "Application Rejected",
      text: "See what to fix and re-apply",
      href: "/partner-portal/profile",
    };
  }
  return {
    icon: "grid",
    title: "Partner Dashboard",
    text: "Monitor your sales and manage your products",
    href: "/partner-portal",
  };
}

export function SellerCard({ user }: { user: User }) {
  const { icon, title, text, href } = contentFor(user.partner);
  return (
    <Link href={href} className={styles.card}>
      <span className={styles.icon}>
        <Icon name={icon} size={20} />
      </span>
      <span className={styles.text}>
        <span className={styles.cardTitle}>{title}</span>
        <span className={styles.cardSub}>{text}</span>
      </span>
      <Icon name="chevron-right" size={16} className={styles.chevron} />
    </Link>
  );
}
