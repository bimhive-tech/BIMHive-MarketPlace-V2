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
 * Installer for plugin products (fetches uploaded builds lazily on open, so
 * the list itself doesn't pay for an extra request per row). Every download
 * click generates the .exe live server-side — nothing is pre-built or
 * cached, so this uses fetch+blob instead of a plain link: a failed build
 * returns a JSON error, and a plain <a> would just "download" that JSON
 * instead of showing the admin what went wrong. Renders through a portal so
 * it isn't clipped by the table's overflow-y: hidden wrapper. */
export function ProductRowActions({ productId, editHref, isPlugin }: ProductRowActionsProps) {
  const [open, setOpen] = useState(false);
  const [builds, setBuilds] = useState<PluginBuild[] | null>(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState("");
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
      setError("");
      if (isPlugin && builds === null) {
        getPluginBuilds(productId).then(setBuilds).catch(() => setBuilds([]));
      }
    }
    setOpen((o) => !o);
  }

  async function onDownload(build: PluginBuild) {
    setError("");
    setDownloadingId(build.id);
    try {
      const res = await fetch(`/api/admin/plugin-builds/${build.id}/download`, { credentials: "include" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}) as Record<string, string>);
        throw new Error(body.detail || "Could not generate the installer.");
      }
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") || "";
      const filename = disposition.match(/filename="?([^"]+)"?/)?.[1] || `installer-${build.revit_year}.exe`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate the installer.");
    } finally {
      setDownloadingId(null);
    }
  }

  const uploadedBuilds = (builds ?? []).filter((b) => b.dll_filename && b.addin_filename);

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
                {error && <span className={styles.menuError}>{error}</span>}
                {builds === null && <span className={styles.menuHint}>Loading…</span>}
                {builds !== null && uploadedBuilds.length === 0 && (
                  <span className={styles.menuHint}>Upload a .dll and .addin first</span>
                )}
                {uploadedBuilds.map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    className={styles.menuItem}
                    disabled={downloadingId === b.id}
                    onClick={() => onDownload(b)}
                  >
                    <Icon name="download" size={14} />
                    {downloadingId === b.id ? `Building Revit ${b.revit_year}…` : `Revit ${b.revit_year}`}
                  </button>
                ))}
              </div>
            )}
          </div>,
          document.body,
        )}
    </>
  );
}
