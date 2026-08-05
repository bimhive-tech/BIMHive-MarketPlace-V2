import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { PriceTag } from "@/components/PriceTag/PriceTag";
import { ProductBadges } from "@/components/ProductBadges/ProductBadges";
import { StarRating } from "@/components/StarRating/StarRating";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";
import { QuickAddButton } from "@/features/cart/QuickAddButton/QuickAddButton";
import { unitPrice } from "@/lib/pricing";
import type { ProductCard as ProductCardType } from "@/lib/types";

import styles from "./ProductCard.module.css";

export function ProductCard({ product }: { product: ProductCardType }) {
  return (
    <article className={`${styles.card} cardHoverTarget`}>
      <Link href={`/products/${product.slug}`} className={styles.media} aria-label={product.name}>
        {product.cover_image_url ? (
          <Image
            src={product.cover_image_url}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 100vw, 300px"
            className={styles.image}
          />
        ) : (
          <WireframeThumb seed={product.slug} label={product.name} />
        )}
        <span className={styles.badgeSlot}>
          <ProductBadges product={product} />
        </span>
      </Link>

      <div className={styles.body}>
        <Link href={`/products/${product.slug}`} className={styles.titleLink}>
          <h3 className={styles.title}>{product.name}</h3>
        </Link>
        <p className={styles.desc}>{product.short_description}</p>

        {product.membership && (
          <p className={styles.membership}>
            {product.membership.included_in_my_plan ? (
              <>
                <Icon name="check-circle" size={14} />
                In your All-Access plan
              </>
            ) : (
              <>
                <Icon name="wallet" size={14} />
                Free with {product.membership.plan_name}
              </>
            )}
          </p>
        )}

        <div className={styles.footer}>
          <div>
            <PriceTag product={product} size="lg" />
            <div className={styles.rating}>
              <StarRating value={Number(product.rating_average)} count={product.rating_count} />
            </div>
          </div>
          <QuickAddButton
            productId={product.id}
            slug={product.slug}
            name={product.name}
            coverImageUrl={product.cover_image_url}
            price={unitPrice(product)}
            currency={product.currency}
          />
        </div>
      </div>
    </article>
  );
}
