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
  const images = media.filter((m) => m.media_type === "image" && m.url);
  const [active, setActive] = useState(0);

  // No uploaded media yet → show the brand wireframe as the single frame.
  if (!images.length) {
    return (
      <div className={styles.gallery}>
        <div className={styles.stage}>
          <WireframeThumb seed={slug} label={name} />
        </div>
      </div>
    );
  }

  const current = images[Math.min(active, images.length - 1)];

  return (
    <div className={styles.gallery}>
      <div className={styles.stage}>
        <Image src={current.url} alt={current.caption || name} fill sizes="(max-width: 900px) 100vw, 640px" className={styles.stageImg} />
      </div>
      <div className={styles.thumbs}>
        {images.map((img, i) => (
          <button
            key={img.id}
            className={`${styles.thumb} ${i === active ? styles.thumbActive : ""}`}
            onClick={() => setActive(i)}
            aria-label={`View image ${i + 1}`}
          >
            <Image src={img.url} alt="" fill sizes="80px" className={styles.thumbImg} />
          </button>
        ))}
        <span className={styles.playHint} aria-hidden="true">
          <Icon name="play" size={20} />
        </span>
      </div>
    </div>
  );
}
