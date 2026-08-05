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
  // Only present for a subscription product — lets setBillingPeriod() switch
  // monthly<->yearly entirely client-side (recomputing unitPrice) without a
  // fresh API call, the same way unitPrice itself is already just a snapshot
  // taken when the item was added.
  monthlyPrice?: number;
  yearlyPrice?: number;
  qty: number;
}

interface CartContextValue {
  items: CartItem[];
  addItem: (item: Omit<CartItem, "qty" | "key">, qty?: number) => void;
  removeItem: (key: string) => void;
  setQty: (key: string, qty: number) => void;
  setBillingPeriod: (key: string, period: "monthly" | "yearly") => void;
  clear: () => void;
  count: number;
  subtotal: number;
  /** True once prices have been re-checked against the server this session. */
  repriced: boolean;
}

/** One line's current price, from POST /api/cart/quote. */
interface CartQuote {
  slug: string;
  billing_period: BillingPeriod;
  unit_price: string;
  discount_percent: number;
  monthly_price: string | null;
  yearly_price: string | null;
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
  const [repriced, setRepriced] = useState(false);

  // Load persisted cart after mount (avoids SSR/client hydration mismatch).
  useEffect(() => {
    setItems(readStorage());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  }, [items, hydrated]);

  // Each stored price is a snapshot from when the item was added, which a
  // promotion starting or ending makes wrong. Re-ask the server once per
  // session so the cart shows what checkout will actually charge — checkout
  // prices independently either way, so this is about honesty on screen, not
  // about trusting the client.
  useEffect(() => {
    if (!hydrated || repriced) return;
    const stored = readStorage();
    if (stored.length === 0) {
      setRepriced(true);
      return;
    }
    fetch("/api/cart/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: stored.map((i) => ({ slug: i.slug, billingPeriod: i.billingPeriod ?? "" })),
      }),
    })
      .then((res) => res.json())
      .then((body: { items: CartQuote[] }) => setItems((prev) => applyQuotes(prev, body.items ?? [])))
      .catch(() => undefined)
      .finally(() => setRepriced(true));
  }, [hydrated, repriced]);

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

  function setBillingPeriod(key: string, period: "monthly" | "yearly") {
    setItems((prev) => {
      const current = prev.find((i) => i.key === key);
      if (!current) return prev;
      const price = period === "yearly" ? current.yearlyPrice : current.monthlyPrice;
      if (price == null) return prev; // not a subscription line — nothing to switch
      const newKey = `${current.productId}:${period}`;
      if (newKey === key) return prev;

      const conflict = prev.find((i) => i.key === newKey);
      if (conflict) {
        // A line for that period already exists (e.g. added separately
        // earlier) — merge quantities into it instead of ending up with two
        // rows for the same product, same as addItem()'s own merge rule.
        return prev
          .filter((i) => i.key !== key)
          .map((i) => (i.key === newKey ? { ...i, qty: i.qty + current.qty } : i));
      }
      return prev.map((i) =>
        i.key === key ? { ...i, key: newKey, billingPeriod: period, unitPrice: price } : i,
      );
    });
  }

  function clear() {
    setItems([]);
  }

  const count = useMemo(() => items.reduce((sum, i) => sum + i.qty, 0), [items]);
  const subtotal = useMemo(() => items.reduce((sum, i) => sum + i.unitPrice * i.qty, 0), [items]);

  return (
    <CartContext.Provider
      value={{ items, addItem, removeItem, setQty, setBillingPeriod, clear, count, subtotal, repriced }}
    >
      {children}
    </CartContext.Provider>
  );
}

/** Rewrites each line's prices from the server's quote. A line the server
 * didn't quote is dropped — it's no longer purchasable (unpublished, or that
 * billing interval was withdrawn), and checkout would reject the whole cart
 * over it. */
function applyQuotes(items: CartItem[], quotes: CartQuote[]): CartItem[] {
  const byKey = new Map(quotes.map((q) => [`${q.slug}:${q.billing_period}`, q]));
  return items.flatMap((item) => {
    const quote = byKey.get(`${item.slug}:${item.billingPeriod ?? ""}`);
    if (!quote) return [];
    return [
      {
        ...item,
        unitPrice: Number(quote.unit_price),
        monthlyPrice: quote.monthly_price == null ? undefined : Number(quote.monthly_price),
        yearlyPrice: quote.yearly_price == null ? undefined : Number(quote.yearly_price),
      },
    ];
  });
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within a CartProvider");
  return ctx;
}
