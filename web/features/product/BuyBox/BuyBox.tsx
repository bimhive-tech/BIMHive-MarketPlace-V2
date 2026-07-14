"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon, type IconName } from "@/components/Icon/Icon";
import { QtyStepper } from "@/components/QtyStepper/QtyStepper";
import { AccountApiError, claimFreeProduct } from "@/lib/accountApi";
import { me } from "@/lib/auth";
import { formatPrice } from "@/config/site";
import { useCart } from "@/lib/cart";
import type { ProductDetail, User } from "@/lib/types";

import styles from "./BuyBox.module.css";

const ASSURANCES: { icon: IconName; title: string; sub: string }[] = [
  { icon: "download", title: "Instant Download", sub: "Get started right away" },
  { icon: "shield", title: "30-Day Money Back Guarantee", sub: "Risk-free and hassle-free" },
  { icon: "lock", title: "Secure Checkout", sub: "Your data is protected" },
];

export function BuyBox({ product }: { product: ProductDetail }) {
  if (product.is_free) return <FreeBuyBox product={product} />;
  return <PaidBuyBox product={product} />;
}

/** Checkout isn't built yet — free products skip it entirely via a direct claim. */
function FreeBuyBox({ product }: { product: ProductDetail }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [claiming, setClaiming] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    me().then(setUser);
  }, []);

  async function handleClaim() {
    setError("");
    setClaiming(true);
    try {
      await claimFreeProduct(product.slug);
      setClaimed(true);
    } catch (err) {
      setError(err instanceof AccountApiError ? err.detail : "Couldn't add this to your account.");
    } finally {
      setClaiming(false);
    }
  }

  return (
    <aside className={styles.box}>
      <div className={styles.price}>Free</div>

      {claimed ? (
        <div className={styles.actions}>
          <p className={styles.claimedNote}>It&apos;s in your account.</p>
          <Button size="lg" fullWidth href="/account/downloads">
            <Icon name="download" size={18} />
            Go to Downloads
          </Button>
        </div>
      ) : user === null ? (
        <div className={styles.actions}>
          <Button size="lg" fullWidth href={`/login?next=/products/${product.slug}`}>
            Log in to get this for free
          </Button>
        </div>
      ) : (
        <div className={styles.actions}>
          {error && <p className={styles.claimError}>{error}</p>}
          <Button size="lg" fullWidth onClick={handleClaim} disabled={claiming || user === undefined}>
            <Icon name="download" size={18} />
            {claiming ? "Adding to your account…" : "Get for Free"}
          </Button>
        </div>
      )}

      <ul className={styles.assurances}>
        {ASSURANCES.filter((a) => a.title !== "Secure Checkout").map((a) => (
          <li key={a.title} className={styles.assurance}>
            <Icon name={a.icon} size={20} className={styles.assuranceIcon} />
            <div>
              <p className={styles.assuranceTitle}>{a.title}</p>
              <p className={styles.assuranceSub}>{a.sub}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

function PaidBuyBox({ product }: { product: ProductDetail }) {
  const router = useRouter();
  const { items, addItem, setQty } = useCart();
  const cartItem = items.find((i) => i.productId === product.id);

  function handleAddToCart() {
    addItem({
      productId: product.id,
      slug: product.slug,
      name: product.name,
      unitPrice: Number(product.price),
      currency: product.currency,
    });
  }

  function handleBuyNow() {
    if (!cartItem) handleAddToCart();
    router.push("/cart");
  }

  return (
    <aside className={styles.box}>
      <div className={styles.price}>{formatPrice(product.price, product.currency)}</div>

      <div className={styles.actions}>
        {cartItem ? (
          <QtyStepper
            qty={cartItem.qty}
            onDecrease={() => setQty(cartItem.key, cartItem.qty - 1)}
            onIncrease={() => setQty(cartItem.key, cartItem.qty + 1)}
            ariaLabel={`${product.name} quantity in cart`}
            variant="full"
          />
        ) : (
          <Button size="lg" fullWidth onClick={handleAddToCart}>
            <Icon name="cart" size={18} />
            Add to Cart
          </Button>
        )}
        <Button size="lg" variant="secondary" fullWidth onClick={handleBuyNow}>
          Buy Now
        </Button>
      </div>

      <ul className={styles.assurances}>
        {ASSURANCES.map((a) => (
          <li key={a.title} className={styles.assurance}>
            <Icon name={a.icon} size={20} className={styles.assuranceIcon} />
            <div>
              <p className={styles.assuranceTitle}>{a.title}</p>
              <p className={styles.assuranceSub}>{a.sub}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
