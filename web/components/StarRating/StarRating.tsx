import { Icon } from "@/components/Icon/Icon";

import styles from "./StarRating.module.css";

interface StarRatingProps {
  value: number;
  count?: number;
  size?: number;
  showValue?: boolean;
}

export function StarRating({ value, count, size = 16, showValue = true }: StarRatingProps) {
  const rounded = Math.round(value);
  return (
    <span className={styles.wrap}>
      <span className={styles.stars} aria-label={`Rated ${value} out of 5`}>
        {Array.from({ length: 5 }).map((_, i) => (
          <Icon key={i} name="star" size={size} filled={i < rounded} className={styles.star} />
        ))}
      </span>
      {showValue && <span className={styles.value}>{Number(value).toFixed(1)}</span>}
      {count !== undefined && <span className={styles.count}>({count})</span>}
    </span>
  );
}
