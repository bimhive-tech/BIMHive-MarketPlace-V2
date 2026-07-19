"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Icon } from "@/components/Icon/Icon";
import { getPluginBuilds, type PluginBuild } from "@/lib/adminApi";

import styles from "./ProductRowActions.module.css";

interface ProductRowActionsProps {
  productId: number;
  editHref: string;
  /** Only Revit Plugin products can ever have an installer build. */
  isPlugin: boolean;
}

/** Per-row "..." menu on the admin Products list — Edit, plus Download
 * Installer for plugin products (fetches build status lazily on open,
 * so the list itself doesn't pay for an extra request per row). Renders
 * the menu through a portal so it isn't clipped by the table's
 * overflow-y: hidden wrapper. */
export function ProductRowActions({ productId, editHref, isPlugin }: ProductRowActionsProps) {
  const [open, setOpen] = useState(false);
  const [builds, setBuilds] = useState<PluginBuild[] | null>(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e: MouseEvent) {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open]);

  function onToggle() {
    if (!open) {
      const rect = triggerRef.current!.getBoundingClientRect();
      setMenuPos({ top: rect.bottom + 6, left: rect.right - 220 });
      if (isPlugin && builds === null) {
        getPluginBuilds(productId).then(setBuilds).catch(() => setBuilds([]));
      }
    }
    setOpen((o) => !o);
  }

  const readyBuilds = (builds ?? []).filter((b) => b.status === "ready");

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        aria-label="More actions"
        aria-expanded={open}
        onClick={onToggle}
      >
        <Icon name="more-horizontal" size={16} />
      </button>
      {open &&
        createPortal(
          <div ref={menuRef} className={styles.menu} style={{ top: menuPos.top, left: menuPos.left }}>
            <a href={editHref} className={styles.menuItem} onClick={() => setOpen(false)}>
              <Icon name="edit" size={14} /> Edit
            </a>
            {isPlugin && (
              <div className={styles.menuSection}>
                <span className={styles.menuLabel}>Download Installer</span>
                {builds === null && <span className={styles.menuHint}>Loading…</span>}
                {builds !== null && readyBuilds.length === 0 && (
                  <span className={styles.menuHint}>No installer built yet</span>
                )}
                {readyBuilds.map((b) => (
                  <a
                    key={b.id}
                    href={`/api/admin/plugin-builds/${b.id}/download`}
                    className={styles.menuItem}
                    onClick={() => setOpen(false)}
                  >
                    <Icon name="download" size={14} /> Revit {b.revit_year}
                  </a>
                ))}
              </div>
            )}
          </div>,
          document.body,
        )}
    </>
  );
}
