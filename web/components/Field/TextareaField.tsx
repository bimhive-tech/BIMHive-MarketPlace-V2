import type { TextareaHTMLAttributes } from "react";

import styles from "./Field.module.css";

interface TextareaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
  error?: string;
}

/** Field's multi-line sibling — same label, hint and error treatment. */
export function TextareaField({ label, hint, error, id, rows = 4, ...props }: TextareaFieldProps) {
  const inputId = id || props.name;
  return (
    <div className={styles.field}>
      <label htmlFor={inputId} className={styles.label}>
        {label}
      </label>
      <textarea
        id={inputId}
        rows={rows}
        className={`${styles.input} ${styles.textarea} ${error ? styles.inputError : ""}`}
        {...props}
      />
      {error ? (
        <span className={styles.error}>{error}</span>
      ) : hint ? (
        <span className={styles.hint}>{hint}</span>
      ) : null}
    </div>
  );
}
