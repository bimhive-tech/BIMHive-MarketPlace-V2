import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { SectionHeader } from "@/components/SectionHeader/SectionHeader";
import { COLLECTION_ICON_BY_SLUG } from "@/config/site";
import type { Collection } from "@/lib/types";

import styles from "./CollectionsRow.module.css";

export function CollectionsRow({ collections }: { collections: Collection[] }) {
  if (!collections.length) return null;
  return (
    <section className={styles.section}>
      <SectionHeader title="Popular Collections" viewAllHref="/collections" viewAllLabel="View all collections" />
      <div className={styles.grid}>
        {collections.map((col) => (
          <Link key={col.id} href={`/collections/${col.slug}`} className={styles.card}>
            <span className={styles.icon}>
              <Icon name={COLLECTION_ICON_BY_SLUG[col.slug] ?? "grid"} size={22} />
            </span>
            <span className={styles.text}>
              <span className={styles.name}>{col.name}</span>
              <span className={styles.count}>{col.product_count} products</span>
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
