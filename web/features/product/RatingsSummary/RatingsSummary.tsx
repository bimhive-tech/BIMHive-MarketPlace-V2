import { Button } from "@/components/Button/Button";
import { StarRating } from "@/components/StarRating/StarRating";
import type { RatingBreakdownRow } from "@/lib/types";

import styles from "./RatingsSummary.module.css";

interface RatingsSummaryProps {
  average: number;
  count: number;
  breakdown: RatingBreakdownRow[];
}

export function RatingsSummary({ average, count, breakdown }: RatingsSummaryProps) {
  return (
    <div className={styles.card}>
      <div className={styles.left}>
        <div className={styles.average}>
          {average.toFixed(1)} <span className={styles.outOf}>out of 5</span>
        </div>
        <StarRating value={average} size={18} showValue={false} />
        <p className={styles.based}>Based on {count} reviews</p>
        <Button variant="secondary">View all reviews</Button>
      </div>

      <div className={styles.bars}>
        {breakdown.map((row) => (
          <div key={row.stars} className={styles.barRow}>
            <span className={styles.starLabel}>{row.stars}★</span>
            <span className={styles.track}>
              <span className={styles.fill} style={{ width: `${row.percent}%` }} />
            </span>
            <span className={styles.percent}>{row.percent}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
