"use client";

import { useCallback, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Modal } from "@/components/Modal/Modal";

export interface ConfirmOptions {
  title: string;
  /** The consequence, in a sentence — what actually happens if they say yes. */
  message?: string;
  confirmLabel?: string;
  /** Red confirm button, for something that can't be undone. */
  danger?: boolean;
}

type PendingConfirm = ConfirmOptions & { resolve: (confirmed: boolean) => void };

/**
 * An in-app replacement for window.confirm(): same one-line call site, but a
 * real dialog that matches the rest of the UI instead of the browser's.
 *
 *   const { confirm, dialog } = useConfirm();
 *   if (!(await confirm({ title: "Delete this tag?", danger: true }))) return;
 *   ...
 *   return <>{...}{dialog}</>;
 *
 * Closing it any other way (Escape, the backdrop, the X) counts as "no".
 */
export function useConfirm() {
  const [pending, setPending] = useState<PendingConfirm | null>(null);

  const confirm = useCallback(
    (options: ConfirmOptions) => new Promise<boolean>((resolve) => setPending({ ...options, resolve })),
    [],
  );

  function settle(confirmed: boolean) {
    pending?.resolve(confirmed);
    setPending(null);
  }

  const dialog = (
    <Modal
      open={pending !== null}
      onClose={() => settle(false)}
      size="md"
      title={pending?.title ?? ""}
      description={pending?.message}
      footer={
        <>
          <Button variant="secondary" onClick={() => settle(false)}>
            Cancel
          </Button>
          <Button variant={pending?.danger ? "danger" : "primary"} onClick={() => settle(true)}>
            {pending?.confirmLabel ?? "Confirm"}
          </Button>
        </>
      }
    />
  );

  return { confirm, dialog };
}
