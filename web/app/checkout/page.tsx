import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { EmptyState } from "@/components/EmptyState/EmptyState";

import styles from "./page.module.css";

export const metadata: Metadata = { title: "Checkout" };

export default function CheckoutPage() {
  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Cart", href: "/cart" }, { label: "Checkout" }]} />
      <EmptyState
        icon="lock"
        title="Checkout is coming soon"
        text="Secure payment via Stripe and PayPal is being wired up. Your cart is saved — come back shortly to complete your purchase."
        actionLabel="Back to cart"
        actionHref="/cart"
      />
    </div>
  );
}
