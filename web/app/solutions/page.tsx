import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { CategoryCard } from "@/components/CategoryCard/CategoryCard";
import { CollectionCard } from "@/components/CollectionCard/CollectionCard";
import { getCategories, getCollections } from "@/lib/api";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Solutions",
  description: "Find the right BIMHIVE tools for your workflow, by collection or by category.",
};

// No dynamic segments here, so Next would otherwise try to prerender this at
// image-build time — when the API isn't reachable yet (it starts in the same
// container, after this build step finishes). Render on-demand instead, same
// as /catalog, /collections, and /docs.
export const dynamic = "force-dynamic";

export default async function SolutionsPage() {
  const [categories, collections] = await Promise.all([getCategories(), getCollections()]);

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Solutions" }]} />

      <header className={styles.head}>
        <h1 className={styles.title}>Solutions</h1>
        <p className={styles.sub}>Find the right tools for your workflow, by collection or by category.</p>
      </header>

      {collections.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Browse by Workflow</h2>
          <div className={styles.grid}>
            {collections.map((collection) => (
              <CollectionCard key={collection.id} collection={collection} />
            ))}
          </div>
        </section>
      )}

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Browse by Category</h2>
        <div className={styles.grid}>
          {categories.map((category) => (
            <CategoryCard key={category.id} category={category} />
          ))}
        </div>
      </section>
    </div>
  );
}
