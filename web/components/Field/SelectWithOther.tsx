"use client";

import { useState } from "react";

import styles from "./Field.module.css";

const OTHER = "__other__";

interface SelectWithOtherProps {
  label: string;
  name: string;
  /** The curated values offered in the dropdown, before "Other" is appended. */
  options: string[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  otherPlaceholder?: string;
  hint?: string;
  error?: string;
}

/**
 * A dropdown that falls back to free text when the answer isn't on the list.
 * Picking "Other" reveals an input and the typed value is what's submitted —
 * there's no separate "other" field to reconcile downstream, so the server
 * stores one plain string either way (see Profile.university).
 *
 * Kept controlled because the reveal depends on the current selection; the
 * curated list itself comes from the backend, never hardcoded here.
 */
export function SelectWithOther({
  label,
  name,
  options,
  value,
  onChange,
  placeholder = "Select…",
  otherPlaceholder = "Type it in",
  hint,
  error,
}: SelectWithOtherProps) {
  // A value that isn't on the list can only have come from "Other" — either
  // typed just now, or loaded back from a saved profile.
  const [pickedOther, setPickedOther] = useState(() => value !== "" && !options.includes(value));

  // Until staff have curated the list there is nothing to pick, so a dropdown
  // whose only real entry is "Other" would just be a pointless extra click.
  const listIsEmpty = options.length === 0;
  const showOther = listIsEmpty || pickedOther;

  function onSelect(selected: string) {
    setPickedOther(selected === OTHER);
    onChange(selected === OTHER ? "" : selected);
  }

  return (
    <div className={styles.field}>
      <label htmlFor={name} className={styles.label}>
        {label}
      </label>

      {!listIsEmpty && (
        <select
          id={name}
          className={`${styles.input} ${error ? styles.inputError : ""}`}
          value={showOther ? OTHER : value}
          onChange={(e) => onSelect(e.target.value)}
        >
          <option value="">{placeholder}</option>
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
          <option value={OTHER}>Other</option>
        </select>
      )}

      {showOther && (
        <input
          id={listIsEmpty ? name : undefined}
          className={`${styles.input} ${styles.reveal}`}
          placeholder={otherPlaceholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-label={listIsEmpty ? undefined : `${label} — other`}
          autoFocus={pickedOther}
        />
      )}

      {error ? (
        <span className={styles.error}>{error}</span>
      ) : hint ? (
        <span className={styles.hint}>{hint}</span>
      ) : null}
    </div>
  );
}
