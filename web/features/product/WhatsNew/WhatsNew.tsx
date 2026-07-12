import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import type { ChangelogEntry } from "@/lib/types";

import styles from "./WhatsNew.module.css";

export function WhatsNew({ changelog }: { changelog: ChangelogEntry[] }) {
  const latest = changelog[0];
  if (!latest) return null;
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.title}>What&apos;s New in v{latest.version}</h3>
        <Link href="#changelog" className={styles.link}>
          View full changelog
          <Icon name="arrow-right" size={14} />
        </Link>
      </div>
      <ul className={styles.list}>
        {latest.notes.map((note, i) => (
          <li key={i} className={styles.item}>
            <Icon name="check-circle" size={18} className={styles.check} />
            {note}
          </li>
        ))}
      </ul>
    </div>
  );
}
