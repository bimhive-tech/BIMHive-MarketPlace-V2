import { formatPrice } from "@/config/site";
import type { ProductCard } from "@/lib/types";

import styles from "./PriceTag.module.css";

type PriceSource = Pick<
  ProductCard,
  | "price"
  | "price_label"
  | "original_price_label"
  | "currency"
  | "is_subscription"
  | "monthly_price"
  | "yearly_price"
  | "promotion"
>;

/**
 * A product's price, with a higher "was" price struck through beside it when
 * there is one: the list price while a promotion runs, otherwise the product's
 * own display-only original price (e.g. "~~$29.00~~ Free").
 *
 * Every figure comes from the server, never from multiplying on the client —
 * the same numbers checkout will charge.
 */
export function PriceTag({ product, size = "md" }: { product: PriceSource; size?: "md" | "lg" }) {
  const { promotion } = product;
  const wasLabel = promotion ? product.price_label : product.original_price_label;

  if (!wasLabel) {
    return <span className={`${styles.price} ${styles[size]}`}>{product.price_label}</span>;
  }

  return (
    <span className={styles.group}>
      <span className={`${styles.price} ${styles.sale} ${styles[size]}`}>
        {promotion ? salePriceLabel(product) : product.price_label}
      </span>
      <s className={styles.was}>{wasLabel}</s>
    </span>
  );
}

/** Mirrors Product.price_label on the server, but reading the promotion's
 * discounted figures — a subscription advertises its interval, a one-time
 * product just its price. */
function salePriceLabel(product: PriceSource): string {
  const { promotion } = product;
  if (!promotion) return product.price_label;
  if (product.is_subscription) {
    if (promotion.monthly_price) return `${formatPrice(promotion.monthly_price, product.currency)}/mo`;
    if (promotion.yearly_price) return `${formatPrice(promotion.yearly_price, product.currency)}/yr`;
  }
  return formatPrice(promotion.price, product.currency);
}
