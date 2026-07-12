import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";

import styles from "./SectionHeader.module.css";

interface SectionHeaderProps {
  title: string;
  viewAllHref?: string;
  viewAllLabel?: string;
}

export function SectionHeader({ title, viewAllHref, viewAllLabel = "View all" }: SectionHeaderProps) {
  return (
    <div className={styles.header}>
      <h2 className={styles.title}>{title}</h2>
      {viewAllHref && (
        <Link href={viewAllHref} className={styles.viewAll}>
          {viewAllLabel}
          <Icon name="arrow-right" size={16} />
        </Link>
      )}
    </div>
  );
}
