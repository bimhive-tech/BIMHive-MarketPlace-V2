import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleView } from "@/components/ArticleView/ArticleView";
import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { getArticle } from "@/lib/api";

import styles from "./LegalPage.module.css";

async function getLegalArticle(slug: string) {
  const article = await getArticle(slug);
  return article?.kind === "legal" ? article : null;
}

export async function legalMetadata(slug: string, fallbackTitle: string): Promise<Metadata> {
  const article = await getLegalArticle(slug);
  return { title: article?.title ?? fallbackTitle, description: article?.summary || undefined };
}

/** Shared body of /terms and /privacy — both are articles edited in /admin. */
export async function LegalPage({ slug }: { slug: string }) {
  const article = await getLegalArticle(slug);
  if (!article) notFound();

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: article.title }]} />
      <ArticleView article={article} />
    </div>
  );
}
