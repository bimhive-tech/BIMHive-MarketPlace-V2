import Image from "next/image";
import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { StarRating } from "@/components/StarRating/StarRating";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";
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
      </Link>

      <div className={styles.body}>
        <Link href={`/products/${product.slug}`} className={styles.titleLink}>
          <h3 className={styles.title}>{product.name}</h3>
        </Link>
        <p className={styles.desc}>{product.short_description}</p>

        <div className={styles.footer}>
          <div>
            <span className={styles.price}>{product.price_label}</span>
            <div className={styles.rating}>
              <StarRating value={Number(product.rating_average)} count={product.rating_count} />
            </div>
          </div>
          <button className={styles.cartBtn} aria-label={`Add ${product.name} to cart`}>
            <Icon name="cart" size={18} />
          </button>
        </div>
      </div>
    </article>
  );
}
