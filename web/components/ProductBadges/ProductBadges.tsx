import type { ProductCard, ProductDetail } from "@/lib/types";

import styles from "./ProductBadges.module.css";

type BadgeSource = Pick<ProductCard, "is_new" | "is_updated" | "promotion">;

/**
 * The overlay badges on a product's image: how much is off, and whether it's
 * newly published or freshly updated.
 *
 * All three are server-decided and self-expiring — the discount lives inside
 * its promotion's window, and the freshness badges inside the day windows set
 * by NEW_PRODUCT_BADGE_DAYS / UPDATED_PRODUCT_BADGE_DAYS. Nothing here needs a
 * scheduled job to take a badge down.
 */
export function ProductBadges({ product }: { product: BadgeSource }) {
  const showFreshness = product.is_new || product.is_updated;
  if (!product.promotion && !showFreshness) return null;

  return (
    <div className={styles.badges}>
      {product.promotion && (
        <span className={`${styles.badge} ${styles.discount}`}>
          −{product.promotion.discount_percent}%
        </span>
      )}
      {product.is_new && <span className={`${styles.badge} ${styles.new}`}>New</span>}
      {product.is_updated && <span className={`${styles.badge} ${styles.updated}`}>Updated</span>}
    </div>
  );
}

/** Same badges, sized for the product detail page's title row. */
export function ProductBadgesInline({ product }: { product: ProductDetail }) {
  return (
    <div className={styles.inline}>
      <ProductBadges product={product} />
    </div>
  );
}
