"use client";

import { useRef, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import {
  AdminApiError,
  deletePluginResource,
  triggerPluginBuild,
  updatePluginBuild,
  uploadPluginAddin,
  uploadPluginDll,
  uploadPluginResource,
  type DestinationOption,
  type PluginBuild,
} from "@/lib/adminApi";

import styles from "./ProductForm.module.css";

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  ready: "success",
  building: "warning",
  failed: "error",
  draft: "neutral",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface PluginBuildCardProps {
  build: PluginBuild;
  destinationOptions: DestinationOption[];
  asPartner: boolean;
  onChange: (build: PluginBuild) => void;
  onRemove: () => void;
}

export function PluginBuildCard({ build, destinationOptions, asPartner, onChange, onRemove }: PluginBuildCardProps) {
  const dllInputRef = useRef<HTMLInputElement>(null);
  const addinInputRef = useRef<HTMLInputElement>(null);
  const [version, setVersion] = useState(build.plugin_version);
  const [uploadingDll, setUploadingDll] = useState(false);
  const [uploadingAddin, setUploadingAddin] = useState(false);
  const [building, setBuilding] = useState(false);
  const [showLog, setShowLog] = useState(false);
  const [error, setError] = useState("");

  const [resourceFile, setResourceFile] = useState<File | null>(null);
  const [resourceKind, setResourceKind] = useState<"resource" | "dependency">("resource");
  const [resourceToken, setResourceToken] = useState(destinationOptions[0]?.token ?? "");
  const [resourceSubpath, setResourceSubpath] = useState("");
  const [addingResource, setAddingResource] = useState(false);

  async function onVersionBlur() {
    if (version === build.plugin_version) return;
    try {
      const updated = await updatePluginBuild(build.id, { plugin_version: version }, asPartner);
      onChange(updated);
    } catch {
      setVersion(build.plugin_version);
      setError("Could not save the version number.");
    }
  }

  async function onPickDll(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setUploadingDll(true);
    try {
      onChange(await uploadPluginDll(build.id, file, asPartner));
    } catch (err) {
      setError(err instanceof AdminApiError ? err.detail : "Could not upload the .dll file.");
    } finally {
      setUploadingDll(false);
    }
  }

  async function onPickAddin(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setUploadingAddin(true);
    try {
      onChange(await uploadPluginAddin(build.id, file, asPartner));
    } catch (err) {
      setError(err instanceof AdminApiError ? err.detail : "Could not upload the .addin file.");
    } finally {
      setUploadingAddin(false);
    }
  }

  async function onAddResource() {
    setError("");
    if (!resourceFile) {
      setError("Choose a file to add.");
      return;
    }
    if (!resourceToken) {
      setError("Choose a destination first.");
      return;
    }
    const destinationPath = resourceSubpath ? `${resourceToken}\\${resourceSubpath}` : resourceToken;
    setAddingResource(true);
    try {
      await uploadPluginResource(build.id, resourceFile, destinationPath, resourceKind, asPartner);
      onChange({
        ...build,
        status: "draft",
        resource_files: [
          ...build.resource_files,
          {
            id: crypto.randomUUID(),
            kind: resourceKind,
            original_filename: resourceFile.name,
            destination_path: destinationPath,
            sort_order: build.resource_files.length,
          },
        ],
      });
      setResourceFile(null);
      setResourceSubpath("");
    } catch (err) {
      setError(err instanceof AdminApiError ? err.detail : "Could not add this file.");
    } finally {
      setAddingResource(false);
    }
  }

  async function onRemoveResource(resourceId: string) {
    await deletePluginResource(build.id, resourceId, asPartner);
    onChange({
      ...build,
      status: "draft",
      resource_files: build.resource_files.filter((r) => r.id !== resourceId),
    });
  }

  async function onBuild() {
    setError("");
    setBuilding(true);
    try {
      const result = await triggerPluginBuild(build.id, asPartner);
      onChange(result);
      setShowLog(result.status === "failed");
    } catch (err) {
      setError(err instanceof AdminApiError ? err.detail : "Could not start the build.");
    } finally {
      setBuilding(false);
    }
  }

  const activeHint = destinationOptions.find((o) => o.token === resourceToken)?.hint;
  const canBuild = Boolean(build.dll_filename && build.addin_filename) && !building;

  return (
    <div className={`${styles.fileRow} ${styles.buildCard}`}>
      <div className={styles.buildHeaderRow}>
        <strong>Revit {build.revit_year}</strong>
        <Pill tone={STATUS_TONE[build.status] ?? "neutral"}>{build.status}</Pill>
        <Pill tone="neutral">{build.scope === "perMachine" ? "Program Files (admin)" : "Per-user"}</Pill>
        <span className={styles.spacer} />
        <button type="button" className={styles.iconBtn} aria-label="Remove this Revit-year build" onClick={onRemove}>
          <Icon name="trash" size={16} />
        </button>
      </div>

      <label className={styles.label}>
        Plugin Version
        <input
          className={styles.input}
          value={version}
          onChange={(e) => setVersion(e.target.value)}
          onBlur={onVersionBlur}
          placeholder="1.0.0"
        />
      </label>

      <div className={styles.row}>
        <div className={styles.fileInfo}>
          <span className={styles.fileName}>{build.dll_filename || "No .dll uploaded"}</span>
          <span className={styles.fileMeta}>Compiled plugin DLL</span>
        </div>
        <input ref={dllInputRef} type="file" accept=".dll" className={styles.hiddenFileInput} onChange={onPickDll} />
        <button type="button" className={styles.addBtn} disabled={uploadingDll} onClick={() => dllInputRef.current?.click()}>
          <Icon name="upload" size={14} /> {uploadingDll ? "Uploading…" : build.dll_filename ? "Replace .dll" : "Upload .dll"}
        </button>
      </div>

      <div className={styles.row}>
        <div className={styles.fileInfo}>
          <span className={styles.fileName}>{build.addin_filename || "No .addin uploaded"}</span>
          <span className={styles.fileMeta}>Revit add-in manifest</span>
        </div>
        <input
          ref={addinInputRef}
          type="file"
          accept=".addin"
          className={styles.hiddenFileInput}
          onChange={onPickAddin}
        />
        <button
          type="button"
          className={styles.addBtn}
          disabled={uploadingAddin}
          onClick={() => addinInputRef.current?.click()}
        >
          <Icon name="upload" size={14} /> {uploadingAddin ? "Uploading…" : build.addin_filename ? "Replace .addin" : "Upload .addin"}
        </button>
      </div>

      <div>
        <p className={styles.label}>Resources &amp; Dependencies</p>
        {build.resource_files.length > 0 && (
          <ul className={styles.fileList}>
            {build.resource_files.map((resource) => (
              <li key={resource.id} className={styles.fileRow}>
                <Icon name={resource.kind === "dependency" ? "plug" : "document"} size={16} />
                <div className={styles.fileInfo}>
                  <span className={styles.fileName}>{resource.original_filename}</span>
                  <span className={styles.fileMeta}>{resource.destination_path}</span>
                </div>
                <button
                  type="button"
                  className={styles.iconBtn}
                  aria-label={`Remove ${resource.original_filename}`}
                  onClick={() => onRemoveResource(resource.id)}
                >
                  <Icon name="trash" size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className={styles.uploadRow}>
          <select className={styles.input} value={resourceKind} onChange={(e) => setResourceKind(e.target.value as "resource" | "dependency")}>
            <option value="resource">Resource</option>
            <option value="dependency">Dependency</option>
          </select>
          <select className={styles.input} value={resourceToken} onChange={(e) => setResourceToken(e.target.value)}>
            {destinationOptions.map((option) => (
              <option key={option.token} value={option.token}>
                {option.label}
              </option>
            ))}
          </select>
          <input
            className={styles.input}
            value={resourceSubpath}
            onChange={(e) => setResourceSubpath(e.target.value)}
            placeholder="optional subfolder\file.ext"
          />
          <input
            type="file"
            className={styles.fileInput}
            onChange={(e) => setResourceFile(e.target.files?.[0] ?? null)}
          />
        </div>
        {activeHint && <p className={styles.hint}>{activeHint}</p>}
        <button type="button" className={styles.addBtn} disabled={addingResource} onClick={onAddResource}>
          <Icon name="plus" size={14} /> {addingResource ? "Adding…" : "Add File"}
        </button>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.buildActionsRow}>
        <button type="button" className={styles.primaryBtn} disabled={!canBuild} onClick={onBuild}>
          {building ? "Building…" : "Build Installer"}
        </button>
        {build.built_at && (
          <span className={styles.fileMeta}>
            Last built {new Date(build.built_at).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })}
          </span>
        )}
        {build.build_log && (
          <button type="button" className={styles.secondaryBtn} onClick={() => setShowLog((v) => !v)}>
            {showLog ? "Hide Log" : "View Log"}
          </button>
        )}
      </div>

      {showLog && build.build_log && <pre className={styles.buildLog}>{build.build_log}</pre>}
    </div>
  );
}
