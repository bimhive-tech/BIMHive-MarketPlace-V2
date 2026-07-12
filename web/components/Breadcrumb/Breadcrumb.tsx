import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";

import styles from "./Breadcrumb.module.css";

export interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav className={styles.breadcrumb} aria-label="Breadcrumb">
      {items.map((item, i) => {
        const isLast = i === items.length - 1;
        return (
          <span key={item.label} className={styles.crumb}>
            {item.href && !isLast ? (
              <Link href={item.href} className={styles.link}>
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? styles.current : styles.link}>{item.label}</span>
            )}
            {!isLast && <Icon name="chevron-right" size={14} className={styles.sep} />}
          </span>
        );
      })}
    </nav>
  );
}
