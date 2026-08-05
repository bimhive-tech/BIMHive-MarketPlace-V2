import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { ProductCard } from "@/components/ProductCard/ProductCard";
import { MEMBERSHIP_FAQ, MEMBERSHIP_HIGHLIGHTS } from "@/config/site";
import { PlanGrid } from "@/features/membership/PlanGrid/PlanGrid";
import { getMembershipPlans, getProducts } from "@/lib/api";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "All-Access membership",
  description:
    "One subscription, one license key, and the BIMHive catalogue unlocked — instead of buying each plugin separately.",
};

// Plans and their product counts change from the admin portal, and the Django
// API isn't reachable during the Docker build's frontend stage — render on
// demand, same as /catalog and /solutions.
export const dynamic = "force-dynamic";

// A taste of what's included, not the full list — the plan cards carry the
// real count and /catalog carries the browsing.
const PREVIEW_COUNT = 8;

export default async function MembershipPage() {
  const [plans, { results: products }] = await Promise.all([
    getMembershipPlans(),
    getProducts({ page: 1 }),
  ]);
  const included = products.filter((product) => product.membership).slice(0, PREVIEW_COUNT);

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "All-Access" }]} />

      <header className={styles.hero}>
        <p className={styles.eyebrow}>BIMHive All-Access</p>
        <h1 className={styles.title}>
          Stop buying plugins <span className={styles.accent}>one at a time.</span>
        </h1>
        <p className={styles.sub}>
          One subscription unlocks the tools in your plan, and one universal license key activates
          every one of them. New releases join your plan as they ship.
        </p>

        <ul className={styles.highlights}>
          {MEMBERSHIP_HIGHLIGHTS.map((highlight) => (
            <li key={highlight.title} className={styles.highlight}>
              <Icon name={highlight.icon} size={22} className={styles.highlightIcon} />
              <div>
                <p className={styles.highlightTitle}>{highlight.title}</p>
                <p className={styles.highlightText}>{highlight.text}</p>
              </div>
            </li>
          ))}
        </ul>
      </header>

      <section className={styles.section} aria-labelledby="plans-heading">
        <h2 id="plans-heading" className={styles.sectionTitle}>
          Choose your plan
        </h2>
        {plans.length > 0 ? (
          <PlanGrid plans={plans} />
        ) : (
          <EmptyState
            icon="wallet"
            title="Plans are on the way"
            text="All-Access isn't open for sign-ups just yet. In the meantime, every product is available to buy on its own."
            actionLabel="Browse the marketplace"
            actionHref="/catalog"
          />
        )}
      </section>

      {included.length > 0 && (
        <section className={styles.section} aria-labelledby="included-heading">
          <h2 id="included-heading" className={styles.sectionTitle}>
            A taste of what&apos;s included
          </h2>
          <div className={styles.productGrid}>
            {included.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </section>
      )}

      <section className={styles.section} aria-labelledby="faq-heading">
        <h2 id="faq-heading" className={styles.sectionTitle}>
          Common questions
        </h2>
        <dl className={styles.faq}>
          {MEMBERSHIP_FAQ.map((entry) => (
            <div key={entry.question} className={styles.faqItem}>
              <dt className={styles.faqQuestion}>{entry.question}</dt>
              <dd className={styles.faqAnswer}>{entry.answer}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
