"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { Icon } from "@/components/Icon/Icon";

import styles from "./Modal.module.css";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  /** Rendered as the dialog's accessible name — required, never decorative. */
  title: string;
  /** Optional line under the title, e.g. what the form does. */
  description?: string;
  /** Omit for a message-only dialog (e.g. a confirmation), which then has no
   * empty padded body between the header and the buttons. */
  children?: ReactNode;
  /** Action buttons pinned to the bottom; omit for a content-only dialog. */
  footer?: ReactNode;
  /** "lg" for dense forms (the admin create/edit panels), "xl" for a preview. */
  size?: "md" | "lg" | "xl";
}

/** Focusable elements, in DOM order, for the focus trap. */
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * The app's only modal. Portals to document.body so it can't be clipped by a
 * table's `overflow: hidden` wrapper (the same reason ProductRowActions does),
 * and layers on --z-modal.
 *
 * Deliberately carries the accessibility the app's older ad-hoc overlays never
 * had — Escape to close, a focus trap, focus restored to whatever opened it,
 * background scroll lock, and a real labelled `role="dialog"`. Anything that
 * needs an overlay should use this rather than adding a fourth hand-rolled
 * Escape/outside-click effect.
 */
export function Modal({ open, onClose, title, description, children, footer, size = "lg" }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  // Escape to close + focus trap. One listener, only while open.
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const focusables = panelRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE);
      if (!focusables?.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      // Wrap at both ends so focus can never escape into the page behind.
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  // Lock background scroll while open, and hand focus back on close — without
  // this the page behind scrolls under the overlay and the trigger loses focus.
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";
    // Focus the first control so keyboard users land inside, not behind.
    panelRef.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    return () => {
      document.body.style.overflow = overflow;
      previouslyFocused?.focus();
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className={styles.overlay} onMouseDown={onClose}>
      <div
        ref={panelRef}
        className={`${styles.panel} ${styles[size]}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        // The overlay closes on click; stop clicks inside the panel from
        // bubbling up to it, otherwise dragging a text selection out of an
        // input would dismiss the whole dialog.
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className={styles.header}>
          <div>
            <h2 id={titleId} className={styles.title}>
              {title}
            </h2>
            {description && (
              <p id={descriptionId} className={styles.description}>
                {description}
              </p>
            )}
          </div>
          <button type="button" className={styles.close} aria-label="Close" onClick={onClose}>
            <Icon name="x" size={18} />
          </button>
        </header>

        {children && <div className={styles.body}>{children}</div>}

        {footer && <footer className={styles.footer}>{footer}</footer>}
      </div>
    </div>,
    document.body,
  );
}
