"use client";

import { useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { AdminApiError, deleteProductFile, uploadProductFile, type AdminProductFile } from "@/lib/adminApi";

import styles from "./ProductForm.module.css";

interface FilesTabProps {
  productId?: number;
  files: AdminProductFile[];
  setFiles: (updater: (list: AdminProductFile[]) => AdminProductFile[]) => void;
  ensureSaved: () => Promise<number | null>;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FilesTab({ productId, files, setFiles, ensureSaved }: FilesTabProps) {
  const [revitVersion, setRevitVersion] = useState("2025");
  const [versionLabel, setVersionLabel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function onUpload() {
    setError("");
    if (!file || !versionLabel.trim()) {
      setError("A build version and a file are required.");
      return;
    }
    setUploading(true);
    try {
      const id = productId ?? (await ensureSaved());
      if (!id) return;
      const form = new FormData();
      form.append("revit_version", revitVersion);
      form.append("version_label", versionLabel.trim());
      form.append("is_current", "true");
      form.append("file", file);
      const created = await uploadProductFile(id, form);
      setFiles((list) => [created, ...list]);
      setVersionLabel("");
      setFile(null);
    } catch (err) {
      setError(err instanceof AdminApiError ? err.detail : "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(fileId: number) {
    await deleteProductFile(fileId);
    setFiles((list) => list.filter((f) => f.id !== fileId));
  }

  return (
    <div className={styles.panel}>
      <p className={styles.label}>Uploaded Builds</p>
      <p className={styles.hint}>
        Multi-variant: one file per Revit version. The download endpoint serves the right build for
        the requesting plugin.
      </p>

      {files.length > 0 && (
        <ul className={styles.fileList}>
          {files.map((f) => (
            <li key={f.id} className={styles.fileRow}>
              <Icon name="document" size={18} />
              <span className={styles.fileInfo}>
                <span className={styles.fileName}>
                  Revit {f.revit_version || "any"} — v{f.version_label}
                </span>
                <span className={styles.fileMeta}>{formatSize(f.file_size_bytes)}</span>
              </span>
              <button className={styles.iconBtn} aria-label="Delete file" onClick={() => onDelete(f.id)}>
                <Icon name="trash" size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className={styles.uploadRow}>
        <select className={styles.input} value={revitVersion} onChange={(e) => setRevitVersion(e.target.value)}>
          {["2022", "2023", "2024", "2025", "2026"].map((y) => (
            <option key={y} value={y}>
              Revit {y}
            </option>
          ))}
        </select>
        <input
          className={styles.input}
          value={versionLabel}
          onChange={(e) => setVersionLabel(e.target.value)}
          placeholder="Build version, e.g. 2.1.0"
        />
        <input
          className={styles.fileInput}
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button className={styles.addBtn} disabled={uploading} onClick={onUpload}>
          <Icon name="plus" size={14} /> {uploading ? "Uploading…" : "Upload"}
        </button>
      </div>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
