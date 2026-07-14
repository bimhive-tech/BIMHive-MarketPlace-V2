"use client";

import { useState } from "react";

import { Icon } from "@/components/Icon/Icon";

import styles from "./StarRatingInput.module.css";

interface StarRatingInputProps {
  value: number;
  onChange: (value: number) => void;
  size?: number;
}

export function StarRatingInput({ value, onChange, size = 24 }: StarRatingInputProps) {
  const [hovered, setHovered] = useState(0);
  const shown = hovered || value;

  return (
    <span className={styles.stars} role="radiogroup" aria-label="Rating">
      {Array.from({ length: 5 }).map((_, i) => {
        const star = i + 1;
        return (
          <button
            key={star}
            type="button"
            role="radio"
            aria-checked={value === star}
            aria-label={`${star} star${star === 1 ? "" : "s"}`}
            className={styles.star}
            onClick={() => onChange(star)}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
          >
            <Icon name="star" size={size} filled={star <= shown} />
          </button>
        );
      })}
    </span>
  );
}
