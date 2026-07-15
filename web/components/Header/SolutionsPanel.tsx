"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { CATEGORY_ICON_BY_SLUG, COLLECTION_ICON_BY_SLUG } from "@/config/site";
import type { Category, Collection } from "@/lib/types";

import styles from "./HeaderPanels.module.css";

// Caps each column so the panel stays a fixed size no matter how many
// categories or collections the admin portal adds — the highlight card below
// links to the full list on /solutions instead.
const MAX_PER_COLUMN = 6;

function byProductCount<T extends { product_count: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => b.product_count - a.product_count);
}

/** Fetched client-side (not as page/layout data) specifically so this never
 * runs during `next build`'s static prerendering — Header renders on every
 * page, and the API isn't reachable yet at that point in the Docker build. */
export function SolutionsPanel() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);

  useEffect(() => {
    fetch("/api/categories")
      .then((res) => res.json())
      .then(setCategories)
      .catch(() => setCategories([]));
    fetch("/api/collections")
      .then((res) => res.json())
      .then(setCollections)
      .catch(() => setCollections([]));
  }, []);

  const topCollections = byProductCount(collections).slice(0, MAX_PER_COLUMN);
  const topCategories = byProductCount(categories).slice(0, MAX_PER_COLUMN);

  return (
    <div className={styles.columns}>
      <div className={styles.column}>
        <p className={styles.heading}>Browse by Workflow</p>
        <ul className={styles.list}>
          {topCollections.map((collection) => (
            <li key={collection.id}>
              <Link href={`/collections/${collection.slug}`} className={styles.link}>
                <Icon name={COLLECTION_ICON_BY_SLUG[collection.slug] ?? "grid"} size={18} className={styles.icon} />
                <span>
                  <span className={styles.linkTitle}>{collection.name}</span>
                  <span className={styles.linkMeta}>{collection.product_count} products</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {collections.length > topCollections.length && (
          <Link href="/solutions" className={styles.moreLink}>
            +{collections.length - topCollections.length} more workflows
          </Link>
        )}
      </div>

      <div className={styles.column}>
        <p className={styles.heading}>Browse by Category</p>
        <ul className={styles.list}>
          {topCategories.map((category) => (
            <li key={category.id}>
              <Link href={`/catalog?category=${category.slug}`} className={styles.link}>
                <Icon name={CATEGORY_ICON_BY_SLUG[category.slug] ?? "wrench"} size={18} className={styles.icon} />
                <span>
                  <span className={styles.linkTitle}>{category.name}</span>
                  <span className={styles.linkMeta}>{category.product_count} products</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {categories.length > topCategories.length && (
          <Link href="/solutions" className={styles.moreLink}>
            +{categories.length - topCategories.length} more categories
          </Link>
        )}
      </div>

      <div className={styles.highlight}>
        <Icon name="workflow" size={28} className={styles.highlightIcon} />
        <p className={styles.highlightTitle}>Not sure where to start?</p>
        <p className={styles.highlightText}>See every collection and category in one place.</p>
        <Link href="/solutions" className={styles.highlightLink}>
          Explore all Solutions
          <Icon name="arrow-right" size={14} />
        </Link>
      </div>
    </div>
  );
}
