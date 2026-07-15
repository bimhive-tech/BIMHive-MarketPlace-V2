import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { RESOURCE_LINKS } from "@/config/site";

import styles from "./HeaderPanels.module.css";

export function ResourcesPanel() {
  return (
    <div className={styles.columns}>
      <div className={styles.column}>
        <p className={styles.heading}>Resources</p>
        <ul className={styles.list}>
          {RESOURCE_LINKS.map((item) =>
            item.href ? (
              <li key={item.title}>
                <Link href={item.href} className={styles.link}>
                  <Icon name={item.icon} size={18} className={styles.icon} />
                  <span>
                    <span className={styles.linkTitle}>{item.title}</span>
                    <span className={styles.linkMeta}>{item.description}</span>
                  </span>
                </Link>
              </li>
            ) : (
              <li key={item.title}>
                <span className={`${styles.link} ${styles.linkDisabled}`}>
                  <Icon name={item.icon} size={18} className={styles.icon} />
                  <span>
                    <span className={styles.linkTitle}>
                      {item.title}
                      <span className={styles.soon}>Soon</span>
                    </span>
                    <span className={styles.linkMeta}>{item.description}</span>
                  </span>
                </span>
              </li>
            ),
          )}
        </ul>
      </div>

      <div className={styles.highlight}>
        <Icon name="document" size={28} className={styles.highlightIcon} />
        <p className={styles.highlightTitle}>Looking for setup help?</p>
        <p className={styles.highlightText}>Start with the documentation for the product you're using.</p>
        <Link href="/docs" className={styles.highlightLink}>
          Browse Documentation
          <Icon name="arrow-right" size={14} />
        </Link>
      </div>
    </div>
  );
}
