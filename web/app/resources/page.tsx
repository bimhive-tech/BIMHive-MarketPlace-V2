import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { ResourceCard } from "@/components/ResourceCard/ResourceCard";
import { RESOURCE_LINKS } from "@/config/site";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Resources",
  description: "Documentation, guides, and everything else to help you get the most out of BIMHIVE.",
};

export default function ResourcesPage() {
  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Resources" }]} />

      <header className={styles.head}>
        <h1 className={styles.title}>Resources</h1>
        <p className={styles.sub}>Documentation, guides, and everything else to help you get the most out of BIMHIVE.</p>
      </header>

      <div className={styles.grid}>
        {RESOURCE_LINKS.map((item) => (
          <ResourceCard
            key={item.title}
            icon={item.icon}
            title={item.title}
            description={item.description}
            href={item.href}
          />
        ))}
      </div>
    </div>
  );
}
