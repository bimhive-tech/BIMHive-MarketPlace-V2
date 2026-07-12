import Image from "next/image";

import { Button } from "@/components/Button/Button";
import { SITE } from "@/config/site";

import styles from "./Hero.module.css";

export function Hero() {
  return (
    <section className={styles.hero}>
      {/* Full brand image, shown in its entirety (contain — never cropped or stretched). */}
      <div className={styles.bg} aria-hidden="true">
        <Image
          src="/brand/hero-background.png"
          alt=""
          fill
          priority
          sizes="100vw"
          className={styles.bgImage}
        />
      </div>

      <div className={`container ${styles.inner}`}>
        <div className={styles.copy}>
          <h1 className={styles.headline}>
            Digital tools for <span className={styles.accent}>smarter</span> construction.
          </h1>
          <p className={styles.sub}>{SITE.description}</p>
          <div className={styles.actions}>
            <Button href="/catalog" size="lg">
              Explore Marketplace
            </Button>
            <Button href="/solutions" size="lg" variant="secondary">
              Browse Solutions
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
