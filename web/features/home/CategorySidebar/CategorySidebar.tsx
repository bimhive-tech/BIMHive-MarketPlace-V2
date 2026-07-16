import Link from "next/link";

import { Icon, type IconName } from "@/components/Icon/Icon";
import { SellPromo } from "@/features/home/CategorySidebar/SellPromo";
import type { Category } from "@/lib/types";

import styles from "./CategorySidebar.module.css";

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

export function CategorySidebar({ categories }: { categories: Category[] }) {
  return (
    <aside className={styles.sidebar} aria-label="Categories">
      <h2 className={styles.heading}>Categories</h2>
      <ul className={styles.list}>
        <li>
          <Link href="/catalog" className={`${styles.item} ${styles.active}`}>
            <Icon name="grid" size={18} />
            All Products
          </Link>
        </li>
        {categories.map((cat) => (
          <li key={cat.id}>
            <Link href={`/catalog?category=${cat.slug}`} className={styles.item}>
              <Icon name={ICON_BY_SLUG[cat.slug] ?? "wrench"} size={18} />
              {cat.name}
            </Link>
          </li>
        ))}
      </ul>

      <SellPromo />
    </aside>
  );
}
