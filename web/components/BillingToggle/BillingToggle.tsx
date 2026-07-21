import styles from "./BillingToggle.module.css";

/** A Monthly/Yearly segmented switch with a sliding highlight and an
 * optional "Save N%" badge on the Yearly option — the common SaaS pricing
 * pattern for nudging buyers toward the better-value annual plan. */
export function BillingToggle({
  value,
  onChange,
  yearlySavingsPercent,
}: {
  value: "monthly" | "yearly";
  onChange: (value: "monthly" | "yearly") => void;
  yearlySavingsPercent: number | null;
}) {
  return (
    <div className={styles.toggle} role="tablist" aria-label="Billing interval">
      <span className={`${styles.thumb} ${value === "yearly" ? styles.thumbYearly : ""}`} aria-hidden="true" />
      <button
        type="button"
        role="tab"
        aria-selected={value === "monthly"}
        className={`${styles.option} ${value === "monthly" ? styles.optionActive : ""}`}
        onClick={() => onChange("monthly")}
      >
        Monthly
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === "yearly"}
        className={`${styles.option} ${value === "yearly" ? styles.optionActive : ""}`}
        onClick={() => onChange("yearly")}
      >
        Yearly
        {yearlySavingsPercent != null && <span className={styles.badge}>Save {yearlySavingsPercent}%</span>}
      </button>
    </div>
  );
}
