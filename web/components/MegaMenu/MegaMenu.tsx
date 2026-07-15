"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { Icon } from "@/components/Icon/Icon";

import styles from "./MegaMenu.module.css";

interface MegaMenuProps {
  label: string;
  children: ReactNode;
}

/** A full-width dropdown panel anchored under the header — opens on hover or
 * click, closes on outside click, Escape, or route change. The panel (and
 * whatever it renders, e.g. SolutionsPanel's data fetch) stays mounted at all
 * times and is only hidden via CSS — toggling it in and out of the tree would
 * re-run that fetch on every single open. */
export function MegaMenu({ label, children }: MegaMenuProps) {
  const [open, setOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
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

  function openNow() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpen(true);
  }

  // Short delay so moving the mouse from the trigger into the panel doesn't
  // close it — without this, any gap between the two reads as "left the menu."
  function closeSoon() {
    closeTimer.current = setTimeout(() => setOpen(false), 150);
  }

  return (
    <div className={styles.wrap} ref={wrapRef} onMouseEnter={openNow} onMouseLeave={closeSoon}>
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        // Not a toggle: hover already opens this on desktop, and a click follows
        // right behind the hover that triggered it — toggling here would just
        // immediately close what hover had opened a moment earlier. Click (and
        // keyboard focus) only ever *open*; closing is mouseleave/outside-click/Escape.
        onClick={openNow}
        onFocus={openNow}
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
