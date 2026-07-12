import { Icon, type IconName } from "@/components/Icon/Icon";
import type { KeyFeature } from "@/lib/types";

import styles from "./KeyFeatures.module.css";

const ALLOWED: IconName[] = [
  "broom", "eye", "document", "layers", "hash", "grid", "workflow",
  "database", "chart", "share", "refresh", "bolt",
];

function iconFor(name: string): IconName {
  return (ALLOWED.includes(name as IconName) ? name : "check-circle") as IconName;
}

export function KeyFeatures({ features }: { features: KeyFeature[] }) {
  if (!features.length) return null;
  return (
    <div className={styles.wrap}>
      <h3 className={styles.heading}>Key Features</h3>
      <ul className={styles.list}>
        {features.map((f) => (
          <li key={f.id} className={styles.item}>
            <span className={styles.icon}>
              <Icon name={iconFor(f.icon)} size={24} />
            </span>
            <div>
              <p className={styles.title}>{f.title}</p>
              {f.description && <p className={styles.desc}>{f.description}</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
