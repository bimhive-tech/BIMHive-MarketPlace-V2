"use client";

import Link from "next/link";
import { useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { CATEGORY_ICON_BY_SLUG } from "@/config/site";
import type { Category, Subcategory } from "@/lib/types";

import styles from "./CategoryTree.module.css";

interface CategoryTreeProps {
  categories: Category[];
  /** Slug of the category currently being browsed — may be a root or a child. */
  activeSlug?: string;
  /** Carried through every link so switching category doesn't drop the search. */
  searchQuery?: string;
  showCounts?: boolean;
}

function catalogHref(slug?: string, searchQuery?: string): string {
  const params = new URLSearchParams();
  if (slug) params.set("category", slug);
  if (searchQuery) params.set("q", searchQuery);
  const qs = params.toString();
  return qs ? `/catalog?${qs}` : "/catalog";
}

function isInBranch(root: Category, slug?: string): boolean {
  return Boolean(slug) && (root.slug === slug || root.children.some((child) => child.slug === slug));
}

/**
 * The storefront's category navigation: one root per branch with its
 * subcategories nested underneath. Shared by the homepage sidebar and the
 * /catalog filter rail so both stay in step.
 */
export function CategoryTree({
  categories,
  activeSlug,
  searchQuery,
  showCounts = false,
}: CategoryTreeProps) {
  return (
    <ul className={styles.list}>
      <li>
        <Link
          href={catalogHref(undefined, searchQuery)}
          className={`${styles.item} ${!activeSlug ? styles.active : ""}`}
        >
          <Icon name="grid" size={18} />
          <span className={styles.label}>All Products</span>
        </Link>
      </li>
      {categories.map((category) => (
        <CategoryBranch
          key={category.id}
          category={category}
          activeSlug={activeSlug}
          searchQuery={searchQuery}
          showCounts={showCounts}
        />
      ))}
    </ul>
  );
}

function CategoryBranch({
  category,
  activeSlug,
  searchQuery,
  showCounts,
}: {
  category: Category;
  activeSlug?: string;
  searchQuery?: string;
  showCounts: boolean;
}) {
  const hasChildren = category.children.length > 0;
  // Open when you're already browsing inside this branch, and — since the
  // marketplace has a single root today — open by default rather than hiding
  // the only navigation there is behind a click.
  const [open, setOpen] = useState(hasChildren && (isInBranch(category, activeSlug) || !activeSlug));

  return (
    <li>
      <div className={styles.row}>
        <Link
          href={catalogHref(category.slug, searchQuery)}
          className={`${styles.item} ${activeSlug === category.slug ? styles.active : ""}`}
        >
          <Icon name={CATEGORY_ICON_BY_SLUG[category.slug] ?? "wrench"} size={18} />
          <span className={styles.label}>{category.name}</span>
          {showCounts && <span className={styles.count}>{category.product_count}</span>}
        </Link>
        {hasChildren && (
          <button
            type="button"
            className={styles.toggle}
            onClick={() => setOpen((wasOpen) => !wasOpen)}
            aria-expanded={open}
            aria-label={`${open ? "Hide" : "Show"} ${category.name} subcategories`}
          >
            <Icon name="chevron-down" size={16} className={open ? styles.chevronOpen : styles.chevron} />
          </button>
        )}
      </div>

      {hasChildren && (
        <div className={`${styles.children} ${open ? styles.childrenOpen : ""}`}>
          <ul className={styles.childList}>
            {category.children.map((child) => (
              <SubcategoryItem
                key={child.id}
                subcategory={child}
                activeSlug={activeSlug}
                searchQuery={searchQuery}
                showCounts={showCounts}
              />
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

function SubcategoryItem({
  subcategory,
  activeSlug,
  searchQuery,
  showCounts,
}: {
  subcategory: Subcategory;
  activeSlug?: string;
  searchQuery?: string;
  showCounts: boolean;
}) {
  return (
    <li>
      <Link
        href={catalogHref(subcategory.slug, searchQuery)}
        className={`${styles.item} ${styles.child} ${activeSlug === subcategory.slug ? styles.active : ""}`}
      >
        <span className={styles.label}>{subcategory.name}</span>
        {showCounts && <span className={styles.count}>{subcategory.product_count}</span>}
      </Link>
    </li>
  );
}
