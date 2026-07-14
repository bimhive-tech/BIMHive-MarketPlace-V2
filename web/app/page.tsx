import { CategorySidebar } from "@/features/home/CategorySidebar/CategorySidebar";
import { CollectionsRow } from "@/features/home/CollectionsRow/CollectionsRow";
import { FeaturedGrid } from "@/features/home/FeaturedGrid/FeaturedGrid";
import { Hero } from "@/features/home/Hero/Hero";
import { TrustBar } from "@/features/home/TrustBar/TrustBar";
import { getHome } from "@/lib/api";

import styles from "./page.module.css";

// Featured products/categories/collections change independently of deploys, and
// the Django API this fetches from isn't up yet during the Docker build's
// frontend stage — this must render at request time, not be prerendered at build
// time (which is also how /catalog and /products/[slug] already behave).
export const dynamic = "force-dynamic";

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
