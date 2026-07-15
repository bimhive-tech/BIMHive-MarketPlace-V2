"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { StarRating } from "@/components/StarRating/StarRating";
import { StarRatingInput } from "@/components/StarRatingInput/StarRatingInput";
import {
  AccountApiError,
  deleteAccountReview,
  getAccountReviews,
  updateAccountReview,
  type AccountReview,
} from "@/lib/accountApi";

import styles from "./ReviewsList.module.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function ReviewsList() {
  const [reviews, setReviews] = useState<AccountReview[] | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    getAccountReviews()
      .then(setReviews)
      .catch(() => setReviews([]));
  }, []);

  function replace(review: AccountReview) {
    setReviews((list) => (list ?? []).map((r) => (r.id === review.id ? review : r)));
  }

  async function onDelete(id: number) {
    if (!window.confirm("Delete this review? This cannot be undone.")) return;
    await deleteAccountReview(id);
    setReviews((list) => (list ?? []).filter((r) => r.id !== id));
  }

  if (reviews === null) return <p className={styles.loading}>Loading your reviews…</p>;

  if (reviews.length === 0) {
    return (
      <EmptyState
        icon="star"
        title="No reviews yet"
        text="Reviews you write for products you own will show up here — you can edit or remove them any time."
        actionLabel="Browse the marketplace"
        actionHref="/catalog"
      />
    );
  }

  return (
    <div className={styles.list}>
      {reviews.map((review) =>
        editingId === review.id ? (
          <EditReviewCard
            key={review.id}
            review={review}
            onSaved={(updated) => {
              replace(updated);
              setEditingId(null);
            }}
            onCancel={() => setEditingId(null)}
          />
        ) : (
          <div key={review.id} className={styles.card}>
            <div className={styles.head}>
              <Link href={`/products/${review.product_slug}`} className={styles.product}>
                {review.product_name}
              </Link>
              {review.is_verified_purchase && <Pill tone="success">Verified Purchase</Pill>}
            </div>
            <StarRating value={review.rating} size={16} showValue={false} />
            {review.title && <p className={styles.title}>{review.title}</p>}
            {review.body && <p className={styles.body}>{review.body}</p>}
            <div className={styles.meta}>
              <span className={styles.date}>Reviewed {formatDate(review.created_at)}</span>
              <div className={styles.actions}>
                <button className={styles.actionBtn} onClick={() => setEditingId(review.id)}>
                  <Icon name="edit" size={14} /> Edit
                </button>
                <button className={styles.actionBtnDanger} onClick={() => onDelete(review.id)}>
                  <Icon name="trash" size={14} /> Delete
                </button>
              </div>
            </div>
          </div>
        ),
      )}
    </div>
  );
}

function EditReviewCard({
  review,
  onSaved,
  onCancel,
}: {
  review: AccountReview;
  onSaved: (review: AccountReview) => void;
  onCancel: () => void;
}) {
  const [rating, setRating] = useState(review.rating);
  const [title, setTitle] = useState(review.title);
  const [body, setBody] = useState(review.body);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function onSave() {
    setError("");
    setSaving(true);
    try {
      const updated = await updateAccountReview(review.id, { rating, title, body });
      onSaved(updated);
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't save your changes.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <span className={styles.product}>{review.product_name}</span>
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <StarRatingInput value={rating} onChange={setRating} size={22} />
      <input
        className={styles.input}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Sum it up in a few words"
        maxLength={180}
      />
      <textarea
        className={styles.textarea}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="What did you use this for, and how did it go?"
        rows={4}
      />
      <div className={styles.editActions}>
        <button className={styles.saveBtn} disabled={saving} onClick={onSave}>
          {saving ? "Saving…" : "Save"}
        </button>
        <button className={styles.cancelBtn} disabled={saving} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
