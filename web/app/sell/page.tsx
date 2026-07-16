"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { SELL_BENEFITS } from "@/config/site";
import { me } from "@/lib/auth";
import type { User } from "@/lib/types";

import styles from "./page.module.css";

function ctaFor(user: User | null | undefined): { label: string; href: string } | null {
  if (user === undefined) return null; // still loading
  if (user === null) return { label: "Log in to apply", href: "/login?next=/sell/apply" };
  // Staff already have unrestricted access via the admin portal and must
  // never also be a partner (see catalog.partner_api.BecomeSellerView).
  if (user.is_staff) return null;
  if (!user.partner) return { label: "Become a Seller", href: "/sell/apply" };
  if (user.partner.status === "approved") return { label: "Go to Partner Dashboard", href: "/partner-portal" };
  return { label: "View Application Status", href: "/partner-portal" };
}

export default function SellPage() {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    me().then(setUser);
  }, []);

  const cta = ctaFor(user);

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <div className={`container ${styles.heroInner}`}>
          <h1 className={styles.title}>Sell on BIMHIVE</h1>
          <p className={styles.subtitle}>
            Reach thousands of AEC professionals looking for Revit plugins, Dynamo scripts, and
            BIM tools — submit your products and we'll review them before they go live.
          </p>
          {cta && (
            <Button href={cta.href} size="lg">
              {cta.label}
            </Button>
          )}
        </div>
      </section>

      <div className={`container ${styles.benefits}`}>
        {SELL_BENEFITS.map((b) => (
          <div key={b.title} className={styles.benefit}>
            <span className={styles.benefitIcon}>
              <Icon name={b.icon} size={24} />
            </span>
            <h2 className={styles.benefitTitle}>{b.title}</h2>
            <p className={styles.benefitText}>{b.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
