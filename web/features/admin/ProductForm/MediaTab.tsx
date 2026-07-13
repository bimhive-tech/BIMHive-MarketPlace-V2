import { Icon } from "@/components/Icon/Icon";
import type { AdminProductMedia } from "@/lib/adminApi";

import styles from "./ProductForm.module.css";

interface MediaTabProps {
  media: AdminProductMedia[];
  setMedia: (updater: (list: AdminProductMedia[]) => AdminProductMedia[]) => void;
}

export function MediaTab({ media, setMedia }: MediaTabProps) {
  function update(i: number, patch: Partial<AdminProductMedia>) {
    setMedia((list) => list.map((m, idx) => (idx === i ? { ...m, ...patch } : m)));
  }

  return (
    <div className={styles.panel}>
      <p className={styles.label}>Gallery Images &amp; Video</p>
      <p className={styles.hint}>
        Paste a hosted image or video URL per row. The first item marked &quot;cover&quot; is used
        as the product card thumbnail.
      </p>

      {media.map((item, i) => (
        <div key={i} className={styles.mediaRow}>
          <select
            className={styles.input}
            value={item.media_type}
            onChange={(e) => update(i, { media_type: e.target.value as "image" | "video" })}
          >
            <option value="image">Image</option>
            <option value="video">Video</option>
          </select>
          <input
            className={styles.input}
            value={item.url}
            onChange={(e) => update(i, { url: e.target.value })}
            placeholder="https://…"
          />
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

      <button
        className={styles.addBtn}
        onClick={() =>
          setMedia((list) => [
            ...list,
            { media_type: "image", url: "", caption: "", is_cover: list.length === 0, sort_order: list.length },
          ])
        }
      >
        <Icon name="plus" size={14} /> Add Media
      </button>
    </div>
  );
}
