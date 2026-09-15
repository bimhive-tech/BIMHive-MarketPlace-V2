import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ArticleView } from "@/components/ArticleView/ArticleView";
import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { getArticle } from "@/lib/api";

import styles from "./page.module.css";

interface PageProps {
  params: Promise<{ slug: string }>;
}

async function getGuide(slug: string) {
  const article = await getArticle(slug);
  return article?.kind === "knowledge" ? article : null;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const article = await getGuide((await params).slug);
  if (!article) return { title: "Guide not found" };
  return { title: article.title, description: article.summary || undefined };
}

export default async function KnowledgeArticlePage({ params }: PageProps) {
  const article = await getGuide((await params).slug);
  if (!article) notFound();

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Knowledge Base", href: "/knowledge" },
          { label: article.title },
        ]}
      />
      <ArticleView article={article} />
    </div>
  );
}
