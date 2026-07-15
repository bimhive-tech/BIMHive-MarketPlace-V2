import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { Icon } from "@/components/Icon/Icon";
import { getDocumentation } from "@/lib/api";

import styles from "./page.module.css";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const doc = await getDocumentation(slug);
  if (!doc) return { title: "Documentation not found" };
  return { title: doc.title, description: doc.summary || undefined };
}

export default async function DocumentationDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const doc = await getDocumentation(slug);
  if (!doc) notFound();

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Documentation", href: "/docs" },
          { label: doc.title },
        ]}
      />

      <Link href={`/products/${doc.product_slug}`} className={styles.productLink}>
        <Icon name="chevron-left" size={14} />
        {doc.product_name}
      </Link>

      <header className={styles.head}>
        <h1 className={styles.title}>{doc.title}</h1>
        {doc.summary && <p className={styles.summary}>{doc.summary}</p>}
      </header>

      {doc.overview && <p className={styles.overview}>{doc.overview}</p>}

      {doc.sections.map((section) => (
        <section key={section.id} className={styles.section}>
          <h2 className={styles.sectionTitle}>{section.title}</h2>
          <p className={styles.sectionBody}>{section.body}</p>
        </section>
      ))}
    </div>
  );
}
