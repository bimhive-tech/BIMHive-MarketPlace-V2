"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { CATEGORY_ICON_BY_SLUG } from "@/config/site";
import { browsableCategories } from "@/lib/categories";
import type { Category } from "@/lib/types";

import styles from "./HeaderPanels.module.css";

// Caps the column so the panel stays a fixed size no matter how many
// categories the admin portal adds — the highlight card below links to the
// full list on /solutions instead.
const MAX_PER_COLUMN = 6;

/** Fetched client-side (not as page/layout data) specifically so this never
 * runs during `next build`'s static prerendering — Header renders on every
 * page, and the API isn't reachable yet at that point in the Docker build. */
export function SolutionsPanel() {
  const [categoryTree, setCategoryTree] = useState<Category[]>([]);

  useEffect(() => {
    fetch("/api/categories")
      .then((res) => res.json())
      .then(setCategoryTree)
      .catch(() => setCategoryTree([]));
  }, []);

  // Subcategories, not the single root they all hang off — a one-item
  // "Revit Plugins" column tells a browsing customer nothing.
  const categories = browsableCategories(categoryTree);
  const topCategories = [...categories].sort((a, b) => b.product_count - a.product_count).slice(0, MAX_PER_COLUMN);

  return (
    <div className={styles.columns}>
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
        <p className={styles.highlightText}>See every category in one place.</p>
        <Link href="/solutions" className={styles.highlightLink}>
          Explore all Solutions
          <Icon name="arrow-right" size={14} />
        </Link>
      </div>
    </div>
  );
}
