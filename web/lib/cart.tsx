"use client";

/**
 * Client-side cart: persisted to localStorage. Real functionality (not a
 * placeholder) — items survive a refresh; the header badge and /cart page both
 * read from this context. Checkout itself is not wired yet (see /checkout).
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "bimhive.cart.v1";

export interface CartItem {
  key: string; // `${productId}-${tier}`
  productId: number;
  slug: string;
  name: string;
  tier: "single" | "team";
  tierLabel: string;
  unitPrice: number;
  currency: string;
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
    const key = `${item.productId}-${item.tier}`;
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
