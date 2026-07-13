"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon, type IconName } from "@/components/Icon/Icon";
import { formatPrice } from "@/config/site";
import { useCart } from "@/lib/cart";
import type { ProductDetail } from "@/lib/types";

import styles from "./BuyBox.module.css";

const ASSURANCES: { icon: IconName; title: string; sub: string }[] = [
  { icon: "download", title: "Instant Download", sub: "Get started right away" },
  { icon: "shield", title: "30-Day Money Back Guarantee", sub: "Risk-free and hassle-free" },
  { icon: "lock", title: "Secure Checkout", sub: "Your data is protected" },
];

export function BuyBox({ product }: { product: ProductDetail }) {
  const router = useRouter();
  const { addItem } = useCart();
  const hasTeam = product.team_price != null && Number(product.team_price) > 0;
  const [tier, setTier] = useState<"single" | "team">("single");
  const [added, setAdded] = useState(false);
  const activePrice = tier === "team" && hasTeam ? product.team_price! : product.price;

  function cartItem() {
    return {
      productId: product.id,
      slug: product.slug,
      name: product.name,
      tier,
      tierLabel: tier === "team" ? `Team (${product.team_seats} Seats)` : "Single User",
      unitPrice: Number(activePrice),
      currency: product.currency,
    };
  }

  function handleAddToCart() {
    addItem(cartItem());
    setAdded(true);
    window.setTimeout(() => setAdded(false), 1600);
  }

  function handleBuyNow() {
    addItem(cartItem());
    router.push("/cart");
  }

  return (
    <aside className={styles.box}>
      <div className={styles.price}>{formatPrice(activePrice, product.currency)}</div>

      <div className={styles.tierLabel}>License Type</div>
      <div className={styles.tiers} role="radiogroup" aria-label="License type">
        <button
          role="radio"
          aria-checked={tier === "single"}
          className={`${styles.tier} ${tier === "single" ? styles.tierActive : ""}`}
          onClick={() => setTier("single")}
        >
          <span className={styles.radio} aria-hidden="true" />
          <span className={styles.tierName}>Single User</span>
          <span className={styles.tierPrice}>{formatPrice(product.price, product.currency)}</span>
        </button>

        {hasTeam && (
          <button
            role="radio"
            aria-checked={tier === "team"}
            className={`${styles.tier} ${tier === "team" ? styles.tierActive : ""}`}
            onClick={() => setTier("team")}
          >
            <span className={styles.radio} aria-hidden="true" />
            <span className={styles.tierName}>Team ({product.team_seats} Seats)</span>
            <span className={styles.tierPrice}>{formatPrice(product.team_price!, product.currency)}</span>
          </button>
        )}
      </div>

      <div className={styles.actions}>
        <Button size="lg" fullWidth onClick={handleAddToCart}>
          <Icon name={added ? "check" : "cart"} size={18} />
          {added ? "Added to Cart" : "Add to Cart"}
        </Button>
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
