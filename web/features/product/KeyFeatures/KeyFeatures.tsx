"use client";

import { useState } from "react";

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

interface KeyFeaturesProps {
  features: KeyFeature[];
  /** Caps the list to this many items with a Read more/Show less toggle,
   * mirroring ExpandableText — omit to always render the full list (the
   * standalone Features tab wants everything visible). */
  previewCount?: number;
}

export function KeyFeatures({ features, previewCount }: KeyFeaturesProps) {
  const [expanded, setExpanded] = useState(false);
  if (!features.length) return null;

  const collapsible = previewCount != null && features.length > previewCount;
  const visible = collapsible && !expanded ? features.slice(0, previewCount) : features;

  return (
    <div className={styles.wrap}>
      <h3 className={styles.heading}>Key Features</h3>
      <ul className={styles.list}>
        {visible.map((f) => (
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
      {collapsible && (
        <button type="button" className={styles.toggle} onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Show less" : `Read more (${features.length - previewCount!} more)`}
        </button>
      )}
    </div>
  );
}
