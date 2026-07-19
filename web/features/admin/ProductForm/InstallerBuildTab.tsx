"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { SUPPORTED_REVIT_YEARS } from "@/config/site";
import {
  AdminApiError,
  createPluginBuild,
  deletePluginBuild,
  getDestinationOptions,
  getPluginBuilds,
  type DestinationOption,
  type PluginBuild,
} from "@/lib/adminApi";

import { PluginBuildCard } from "./PluginBuildCard";
import styles from "./ProductForm.module.css";

interface InstallerBuildTabProps {
  productId?: number;
  ensureSaved: () => Promise<number | null>;
  asPartner?: boolean;
}

export function InstallerBuildTab({ productId, ensureSaved, asPartner = false }: InstallerBuildTabProps) {
  const [builds, setBuilds] = useState<PluginBuild[] | null>(null);
  const [destinationOptions, setDestinationOptions] = useState<DestinationOption[]>([]);
  const [newYear, setNewYear] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getDestinationOptions().then(setDestinationOptions).catch(() => setDestinationOptions([]));
  }, []);

  useEffect(() => {
    if (!productId) {
      setBuilds([]);
      return;
    }
    getPluginBuilds(productId, asPartner)
      .then(setBuilds)
      .catch(() => setBuilds([]));
  }, [productId, asPartner]);

  const availableYears = SUPPORTED_REVIT_YEARS.filter(
    (year) => !builds?.some((b) => b.revit_year === year),
  );

  async function onAddYear() {
    setError("");
    const year = newYear || availableYears[0];
    if (!year) return;
    setAdding(true);
    try {
      const id = productId ?? (await ensureSaved());
      if (!id) return;
      const created = await createPluginBuild(id, year, asPartner);
      setBuilds((list) => [...(list ?? []), created]);
      setNewYear("");
    } catch (err) {
      setError(err instanceof AdminApiError ? err.detail : "Could not add this Revit year.");
    } finally {
      setAdding(false);
    }
  }

  async function onRemoveBuild(buildId: string) {
    if (!window.confirm("Remove this Revit-year build? The uploaded .dll, .addin, and resource files are deleted.")) {
      return;
    }
    await deletePluginBuild(buildId, asPartner);
    setBuilds((list) => (list ?? []).filter((b) => b.id !== buildId));
  }

  return (
    <div className={styles.panel}>
      <p className={styles.label}>Installer Builds</p>
      <p className={styles.hint}>
        Upload the compiled .dll and .addin manifest for each Revit year you support, plus any
        resources or dependencies. BIMHive generates the real Windows installer on the spot when a
        customer downloads it (or when you test-download it from the products list) — no separate
        installer-building tool, and no build step here.
      </p>

      {!productId && (
        <p className={styles.hint}>Save the product as a draft first (fill in the Product Information tab), then come back here to add a build.</p>
      )}

      {productId && (
        <>
          <div className={styles.addYearRow}>
            <select className={styles.input} value={newYear} onChange={(e) => setNewYear(e.target.value)}>
              <option value="">
                {availableYears.length ? "Choose a Revit year…" : "All supported years already added"}
              </option>
              {availableYears.map((year) => (
                <option key={year} value={year}>
                  Revit {year}
                </option>
              ))}
            </select>
            <button
              type="button"
              className={styles.addBtn}
              disabled={adding || availableYears.length === 0}
              onClick={onAddYear}
            >
              <Icon name="plus" size={14} /> Add Revit Year
            </button>
          </div>

          {error && <p className={styles.error}>{error}</p>}

          {builds === null && <p className={styles.hint}>Loading builds…</p>}

          {builds?.length === 0 && (
            <p className={styles.hint}>No builds yet — add a Revit year above to get started.</p>
          )}

          {builds?.map((build) => (
            <PluginBuildCard
              key={build.id}
              build={build}
              destinationOptions={destinationOptions}
              asPartner={asPartner}
              onChange={(updated) =>
                setBuilds((list) => (list ?? []).map((b) => (b.id === updated.id ? updated : b)))
              }
              onRemove={() => onRemoveBuild(build.id)}
            />
          ))}
        </>
      )}
    </div>
  );
}
