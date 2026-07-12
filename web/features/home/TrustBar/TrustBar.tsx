import { Icon, type IconName } from "@/components/Icon/Icon";
import { TRUST_BADGES } from "@/config/site";

import styles from "./TrustBar.module.css";

export function TrustBar() {
  return (
    <section className={styles.bar} aria-label="Why shop with us">
      <div className={`container ${styles.inner}`}>
        {TRUST_BADGES.map((badge) => (
          <div key={badge.title} className={styles.badge}>
            <Icon name={badge.icon as IconName} size={26} className={styles.icon} />
            <div>
              <p className={styles.title}>{badge.title}</p>
              <p className={styles.subtitle}>{badge.subtitle}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
