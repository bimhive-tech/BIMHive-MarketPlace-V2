import type { ReactNode, SelectHTMLAttributes } from "react";

import styles from "./Field.module.css";

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}

/** The `<select>` counterpart to Field — same label/hint/error layout, so a
 * form mixing text inputs and dropdowns (e.g. sign-up's profession/country)
 * reads as one consistent field list. */
export function SelectField({ label, hint, error, id, children, ...props }: SelectFieldProps) {
  const selectId = id || props.name;
  return (
    <div className={styles.field}>
      <label htmlFor={selectId} className={styles.label}>
        {label}
      </label>
      <select id={selectId} className={`${styles.input} ${error ? styles.inputError : ""}`} {...props}>
        {children}
      </select>
      {error ? (
        <span className={styles.error}>{error}</span>
      ) : hint ? (
        <span className={styles.hint}>{hint}</span>
      ) : null}
    </div>
  );
}
