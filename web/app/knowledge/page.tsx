import type { Metadata } from "next";
import Link from "next/link";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { getArticles } from "@/lib/api";

import styles from "./page.module.css";

const DESCRIPTION = "Guides on Revit automation and building your own tools.";

export const metadata: Metadata = { title: "Knowledge Base", description: DESCRIPTION };

// Rendered on demand: the API isn't reachable during the image build.
export const dynamic = "force-dynamic";

export default async function KnowledgeIndexPage() {
  const articles = await getArticles("knowledge");

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Knowledge Base" }]} />

      <header className={styles.head}>
        <h1 className={styles.title}>Knowledge Base</h1>
        <p className={styles.sub}>{DESCRIPTION}</p>
      </header>

      {articles.length ? (
        <div className={styles.list}>
          {articles.map((article) => (
            <Link key={article.id} href={`/knowledge/${article.slug}`} className={styles.card}>
              <span className={styles.icon}>
                <Icon name="document" size={22} />
              </span>
              <span className={styles.cardBody}>
                <span className={styles.cardTitle}>{article.title}</span>
                {article.summary && <span className={styles.summary}>{article.summary}</span>}
              </span>
              <Icon name="chevron-right" size={18} className={styles.arrow} />
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState
          icon="document"
          title="No guides published yet"
          text="Check back soon — new guides are on their way."
          actionLabel="Browse all products"
          actionHref="/catalog"
        />
      )}
    </div>
  );
}
