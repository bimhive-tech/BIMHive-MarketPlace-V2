"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { StarRating } from "@/components/StarRating/StarRating";
import { deleteAdminReview, getAdminReviews, type AdminReview } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function AdminReviewsPage() {
  const [rows, setRows] = useState<AdminReview[] | null>(null);

  useEffect(() => {
    getAdminReviews().then(setRows).catch(() => setRows([]));
  }, []);

  async function onDelete(id: number) {
    const confirmed = window.confirm("Remove this review? This cannot be undone.");
    if (!confirmed) return;
    await deleteAdminReview(id);
    setRows((list) => list?.filter((r) => r.id !== id) ?? null);
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Reviews</h1>
          <p className={styles.sub}>Moderate reviews across every product.</p>
        </div>
      </header>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Product</th>
              <th>Author</th>
              <th>Rating</th>
              <th>Review</th>
              <th>Posted</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.product_name}</strong>
                </td>
                <td className={styles.muted}>{row.author_name || "Verified user"}</td>
                <td>
                  <StarRating value={row.rating} size={13} showValue={false} />
                </td>
                <td style={{ maxWidth: 360 }}>
                  {row.title && <strong>{row.title}</strong>}
                  <div className={styles.muted}>{row.body}</div>
                </td>
                <td className={styles.muted}>{formatDate(row.created_at)}</td>
                <td>
                  <button
                    className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                    aria-label="Delete review"
                    onClick={() => onDelete(row.id)}
                  >
                    <Icon name="trash" size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {rows === null && <p className={styles.state}>Loading reviews…</p>}
        {rows?.length === 0 && <p className={styles.state}>No reviews yet.</p>}
      </div>

      {rows && rows.length > 0 && (
        <p className={styles.count}>
          Showing {rows.length} {rows.length === 1 ? "review" : "reviews"}
        </p>
      )}
    </div>
  );
}
