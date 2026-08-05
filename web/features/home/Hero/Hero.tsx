"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/Button/Button";
import { PriceTag } from "@/components/PriceTag/PriceTag";
import { ProductBadges } from "@/components/ProductBadges/ProductBadges";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";
import { SITE } from "@/config/site";
import type { ProductCard } from "@/lib/types";

import styles from "./Hero.module.css";

const AUTOPLAY_MS = 6000;

/**
 * The homepage hero: an auto-rotating showcase of the marketplace's best offers
 * (discounted products first, then featured ones — see
 * catalog.views._spotlight_products), in the same spirit as the FOMO-driven
 * carousels on marketplaces like Domestika.
 *
 * Falls back to a single static slide when there's nothing to spotlight yet
 * (an empty catalog) — never an empty carousel.
 */
export function Hero({ products }: { products: ProductCard[] }) {
  const slideCount = products.length;
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const prefersReducedMotion = usePrefersReducedMotion();

  const advance = useCallback(() => {
    setIndex((current) => (current + 1) % Math.max(slideCount, 1));
  }, [slideCount]);

  useEffect(() => {
    if (slideCount <= 1 || paused || prefersReducedMotion) return;
    const timer = setInterval(advance, AUTOPLAY_MS);
    return () => clearInterval(timer);
  }, [advance, slideCount, paused, prefersReducedMotion]);

  if (slideCount === 0) return <StaticHero />;

  return (
    <section
      className={styles.hero}
      aria-roledescription="carousel"
      aria-label="Featured products"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div className={`container ${styles.inner}`}>
        {products.map((product, slideIndex) => (
          <Slide key={product.id} product={product} active={slideIndex === index} />
        ))}
      </div>

      {slideCount > 1 && (
        <div className={styles.dots} role="tablist" aria-label="Choose a slide">
          {products.map((product, dotIndex) => (
            <button
              key={product.id}
              type="button"
              role="tab"
              aria-selected={dotIndex === index}
              aria-label={`Show ${product.name}`}
              className={`${styles.dot} ${dotIndex === index ? styles.dotActive : ""}`}
              onClick={() => setIndex(dotIndex)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function Slide({ product, active }: { product: ProductCard; active: boolean }) {
  return (
    <div className={`${styles.slide} ${active ? styles.slideActive : ""}`} aria-hidden={!active}>
      <div className={styles.copy}>
        <p className={styles.eyebrow}>{product.promotion ? "Limited-time offer" : "Featured product"}</p>
        <h1 className={styles.headline}>{product.name}</h1>
        <p className={styles.sub}>{product.short_description}</p>
        <div className={styles.priceRow}>
          <PriceTag product={product} size="lg" />
        </div>
        <div className={styles.actions}>
          <Button href={`/products/${product.slug}`} size="lg">
            View Product
          </Button>
          <Button href="/catalog" size="lg" variant="secondary">
            Explore Marketplace
          </Button>
        </div>
      </div>

      <div className={styles.mediaFrame}>
        <div className={styles.badgeSlot}>
          <ProductBadges product={product} />
        </div>
        {product.cover_image_url ? (
          <Image
            src={product.cover_image_url}
            alt={product.name}
            fill
            sizes="(max-width: 900px) 100vw, 480px"
            className={styles.media}
            priority={active}
          />
        ) : (
          <WireframeThumb seed={product.slug} label={product.name} className={styles.media} />
        )}
      </div>
    </div>
  );
}

/** The pre-catalog fallback — same headline BIMHive shipped with, minus the
 * "Browse Solutions" secondary action (a single clear next step now). */
function StaticHero() {
  return (
    <section className={styles.hero}>
      <div className={`container ${styles.inner}`}>
        <div className={`${styles.slide} ${styles.slideActive}`}>
          <div className={styles.copy}>
            <h1 className={styles.headline}>
              Digital tools for <span className={styles.accent}>smarter</span> construction.
            </h1>
            <p className={styles.sub}>{SITE.description}</p>
            <div className={styles.actions}>
              <Button href="/catalog" size="lg">
                Explore Marketplace
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = () => setReduced(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);
  return reduced;
}
