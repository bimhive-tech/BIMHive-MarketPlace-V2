import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { ProductCard } from "@/components/ProductCard/ProductCard";
import { COLLECTION_ICON_BY_SLUG } from "@/config/site";
import { getCollection, getProducts } from "@/lib/api";

import styles from "./page.module.css";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const collection = await getCollection(slug);
  if (!collection) return { title: "Collection not found" };
  return { title: collection.name, description: collection.description || undefined };
}

export default async function CollectionDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const collection = await getCollection(slug);
  if (!collection) notFound();

  const products = await getProducts({ collection: slug });

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Collections", href: "/collections" }, { label: collection.name }]} />

      <header className={styles.head}>
        <span className={styles.icon}>
          <Icon name={COLLECTION_ICON_BY_SLUG[collection.slug] ?? "grid"} size={26} />
        </span>
        <div>
          <h1 className={styles.title}>{collection.name}</h1>
          {collection.description && <p className={styles.sub}>{collection.description}</p>}
        </div>
      </header>

      {products.length ? (
        <div className={styles.grid}>
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon="search"
          title="No products in this collection yet"
          text="Check back soon, or browse the full catalog in the meantime."
          actionLabel="Browse all products"
          actionHref="/catalog"
        />
      )}
    </div>
  );
}
