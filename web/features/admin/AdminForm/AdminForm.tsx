"use client";

import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

import styles from "./AdminForm.module.css";

/**
 * The two-column form layout every admin editor uses. Split out because the
 * admin pages were each labelling fields their own way — some with a real
 * label, some with only a placeholder — which is why those forms read as
 * ragged. One field shape here keeps them consistent, and a wrapping <label>
 * means the control is always properly named without threading ids around.
 */
export function AdminFormGrid({ children }: { children: ReactNode }) {
  return <div className={styles.grid}>{children}</div>;
}

interface AdminFieldProps {
  label: string;
  /** Sub-label explaining what the value does. */
  hint?: string;
  /** Spans the full width instead of one column. */
  wide?: boolean;
  children: ReactNode;
}

export function AdminField({ label, hint, wide, children }: AdminFieldProps) {
  return (
    <label className={`${styles.field} ${wide ? styles.wide : ""}`}>
      <span className={styles.label}>{label}</span>
      {children}
      {hint && <span className={styles.hint}>{hint}</span>}
    </label>
  );
}

export function AdminInput({ className = "", ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...rest} className={`${styles.control} ${className}`} />;
}

export function AdminTextarea({ className = "", rows = 3, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...rest} rows={rows} className={`${styles.control} ${styles.textarea} ${className}`} />;
}

interface AdminCheckboxProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: string;
  wide?: boolean;
}

export function AdminCheckbox({ label, checked, onChange, hint, wide }: AdminCheckboxProps) {
  return (
    <label className={`${styles.checkbox} ${wide ? styles.wide : ""}`}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className={styles.checkboxText}>
        {label}
        {hint && <span className={styles.hint}>{hint}</span>}
      </span>
    </label>
  );
}
