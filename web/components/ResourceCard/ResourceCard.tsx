import Link from "next/link";

import { Icon, type IconName } from "@/components/Icon/Icon";

import styles from "./ResourceCard.module.css";

interface ResourceCardProps {
  icon: IconName;
  title: string;
  description: string;
  /** null renders the card as a disabled "coming soon" state instead of a link. */
  href: string | null;
}

export function ResourceCard({ icon, title, description, href }: ResourceCardProps) {
  const content = (
    <>
      <span className={styles.icon}>
        <Icon name={icon} size={24} />
      </span>
      <span className={styles.title}>
        {title}
        {!href && <span className={styles.soon}>Soon</span>}
      </span>
      <span className={styles.desc}>{description}</span>
    </>
  );

  if (!href) {
    return <div className={`${styles.card} ${styles.cardDisabled}`}>{content}</div>;
  }

  return (
    <Link href={href} className={styles.card}>
      {content}
    </Link>
  );
}
