"use client";

/**
 * Client-side cart: persisted to localStorage. Real functionality (not a
 * placeholder) — items survive a refresh; the header badge and /cart page both
 * read from this context. Checkout itself is not wired yet (see /checkout).
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "bimhive.cart.v1";

// "" = one-time price (every item before this field existed, and any
// non-subscription product) — matches licensing.ProductPurchase.BillingPeriod
// on the backend so a cart item's billingPeriod can be sent straight through
// to checkout unchanged.
export type BillingPeriod = "" | "monthly" | "yearly";

export interface CartItem {
  // productId + billingPeriod — a monthly and a yearly line for the same
  // product are distinct line items, not one that silently merges (they
  // have different prices and durations).
  key: string;
  productId: number;
  slug: string;
  name: string;
  // Optional so carts persisted before this field existed still parse fine —
  // the cart page falls back to the wireframe art when it's missing.
  coverImageUrl?: string;
  unitPrice: number;
  currency: string;
  // Optional so carts persisted before this field existed still parse fine —
  // missing means "" (one-time), same as an explicit "".
  billingPeriod?: BillingPeriod;
  qty: number;
}

interface CartContextValue {
  items: CartItem[];
  addItem: (item: Omit<CartItem, "qty" | "key">, qty?: number) => void;
  removeItem: (key: string) => void;
  setQty: (key: string, qty: number) => void;
  clear: () => void;
  count: number;
  subtotal: number;
}

const CartContext = createContext<CartContextValue | null>(null);

function readStorage(): CartItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as CartItem[]) : [];
  } catch {
    return [];
  }
}

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Load persisted cart after mount (avoids SSR/client hydration mismatch).
  useEffect(() => {
    setItems(readStorage());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items, hydrated]);

  function addItem(item: Omit<CartItem, "qty" | "key">, qty = 1) {
    const key = `${item.productId}:${item.billingPeriod ?? ""}`;
    setItems((prev) => {
      const existing = prev.find((i) => i.key === key);
      if (existing) {
        return prev.map((i) => (i.key === key ? { ...i, qty: i.qty + qty } : i));
      }
      return [...prev, { ...item, key, qty }];
    });
  }

  function removeItem(key: string) {
    setItems((prev) => prev.filter((i) => i.key !== key));
  }

  function setQty(key: string, qty: number) {
    if (qty < 1) return removeItem(key);
    setItems((prev) => prev.map((i) => (i.key === key ? { ...i, qty } : i)));
  }

  function clear() {
    setItems([]);
  }

  const count = useMemo(() => items.reduce((sum, i) => sum + i.qty, 0), [items]);
  const subtotal = useMemo(() => items.reduce((sum, i) => sum + i.unitPrice * i.qty, 0), [items]);

  return (
    <CartContext.Provider value={{ items, addItem, removeItem, setQty, clear, count, subtotal }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within a CartProvider");
  return ctx;
}
