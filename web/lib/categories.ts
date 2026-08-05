import type { Category, Subcategory } from "@/lib/types";

/**
 * The categories a customer actually browses by.
 *
 * The taxonomy is one root ("Revit Plugins") with subcategories under it, so
 * flat surfaces — the Solutions mega menu, /solutions, breadcrumbs — want the
 * subcategories, not the single root they all share. A root with no children
 * yet stands in for itself so those surfaces are never empty.
 */
export function browsableCategories(categories: Category[]): Subcategory[] {
  return categories.flatMap((root) => (root.children.length ? root.children : [root]));
}

/** Finds a category by slug across both levels of the tree. */
export function findCategory(categories: Category[], slug?: string): Subcategory | undefined {
  if (!slug) return undefined;
  return categories.flatMap((root) => [root, ...root.children]).find((c) => c.slug === slug);
}
