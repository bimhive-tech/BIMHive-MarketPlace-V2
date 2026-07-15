import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { COLLECTION_ICON_BY_SLUG } from "@/config/site";
import type { Collection } from "@/lib/types";

import styles from "./CollectionCard.module.css";

export function CollectionCard({ collection }: { collection: Collection }) {
  return (
    <Link href={`/collections/${collection.slug}`} className={styles.card}>
      <span className={styles.icon}>
        <Icon name={COLLECTION_ICON_BY_SLUG[collection.slug] ?? "grid"} size={24} />
      </span>
      <span className={styles.name}>{collection.name}</span>
      {collection.description && <span className={styles.desc}>{collection.description}</span>}
      <span className={styles.count}>
        {collection.product_count} {collection.product_count === 1 ? "product" : "products"}
      </span>
    </Link>
  );
}
