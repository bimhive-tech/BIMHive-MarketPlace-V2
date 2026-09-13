"use client";

import { useCallback, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { Modal } from "@/components/Modal/Modal";

import styles from "./useNumberPrompt.module.css";

export interface NumberPromptOptions {
  title: string;
  message?: string;
  label: string;
  initialValue: number;
  /** Smallest whole number accepted. */
  min?: number;
  confirmLabel?: string;
}

type PendingPrompt = NumberPromptOptions & { resolve: (value: number | null) => void };

/**
 * An in-app replacement for window.prompt() when the answer is a whole number
 * (days to extend, seats to allow). Resolves to the number, or null when the
 * dialog is dismissed. Validates before resolving, so callers never have to
 * parse or re-check a free-text string.
 *
 *   const { prompt, dialog } = useNumberPrompt();
 *   const days = await prompt({ title: "Extend license", label: "Days", initialValue: 30, min: 1 });
 *   if (days === null) return;
 */
export function useNumberPrompt() {
  const [pending, setPending] = useState<PendingPrompt | null>(null);
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  const prompt = useCallback((options: NumberPromptOptions) => {
    setValue(String(options.initialValue));
    setError("");
    return new Promise<number | null>((resolve) => setPending({ ...options, resolve }));
  }, []);

  function settle(result: number | null) {
    pending?.resolve(result);
    setPending(null);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const min = pending?.min ?? 0;
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed < min) {
      setError(`Enter a whole number of ${min} or more.`);
      return;
    }
    settle(parsed);
  }

  const dialog = (
    <Modal
      open={pending !== null}
      onClose={() => settle(null)}
      size="md"
      title={pending?.title ?? ""}
      description={pending?.message}
    >
      <form className={styles.form} onSubmit={onSubmit} noValidate>
        <Field
          label={pending?.label ?? ""}
          name="number_prompt_value"
          type="number"
          min={pending?.min}
          step={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          error={error}
        />
        <div className={styles.actions}>
          <Button variant="secondary" onClick={() => settle(null)}>
            Cancel
          </Button>
          <Button type="submit">{pending?.confirmLabel ?? "Save"}</Button>
        </div>
      </form>
    </Modal>
  );

  return { prompt, dialog };
}
