"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { Icon } from "@/components/Icon/Icon";

import styles from "./MegaMenu.module.css";

interface MegaMenuProps {
  label: string;
  children: ReactNode;
}

/** A full-width dropdown panel anchored under the header — opens/closes on
 * click of the trigger, closes on outside click, Escape, or route change. The
 * panel (and whatever it renders, e.g. SolutionsPanel's data fetch) stays
 * mounted at all times and is only hidden via CSS — toggling it in and out of
 * the tree would re-run that fetch on every single open. */
export function MegaMenu({ label, children }: MegaMenuProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onOutsideClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onOutsideClick);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onOutsideClick);
      document.removeEventListener("keydown", onEscape);
    };
  }, []);

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        {label}
        <Icon name="chevron-down" size={16} className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`} />
      </button>

      <div className={`${styles.panel} ${open ? styles.panelOpen : ""}`} aria-hidden={!open}>
        <div className={`container ${styles.panelInner}`} onClick={() => setOpen(false)}>
          {children}
        </div>
      </div>
    </div>
  );
}
