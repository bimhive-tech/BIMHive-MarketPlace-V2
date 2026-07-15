import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { CollectionCard } from "@/components/CollectionCard/CollectionCard";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { getCollections } from "@/lib/api";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Collections",
  description: "Curated bundles of BIMHIVE products, grouped around a workflow or need.",
};

export default async function CollectionsPage() {
  const collections = await getCollections();

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Collections" }]} />

      <header className={styles.head}>
        <h1 className={styles.title}>Collections</h1>
        <p className={styles.sub}>Curated bundles of tools, grouped around a workflow or need.</p>
      </header>

      {collections.length ? (
        <div className={styles.grid}>
          {collections.map((collection) => (
            <CollectionCard key={collection.id} collection={collection} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon="library"
          title="No collections yet"
          text="Check back soon — curated product bundles are on their way."
          actionLabel="Browse all products"
          actionHref="/catalog"
        />
      )}
    </div>
  );
}
