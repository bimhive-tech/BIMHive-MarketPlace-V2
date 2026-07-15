import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";
import { getDocumentationList } from "@/lib/api";

import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Documentation",
  description: "Setup guides and references for every BIMHIVE product.",
};

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
        <div className={styles.list}>
          {docs.map((doc) => (
            <Link key={doc.id} href={`/docs/${doc.slug}`} className={styles.card}>
              <span className={styles.thumb}>
                {doc.product_cover_image_url ? (
                  <Image src={doc.product_cover_image_url} alt="" fill sizes="56px" className={styles.thumbImg} />
                ) : (
                  <WireframeThumb seed={doc.product_slug} />
                )}
              </span>
              <span className={styles.text}>
                <span className={styles.docTitle}>{doc.title}</span>
                {doc.summary && <span className={styles.summary}>{doc.summary}</span>}
                <span className={styles.productName}>{doc.product_name}</span>
              </span>
              <Icon name="chevron-right" size={18} className={styles.arrow} />
            </Link>
          ))}
        </div>
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
