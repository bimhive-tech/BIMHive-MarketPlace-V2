"use client";

import { useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { QtyStepper } from "@/components/QtyStepper/QtyStepper";
import { useCart } from "@/lib/cart";

import styles from "./QuickAddButton.module.css";

interface QuickAddButtonProps {
  productId: number;
  slug: string;
  name: string;
  price: number;
  currency: string;
}

/** Circular "add to cart" button used on product cards — becomes a qty stepper once the product is in the cart. */
export function QuickAddButton({ productId, slug, name, price, currency }: QuickAddButtonProps) {
  const { items, addItem, setQty } = useCart();
  const [added, setAdded] = useState(false);
  const cartItem = items.find((i) => i.productId === productId);

  function onClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    addItem({
      productId,
      slug,
      name,
      unitPrice: price,
      currency,
    });
    setAdded(true);
    window.setTimeout(() => setAdded(false), 1400);
  }

  if (cartItem) {
    return (
      <QtyStepper
        qty={cartItem.qty}
        onDecrease={() => setQty(cartItem.key, cartItem.qty - 1)}
        onIncrease={() => setQty(cartItem.key, cartItem.qty + 1)}
        ariaLabel={`${name} quantity in cart`}
        variant="compact"
      />
    );
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
