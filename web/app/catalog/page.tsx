import type { Metadata } from "next";
import Link from "next/link";

import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pagination } from "@/components/Pagination/Pagination";
import { ProductCard } from "@/components/ProductCard/ProductCard";
import { CATEGORY_ICON_BY_SLUG } from "@/config/site";
import { getCategories, getProducts } from "@/lib/api";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Browse all products",
  description: "Explore plugins, automation tools, and digital solutions for the AEC industry.",
};

// Must match ProductPagination.page_size in api/catalog/views.py.
const PAGE_SIZE = 24;

interface CatalogPageProps {
  searchParams: Promise<{ category?: string; q?: string; page?: string }>;
}

export default async function CatalogPage({ searchParams }: CatalogPageProps) {
  const { category, q, page: pageParam } = await searchParams;
  const page = Math.max(1, Number(pageParam) || 1);
  const [categories, { results: products, count }] = await Promise.all([
    getCategories(),
    getProducts({ category, q, page }),
  ]);
  const active = categories.find((c) => c.slug === category);
  const totalPages = Math.ceil(count / PAGE_SIZE);

  function buildHref(targetPage: number): string {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (q) params.set("q", q);
    if (targetPage > 1) params.set("page", String(targetPage));
    const qs = params.toString();
    return qs ? `/catalog?${qs}` : "/catalog";
  }

  return (
    <div className={`container ${styles.page}`}>
      <header className={styles.head}>
        <h1 className={styles.title}>{q ? `Search results for "${q}"` : active ? active.name : "All Products"}</h1>
        <p className={styles.sub}>
          {count} {count === 1 ? "product" : "products"}
          {active ? ` in ${active.name}` : q ? "" : " across the marketplace"}.
          {q && (
            <>
              {" "}
              <Link href={category ? `/catalog?category=${category}` : "/catalog"} className={styles.clearSearch}>
                Clear search
              </Link>
            </>
          )}
        </p>
      </header>

      <div className={styles.layout}>
        <aside className={styles.sidebar} aria-label="Filter by category">
          <h2 className={styles.filterHeading}>Categories</h2>
          <ul className={styles.filterList}>
            <li>
              <Link
                href={q ? `/catalog?q=${encodeURIComponent(q)}` : "/catalog"}
                className={`${styles.filter} ${!category ? styles.active : ""}`}
              >
                <Icon name="grid" size={18} />
                All Products
              </Link>
            </li>
            {categories.map((cat) => (
              <li key={cat.id}>
                <Link
                  href={`/catalog?category=${cat.slug}${q ? `&q=${encodeURIComponent(q)}` : ""}`}
                  className={`${styles.filter} ${category === cat.slug ? styles.active : ""}`}
                >
                  <Icon name={CATEGORY_ICON_BY_SLUG[cat.slug] ?? "wrench"} size={18} />
                  {cat.name}
                  <span className={styles.count}>{cat.product_count}</span>
                </Link>
              </li>
            ))}
          </ul>
        </aside>

        <div className={styles.main}>
          {products.length ? (
            <>
              <div className={styles.grid}>
                {products.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
              <Pagination page={page} totalPages={totalPages} buildHref={buildHref} />
            </>
          ) : (
            <EmptyState
              icon="search"
              title={q ? "No matching products" : "No products found"}
              text={
                q
                  ? `Nothing matched "${q}". Try a different search term.`
                  : "There are no products in this category yet. Try another category."
              }
              actionLabel="View all products"
              actionHref="/catalog"
            />
          )}
        </div>
      </div>
    </div>
  );
}
