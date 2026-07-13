import Link from "next/link";

import { Icon, type IconName } from "@/components/Icon/Icon";

import styles from "./QuickLinksCard.module.css";

const LINKS: { icon: IconName; title: string; text: string; href: string }[] = [
  { icon: "library", title: "Manage Licenses", text: "View and manage your active licenses", href: "/account/licenses" },
  { icon: "refresh", title: "Manage Subscriptions", text: "View and manage your subscriptions", href: "/account/subscriptions" },
  { icon: "lock", title: "Payment Methods", text: "Update your saved payment methods", href: "/account/payment-methods" },
  { icon: "document", title: "Orders & Invoices", text: "View your purchase history and invoices", href: "/account/orders" },
  { icon: "shield", title: "Security Settings", text: "Change your password and security options", href: "/account/security" },
];

export function QuickLinksCard() {
  return (
    <div className={styles.card}>
      <h2 className={styles.title}>Quick Links</h2>
      {LINKS.map((link) => (
        <Link key={link.title} href={link.href} className={styles.row}>
          <span className={styles.icon}>
            <Icon name={link.icon} size={18} />
          </span>
          <span className={styles.text}>
            <span className={styles.linkTitle}>{link.title}</span>
            <span className={styles.linkSub}>{link.text}</span>
          </span>
          <Icon name="chevron-right" size={16} className={styles.chevron} />
        </Link>
      ))}
    </div>
  );
}
