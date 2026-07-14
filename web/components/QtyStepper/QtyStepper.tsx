import styles from "./QtyStepper.module.css";

interface QtyStepperProps {
  qty: number;
  onDecrease: () => void;
  onIncrease: () => void;
  ariaLabel: string;
  /** "full" is the wide BuyBox layout; "compact" fits a product card's footer row. */
  variant?: "full" | "compact";
}

/** The +/- control shown in place of "Add to Cart" once a product is already in the cart. */
export function QtyStepper({ qty, onDecrease, onIncrease, ariaLabel, variant = "full" }: QtyStepperProps) {
  return (
    <div className={`${styles.stepper} ${styles[variant]}`} role="group" aria-label={ariaLabel}>
      <button type="button" className={styles.btn} aria-label="Decrease quantity" onClick={onDecrease}>
        −
      </button>
      <span className={styles.value}>{qty}</span>
      <button type="button" className={styles.btn} aria-label="Increase quantity" onClick={onIncrease}>
        +
      </button>
    </div>
  );
}
