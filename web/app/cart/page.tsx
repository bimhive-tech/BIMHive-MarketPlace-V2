"use client";

import Image from "next/image";
import Link from "next/link";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { Button } from "@/components/Button/Button";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";
import { formatPrice } from "@/config/site";
import { useCart } from "@/lib/cart";

import styles from "./page.module.css";

export default function CartPage() {
  const { items, removeItem, setQty, subtotal } = useCart();

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Cart" }]} />
      <h1 className={styles.title}>Shopping Cart</h1>

      {items.length === 0 ? (
        <EmptyState
          icon="cart"
          title="Your cart is empty"
          text="Browse the marketplace and add a product to get started."
          actionLabel="Browse the marketplace"
          actionHref="/catalog"
        />
      ) : (
        <div className={styles.layout}>
          <ul className={styles.items}>
            {items.map((item) => (
              <li key={item.key} className={styles.item}>
                <Link href={`/products/${item.slug}`} className={styles.thumb}>
                  {item.coverImageUrl ? (
                    <Image src={item.coverImageUrl} alt="" fill sizes="80px" className={styles.thumbImg} />
                  ) : (
                    <WireframeThumb seed={item.slug} />
                  )}
                </Link>

                <div className={styles.itemInfo}>
                  <Link href={`/products/${item.slug}`} className={styles.itemName}>
                    {item.name}
                  </Link>
                  {item.billingPeriod && (
                    <Pill tone="gold">{item.billingPeriod === "yearly" ? "Yearly" : "Monthly"}</Pill>
                  )}
                  <button className={styles.remove} onClick={() => removeItem(item.key)}>
                    <Icon name="trash" size={14} />
                    Remove
                  </button>
                </div>

                <div className={styles.qty}>
                  <button
                    className={styles.qtyBtn}
                    aria-label="Decrease quantity"
                    onClick={() => setQty(item.key, item.qty - 1)}
                  >
                    −
                  </button>
                  <span className={styles.qtyValue}>{item.qty}</span>
                  <button
                    className={styles.qtyBtn}
                    aria-label="Increase quantity"
                    onClick={() => setQty(item.key, item.qty + 1)}
                  >
                    +
                  </button>
                </div>

                <span className={styles.lineTotal}>
                  {formatPrice(item.unitPrice * item.qty, item.currency)}
                </span>
              </li>
            ))}
          </ul>

          <aside className={styles.summary}>
            <h2 className={styles.summaryTitle}>Order Summary</h2>
            <div className={styles.summaryRow}>
              <span>Subtotal</span>
              <span>{formatPrice(subtotal, items[0]?.currency ?? "USD")}</span>
            </div>
            <div className={styles.summaryRow}>
              <span>Tax</span>
              <span className={styles.muted}>Calculated at checkout</span>
            </div>
            <div className={`${styles.summaryRow} ${styles.summaryTotal}`}>
              <span>Total</span>
              <span>{formatPrice(subtotal, items[0]?.currency ?? "USD")}</span>
            </div>

            <div className={styles.guarantee}>
              <Icon name="shield" size={18} />
              <div>
                <p className={styles.guaranteeTitle}>30-Day Money Back Guarantee</p>
                <p className={styles.guaranteeText}>Not satisfied? Get a full refund within 30 days.</p>
              </div>
            </div>

            <Button href="/checkout" size="lg" fullWidth>
              Proceed to Checkout
            </Button>
            <Link href="/catalog" className={styles.continue}>
              ← Continue shopping
            </Link>
          </aside>
        </div>
      )}
    </div>
  );
}
