import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { CATEGORY_ICON_BY_SLUG } from "@/config/site";
import type { Subcategory } from "@/lib/types";

import styles from "./CategoryCard.module.css";

/** Renders either level of the taxonomy — `Category` is a `Subcategory` plus
 * its children, which this card doesn't show. */
export function CategoryCard({ category }: { category: Subcategory }) {
  return (
    <Link href={`/catalog?category=${category.slug}`} className={styles.card}>
      <span className={styles.icon}>
        <Icon name={CATEGORY_ICON_BY_SLUG[category.slug] ?? "wrench"} size={24} />
      </span>
      <span className={styles.name}>{category.name}</span>
      {category.description && <span className={styles.desc}>{category.description}</span>}
      <span className={styles.count}>
        {category.product_count} {category.product_count === 1 ? "product" : "products"}
      </span>
    </Link>
  );
}
