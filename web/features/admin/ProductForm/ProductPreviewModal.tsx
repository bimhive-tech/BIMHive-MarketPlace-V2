"use client";

import { useEffect, useState } from "react";

import { Modal } from "@/components/Modal/Modal";
import { ProductBadgesInline } from "@/components/ProductBadges/ProductBadges";
import { StarRating } from "@/components/StarRating/StarRating";
import { ProductGallery } from "@/features/product/ProductGallery/ProductGallery";
import { ProductTabs } from "@/features/product/ProductTabs/ProductTabs";
import { PublisherCard } from "@/features/product/PublisherCard/PublisherCard";
import { getProductPreview } from "@/lib/adminApi";
import type { ProductDetail } from "@/lib/types";

import styles from "./ProductPreviewModal.module.css";

interface ProductPreviewModalProps {
  open: boolean;
  onClose: () => void;
  productId?: number;
  /** Scopes the fetch to the caller's own partner, for the partner portal. */
  asPartner?: boolean;
  /** True when the form has edits that haven't been saved yet. */
  dirty?: boolean;
}

/**
 * Shows the product as the storefront would render it, from the server's own
 * ProductDetailSerializer (see AdminProductPreviewView) — so what's on screen
 * is the real thing, not a lookalike built from form state.
 *
 * The buy box is deliberately not rendered: the real one reads the signed-in
 * staff member's licences and pushes to the live cart, neither of which means
 * anything here. A static stand-in shows the price the storefront would.
 */
export function ProductPreviewModal({
  open,
  onClose,
  productId,
  asPartner = false,
  dirty,
}: ProductPreviewModalProps) {
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !productId) return;
    setProduct(null);
    setError("");
    getProductPreview(productId, asPartner)
      .then(setProduct)
      .catch(() => setError("Could not load the preview."));
  }, [open, productId, asPartner]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="xl"
      title="Storefront preview"
      description={
        dirty
          ? "Showing the last saved version — save your changes to see them here."
          : "How this product looks to a customer."
      }
    >
      {!productId && <p className={styles.state}>Save the product as a draft first.</p>}
      {error && <p className={styles.state}>{error}</p>}
      {productId && !product && !error && <p className={styles.state}>Loading preview…</p>}

      {product && (
        <div className={styles.page}>
          <div className={styles.top}>
            <ProductGallery media={product.media} name={product.name} slug={product.slug} />

            <div className={styles.info}>
              <p className={styles.eyebrow}>{product.partner?.name ?? "BIMHIVE"}</p>
              <ProductBadgesInline product={product} />
              <h2 className={styles.title}>{product.name}</h2>
              <p className={styles.tagline}>{product.short_description}</p>
              <StarRating value={Number(product.rating_average)} count={product.rating_count} />

              <div className={styles.priceBox}>
                <span className={styles.price}>{product.price_label}</span>
                <span className={styles.priceNote}>
                  The live buy box is hidden in preview — it reads a real customer&apos;s licences.
                </span>
              </div>

              {product.compatibility.length > 0 && (
                <div className={styles.chips}>
                  {product.compatibility.slice(0, 3).map((row) => (
                    <span key={row.id} className={styles.chip}>
                      {row.value ? `${row.label} ${row.value}` : row.label}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <ProductTabs product={product} preview />
          <PublisherCard product={product} />
        </div>
      )}
    </Modal>
  );
}
