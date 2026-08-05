import { CategoryTree } from "@/components/CategoryTree/CategoryTree";
import { SellPromo } from "@/features/home/CategorySidebar/SellPromo";
import type { Category } from "@/lib/types";

import styles from "./CategorySidebar.module.css";

export function CategorySidebar({ categories }: { categories: Category[] }) {
  return (
    <aside className={styles.sidebar} aria-label="Categories">
      <h2 className={styles.heading}>Categories</h2>
      <CategoryTree categories={categories} />
      <SellPromo />
    </aside>
  );
}
