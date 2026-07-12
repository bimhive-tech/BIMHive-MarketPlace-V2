import { CategorySidebar } from "@/features/home/CategorySidebar/CategorySidebar";
import { CollectionsRow } from "@/features/home/CollectionsRow/CollectionsRow";
import { FeaturedGrid } from "@/features/home/FeaturedGrid/FeaturedGrid";
import { Hero } from "@/features/home/Hero/Hero";
import { TrustBar } from "@/features/home/TrustBar/TrustBar";
import { getHome } from "@/lib/api";

import styles from "./page.module.css";

export default async function HomePage() {
  const { categories, featured_products, collections } = await getHome();

  return (
    <>
      <Hero />
      <TrustBar />
      <div className={`container ${styles.body}`}>
        <div className={styles.layout}>
          <CategorySidebar categories={categories} />
          <div className={styles.main}>
            <FeaturedGrid products={featured_products} />
            <CollectionsRow collections={collections} />
          </div>
        </div>
      </div>
    </>
  );
}
