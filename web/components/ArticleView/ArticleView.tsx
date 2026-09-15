import type { ArticleDetail } from "@/lib/types";

import styles from "./ArticleView.module.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

/** Blank lines in a section body separate paragraphs. */
function paragraphs(body: string): string[] {
  return body
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/** Renders a Knowledge Base guide or legal page: title, summary, then each
 * section's text and optional code sample. */
export function ArticleView({ article }: { article: ArticleDetail }) {
  return (
    <article className={styles.article}>
      <header className={styles.head}>
        <h1 className={styles.title}>{article.title}</h1>
        {article.summary && <p className={styles.summary}>{article.summary}</p>}
        <p className={styles.updated}>Last updated {formatDate(article.updated_at)}</p>
      </header>

      {article.sections.map((section) => (
        <section key={section.id} className={styles.section}>
          <h2 className={styles.sectionTitle}>{section.title}</h2>
          {paragraphs(section.body).map((text, i) => (
            <p key={i} className={styles.paragraph}>
              {text}
            </p>
          ))}
          {section.code && (
            <figure className={styles.codeBlock}>
              {section.code_language && <figcaption className={styles.codeLabel}>{section.code_language}</figcaption>}
              <pre className={styles.pre}>
                <code>{section.code}</code>
              </pre>
            </figure>
          )}
        </section>
      ))}
    </article>
  );
}
