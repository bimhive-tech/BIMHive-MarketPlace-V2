import type { Metadata } from "next";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { getDocumentationList } from "@/lib/api";

import { DocsBrowser } from "./DocsBrowser";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Documentation",
  description: "Setup guides and references for every BIMHIVE product.",
};

// No dynamic segments here, so Next would otherwise try to prerender this at
// image-build time — when the API isn't reachable yet (it starts in the same
// container, after this build step finishes). Render on-demand instead, same
// as /catalog and /products/[slug].
export const dynamic = "force-dynamic";

export default async function DocumentationIndexPage() {
  const docs = await getDocumentationList();

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Documentation" }]} />

      <header className={styles.head}>
        <h1 className={styles.title}>Documentation</h1>
        <p className={styles.sub}>Setup guides and references for every BIMHIVE product.</p>
      </header>

      {docs.length ? (
        <DocsBrowser docs={docs} />
      ) : (
        <EmptyState
          icon="document"
          title="No documentation published yet"
          text="Check back soon — setup guides for our products are on their way."
          actionLabel="Browse all products"
          actionHref="/catalog"
        />
      )}
    </div>
  );
}
