"use client";

import { useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { useCart } from "@/lib/cart";

import styles from "./QuickAddButton.module.css";

interface QuickAddButtonProps {
  productId: number;
  slug: string;
  name: string;
  price: number;
  currency: string;
}

/** Small circular "add to cart" button used on product cards — adds the Single User tier. */
export function QuickAddButton({ productId, slug, name, price, currency }: QuickAddButtonProps) {
  const { addItem } = useCart();
  const [added, setAdded] = useState(false);

  function onClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    addItem({
      productId,
      slug,
      name,
      tier: "single",
      tierLabel: "Single User",
      unitPrice: price,
      currency,
    });
    setAdded(true);
    window.setTimeout(() => setAdded(false), 1400);
  }

  return (
    <button
      className={`${styles.cartBtn} ${added ? styles.added : ""}`}
      aria-label={`Add ${name} to cart`}
      onClick={onClick}
    >
      <Icon name={added ? "check" : "cart"} size={18} />
    </button>
  );
}
