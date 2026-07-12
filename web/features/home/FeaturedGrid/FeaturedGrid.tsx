import { ProductCard } from "@/components/ProductCard/ProductCard";
import { SectionHeader } from "@/components/SectionHeader/SectionHeader";
import type { ProductCard as ProductCardType } from "@/lib/types";

import styles from "./FeaturedGrid.module.css";

export function FeaturedGrid({ products }: { products: ProductCardType[] }) {
  return (
    <section>
      <SectionHeader title="Featured Products" viewAllHref="/catalog" viewAllLabel="View all products" />
      <div className={styles.grid}>
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </section>
  );
}
