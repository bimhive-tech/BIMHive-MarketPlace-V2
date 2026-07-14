"use client";

import Image from "next/image";
import { useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";
import type { ProductMedia } from "@/lib/types";

import styles from "./ProductGallery.module.css";

interface ProductGalleryProps {
  media: ProductMedia[];
  name: string;
  slug: string;
}

export function ProductGallery({ media, name, slug }: ProductGalleryProps) {
  const [active, setActive] = useState(0);

  // No uploaded media yet → show the brand wireframe as the single frame.
  if (!media.length) {
    return (
      <div className={styles.gallery}>
        <div className={styles.stage}>
          <WireframeThumb seed={slug} label={name} />
        </div>
      </div>
    );
  }

  const current = media[Math.min(active, media.length - 1)];
  const hasMultiple = media.length > 1;

  function go(delta: number) {
    setActive((i) => (i + delta + media.length) % media.length);
  }

  return (
    <div className={styles.gallery}>
      <div className={styles.stage}>
        {current.media_type === "video" ? (
          // Keyed so switching between videos fully remounts the player instead
          // of just swapping `src` on a live element, which can leave stale
          // playback/controls state behind.
          <video key={current.id} src={current.url} controls playsInline className={styles.stageVideo} />
        ) : (
          <Image
            src={current.url}
            alt={current.caption || name}
            fill
            sizes="(max-width: 900px) 100vw, 640px"
            className={styles.stageImg}
          />
        )}

        {hasMultiple && (
          <>
            <button
              type="button"
              className={`${styles.navBtn} ${styles.navPrev}`}
              onClick={() => go(-1)}
              aria-label="Previous media"
            >
              <Icon name="chevron-left" size={20} />
            </button>
            <button
              type="button"
              className={`${styles.navBtn} ${styles.navNext}`}
              onClick={() => go(1)}
              aria-label="Next media"
            >
              <Icon name="chevron-right" size={20} />
            </button>
          </>
        )}
      </div>

      {hasMultiple && (
        <div className={styles.thumbs}>
          {media.map((item, i) => (
            <button
              type="button"
              key={item.id}
              className={`${styles.thumb} ${i === active ? styles.thumbActive : ""}`}
              onClick={() => setActive(i)}
              aria-label={item.media_type === "video" ? `Play video ${i + 1}` : `View image ${i + 1}`}
            >
              {item.media_type === "video" ? (
                <span className={styles.thumbVideo} aria-hidden="true">
                  <Icon name="play" size={18} />
                </span>
              ) : (
                <Image src={item.url} alt="" fill sizes="80px" className={styles.thumbImg} />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
