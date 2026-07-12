import Image from "next/image";

import { Button } from "@/components/Button/Button";

import styles from "./Hero.module.css";

export function Hero() {
  return (
    <section className={styles.hero}>
      <div className={`container ${styles.inner}`}>
        <div className={styles.copy}>
          <h1 className={styles.headline}>
            Digital tools for <span className={styles.accent}>smarter</span> construction.
          </h1>
          <p className={styles.sub}>
            Explore plugins, automation tools, and digital solutions designed for the AEC industry.
          </p>
          <div className={styles.actions}>
            <Button href="/catalog" size="lg">
              Explore Marketplace
            </Button>
            <Button href="/solutions" size="lg" variant="secondary">
              Browse Solutions
            </Button>
          </div>
        </div>

        <div className={styles.art} aria-hidden="true">
          <Image
            src="/brand/hero-background.png"
            alt=""
            width={760}
            height={520}
            className={styles.artImage}
            priority
          />
        </div>
      </div>
    </section>
  );
}
