import type { Metadata } from "next";
import Link from "next/link";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon, type IconName } from "@/components/Icon/Icon";
import { ProductCard } from "@/components/ProductCard/ProductCard";
import { getCategories, getProducts } from "@/lib/api";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Browse all products",
  description: "Explore plugins, automation tools, and digital solutions for the AEC industry.",
};

const ICON_BY_SLUG: Record<string, IconName> = {
  "revit-plugins": "puzzle",
  "automation-tools": "bolt",
  "dynamo-scripts": "workflow",
  "bim-libraries": "library",
  templates: "template",
  "training-courses": "graduation-cap",
  integrations: "plug",
  "other-tools": "wrench",
};

interface CatalogPageProps {
  searchParams: Promise<{ category?: string }>;
}

export default async function CatalogPage({ searchParams }: CatalogPageProps) {
  const { category } = await searchParams;
  const [categories, products] = await Promise.all([
    getCategories(),
    getProducts({ category }),
  ]);
  const active = categories.find((c) => c.slug === category);

  return (
    <div className={`container ${styles.page}`}>
      <header className={styles.head}>
        <h1 className={styles.title}>{active ? active.name : "All Products"}</h1>
        <p className={styles.sub}>
          {products.length} {products.length === 1 ? "product" : "products"}
          {active ? ` in ${active.name}` : " across the marketplace"}.
        </p>
      </header>

      <div className={styles.layout}>
        <aside className={styles.sidebar} aria-label="Filter by category">
          <h2 className={styles.filterHeading}>Categories</h2>
          <ul className={styles.filterList}>
            <li>
              <Link href="/catalog" className={`${styles.filter} ${!category ? styles.active : ""}`}>
                <Icon name="grid" size={18} />
                All Products
              </Link>
            </li>
            {categories.map((cat) => (
              <li key={cat.id}>
                <Link
                  href={`/catalog?category=${cat.slug}`}
                  className={`${styles.filter} ${category === cat.slug ? styles.active : ""}`}
                >
                  <Icon name={ICON_BY_SLUG[cat.slug] ?? "wrench"} size={18} />
                  {cat.name}
                  <span className={styles.count}>{cat.product_count}</span>
                </Link>
              </li>
            ))}
          </ul>
        </aside>

        <div className={styles.main}>
          {products.length ? (
            <div className={styles.grid}>
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon="search"
              title="No products found"
              text="There are no products in this category yet. Try another category."
              actionLabel="View all products"
              actionHref="/catalog"
            />
          )}
        </div>
      </div>
    </div>
  );
}
