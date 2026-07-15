import { ReviewsList } from "@/features/account/ReviewsList/ReviewsList";

import styles from "../section.module.css";

export default function ReviewsPage() {
  return (
    <div className={styles.section}>
      <h1 className={styles.title}>My Reviews</h1>
      <p className={styles.sub}>Reviews you've written for products you own. Edit or remove them any time.</p>
      <ReviewsList />
    </div>
  );
}
