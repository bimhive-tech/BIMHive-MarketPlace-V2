"use client";

import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { KeyFeatures } from "@/features/product/KeyFeatures/KeyFeatures";
import { RatingsSummary } from "@/features/product/RatingsSummary/RatingsSummary";
import { WhatsNew } from "@/features/product/WhatsNew/WhatsNew";
import { WriteReviewForm } from "@/features/product/WriteReviewForm/WriteReviewForm";
import { StarRating } from "@/components/StarRating/StarRating";
import type { ProductDetail } from "@/lib/types";

import styles from "./ProductTabs.module.css";

type TabId = "overview" | "features" | "reviews" | "compatibility" | "documentation" | "support";

export function ProductTabs({ product }: { product: ProductDetail }) {
  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "features", label: "Features" },
    { id: "reviews", label: `Reviews (${product.rating_count})` },
    { id: "compatibility", label: "Compatibility" },
    { id: "documentation", label: "Documentation" },
    { id: "support", label: "Support" },
  ];
  const [active, setActive] = useState<TabId>("overview");

  return (
    <section className={styles.wrap}>
      <div className={styles.tabStrip} role="tablist" aria-label="Product details">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active === tab.id}
            className={`${styles.tab} ${active === tab.id ? styles.tabActive : ""}`}
            onClick={() => setActive(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className={styles.panel} role="tabpanel">
        {active === "overview" && <OverviewPanel product={product} />}
        {active === "features" && <KeyFeatures features={product.features} />}
        {active === "reviews" && <ReviewsPanel product={product} />}
        {active === "compatibility" && <CompatibilityPanel product={product} />}
        {active === "documentation" && <DocumentationPanel product={product} />}
        {active === "support" && <SupportPanel />}
      </div>
    </section>
  );
}

function OverviewPanel({ product }: { product: ProductDetail }) {
  return (
    <div className={styles.overview}>
      <div className={styles.overviewMain}>
        <h2 className={styles.h2}>Overview</h2>
        <p className={styles.body}>{product.description}</p>
        <KeyFeatures features={product.features} />
      </div>
      <div className={styles.overviewMid}>
        <WhatsNew changelog={product.changelog} />
        <RatingsSummary
          average={Number(product.rating_average)}
          count={product.rating_count}
          breakdown={product.rating_breakdown}
        />
      </div>
    </div>
  );
}

function ReviewsPanel({ product }: { product: ProductDetail }) {
  // Seeded from the server-rendered product, then a just-posted review is
  // prepended locally — product.reviews comes from a 60s-cached fetch, so
  // waiting on that to catch up would leave a fresh review invisible for up
  // to a minute even though it saved successfully.
  const [reviews, setReviews] = useState(product.reviews);

  return (
    <div className={styles.reviews}>
      <RatingsSummary
        average={Number(product.rating_average)}
        count={product.rating_count}
        breakdown={product.rating_breakdown}
      />
      <WriteReviewForm productSlug={product.slug} onPosted={(review) => setReviews((r) => [review, ...r])} />
      <ul className={styles.reviewList}>
        {reviews.map((review) => (
          <li key={review.id} className={styles.review}>
            <div className={styles.reviewHead}>
              <span className={styles.reviewAuthor}>{review.author_name || "Verified user"}</span>
              <StarRating value={review.rating} size={14} showValue={false} />
            </div>
            {review.title && <p className={styles.reviewTitle}>{review.title}</p>}
            {review.body && <p className={styles.reviewBody}>{review.body}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CompatibilityPanel({ product }: { product: ProductDetail }) {
  if (!product.compatibility.length) {
    return <p className={styles.empty}>Compatibility details coming soon.</p>;
  }
  return (
    <table className={styles.compat}>
      <tbody>
        {product.compatibility.map((row) => (
          <tr key={row.id}>
            <th scope="row">{row.label}</th>
            <td>{row.value || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DocumentationPanel({ product }: { product: ProductDetail }) {
  const doc = product.documentation;
  if (!doc) return <p className={styles.empty}>Documentation coming soon.</p>;
  return (
    <div className={styles.docs}>
      <h2 className={styles.h2}>{doc.title}</h2>
      {doc.summary && <p className={styles.docSummary}>{doc.summary}</p>}
      {doc.overview && <p className={styles.body}>{doc.overview}</p>}
      {doc.sections.map((section) => (
        <div key={section.id} className={styles.docSection}>
          <h3 className={styles.h3}>{section.title}</h3>
          <p className={styles.body}>{section.body}</p>
        </div>
      ))}
    </div>
  );
}

function SupportPanel() {
  return (
    <div className={styles.support}>
      <Icon name="help" size={28} className={styles.supportIcon} />
      <h2 className={styles.h2}>Need help?</h2>
      <p className={styles.body}>
        Our team is here to help with installation, licensing, and usage questions.
      </p>
      <Button href="/support" variant="secondary">
        Contact Support
      </Button>
    </div>
  );
}
