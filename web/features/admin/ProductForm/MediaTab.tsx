"use client";

import { useRef, useState, type ChangeEvent } from "react";

import { Icon } from "@/components/Icon/Icon";
import { uploadProductMedia, type AdminProductMedia } from "@/lib/adminApi";

import styles from "./ProductForm.module.css";

interface MediaTabProps {
  media: AdminProductMedia[];
  setMedia: (updater: (list: AdminProductMedia[]) => AdminProductMedia[]) => void;
  productId?: number;
  ensureSaved: () => Promise<number | null>;
}

export function MediaTab({ media, setMedia, productId, ensureSaved }: MediaTabProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  function update(i: number, patch: Partial<AdminProductMedia>) {
    setMedia((list) => list.map((m, idx) => (idx === i ? { ...m, ...patch } : m)));
  }

  function reorder(from: number, to: number) {
    setMedia((list) => {
      const next = [...list];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  }

  async function onPick(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setUploading(true);
    try {
      const id = productId ?? (await ensureSaved());
      if (!id) return;
      const uploaded = await uploadProductMedia(id, file);
      setMedia((list) => [
        ...list,
        {
          media_type: uploaded.media_type,
          url: uploaded.url,
          caption: "",
          is_cover: list.length === 0,
          sort_order: list.length,
        },
      ]);
    } catch {
      setError("Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className={styles.panel}>
      <p className={styles.label}>Gallery Images &amp; Video</p>
      <p className={styles.hint}>
        Upload an image or video — the type is detected automatically. Drag rows by the handle to
        reorder; the item marked &quot;cover&quot; is used as the product card thumbnail.
      </p>

      {media.map((item, i) => (
        <div
          key={i}
          className={`${styles.mediaRow} ${dragIndex === i ? styles.mediaRowDragging : ""}`}
          draggable
          onDragStart={() => setDragIndex(i)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => {
            if (dragIndex !== null && dragIndex !== i) reorder(dragIndex, i);
            setDragIndex(null);
          }}
          onDragEnd={() => setDragIndex(null)}
        >
          <span className={styles.dragHandle} aria-hidden="true">
            <Icon name="grip-vertical" size={16} />
          </span>
          <span className={styles.mediaThumb}>
            {item.media_type === "video" ? (
              <Icon name="video" size={18} />
            ) : item.url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={item.url} alt="" />
            ) : (
              <Icon name="image" size={18} />
            )}
          </span>
          <input
            className={styles.input}
            value={item.caption}
            onChange={(e) => update(i, { caption: e.target.value })}
            placeholder="Caption (optional)"
          />
          <label className={styles.coverToggle}>
            <input
              type="radio"
              name="cover"
              checked={item.is_cover}
              onChange={() => setMedia((list) => list.map((m, idx) => ({ ...m, is_cover: idx === i })))}
            />
            Cover
          </label>
          <button
            className={styles.iconBtn}
            aria-label="Remove media"
            onClick={() => setMedia((list) => list.filter((_, idx) => idx !== i))}
          >
            <Icon name="trash" size={16} />
          </button>
        </div>
      ))}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,video/*"
        className={styles.hiddenFileInput}
        onChange={onPick}
      />
      <button className={styles.addBtn} disabled={uploading} onClick={() => fileInputRef.current?.click()}>
        <Icon name="upload" size={14} /> {uploading ? "Uploading…" : "Upload Image or Video"}
      </button>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}
