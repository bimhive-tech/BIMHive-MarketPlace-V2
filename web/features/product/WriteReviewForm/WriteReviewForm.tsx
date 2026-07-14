"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Field } from "@/components/Field/Field";
import { StarRatingInput } from "@/components/StarRatingInput/StarRatingInput";
import { AccountApiError, submitReview } from "@/lib/accountApi";
import { me } from "@/lib/auth";
import type { Review, User } from "@/lib/types";

import styles from "./WriteReviewForm.module.css";

interface WriteReviewFormProps {
  productSlug: string;
  onPosted: (review: Review) => void;
}

export function WriteReviewForm({ productSlug, onPosted }: WriteReviewFormProps) {
  const router = useRouter();
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    me().then(setUser);
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating === 0) {
      setError("Pick a star rating first.");
      return;
    }
    setError("");
    setPending(true);
    try {
      const review = await submitReview(productSlug, { rating, title, body });
      setSubmitted(true);
      onPosted(review);
      router.refresh(); // reconciles the aggregate rating/count once the page's fetch cache catches up
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't post your review.");
    } finally {
      setPending(false);
    }
  }

  if (submitted) {
    return <p className={styles.thanks}>Thanks — your review is posted.</p>;
  }

  if (user === null) {
    return (
      <div className={styles.loginPrompt}>
        <span>Have this product?</span>
        <Button href={`/login?next=/products/${productSlug}`} variant="secondary" size="md">
          Log in to write a review
        </Button>
      </div>
    );
  }

  if (user === undefined) return null;

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <h3 className={styles.heading}>Write a review</h3>
      {error && <p className={styles.error}>{error}</p>}
      <StarRatingInput value={rating} onChange={setRating} />
      <Field
        label="Title"
        name="title"
        placeholder="Sum it up in a few words"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={180}
      />
      <div className={styles.field}>
        <label htmlFor="review-body" className={styles.label}>
          Review
        </label>
        <textarea
          id="review-body"
          className={styles.textarea}
          placeholder="What did you use this for, and how did it go?"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
        />
      </div>
      <Button type="submit" disabled={pending} size="md">
        {pending ? "Posting…" : "Post Review"}
      </Button>
    </form>
  );
}
