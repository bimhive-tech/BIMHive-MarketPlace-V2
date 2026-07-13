import { Icon } from "@/components/Icon/Icon";
import type { AdminCompatibilityItem } from "@/lib/adminApi";

import styles from "./ProductForm.module.css";

interface CompatibilityTabProps {
  compatibility: AdminCompatibilityItem[];
  setCompatibility: (updater: (list: AdminCompatibilityItem[]) => AdminCompatibilityItem[]) => void;
}

export function CompatibilityTab({ compatibility, setCompatibility }: CompatibilityTabProps) {
  function update(i: number, patch: Partial<AdminCompatibilityItem>) {
    setCompatibility((list) => list.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));
  }

  return (
    <div className={styles.panel}>
      <p className={styles.label}>Supported Environments</p>
      <p className={styles.hint}>Shown on the Compatibility tab of the product page (e.g. Revit, Platform, Language).</p>

      {compatibility.map((item, i) => (
        <div key={i} className={styles.compatRow}>
          <input
            className={styles.input}
            value={item.label}
            onChange={(e) => update(i, { label: e.target.value })}
            placeholder="Label, e.g. Revit"
          />
          <input
            className={styles.input}
            value={item.value}
            onChange={(e) => update(i, { value: e.target.value })}
            placeholder="Value, e.g. 2023–2025"
          />
          <button
            className={styles.iconBtn}
            aria-label="Remove row"
            onClick={() => setCompatibility((list) => list.filter((_, idx) => idx !== i))}
          >
            <Icon name="trash" size={16} />
          </button>
        </div>
      ))}

      <button
        className={styles.addBtn}
        onClick={() => setCompatibility((list) => [...list, { label: "", value: "", sort_order: list.length }])}
      >
        <Icon name="plus" size={14} /> Add Row
      </button>
    </div>
  );
}
