import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";

import styles from "./Pagination.module.css";

interface PaginationProps {
  page: number;
  totalPages: number;
  buildHref: (page: number) => string;
}

function pageWindow(current: number, total: number): (number | "…")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const pages = Array.from(new Set([1, total, current - 1, current, current + 1]))
    .filter((p) => p >= 1 && p <= total)
    .sort((a, b) => a - b);
  const withGaps: (number | "…")[] = [];
  pages.forEach((p, i) => {
    if (i > 0 && p - pages[i - 1] > 1) withGaps.push("…");
    withGaps.push(p);
  });
  return withGaps;
}

export function Pagination({ page, totalPages, buildHref }: PaginationProps) {
  if (totalPages <= 1) return null;

  return (
    <nav className={styles.nav} aria-label="Pagination">
      <PageLink page={page - 1} disabled={page <= 1} buildHref={buildHref} label="Previous page">
        <Icon name="chevron-left" size={16} />
      </PageLink>

      {pageWindow(page, totalPages).map((p, i) =>
        p === "…" ? (
          <span key={`gap-${i}`} className={styles.gap}>
            …
          </span>
        ) : (
          <Link
            key={p}
            href={buildHref(p)}
            className={`${styles.page} ${p === page ? styles.pageActive : ""}`}
            aria-current={p === page ? "page" : undefined}
          >
            {p}
          </Link>
        ),
      )}

      <PageLink page={page + 1} disabled={page >= totalPages} buildHref={buildHref} label="Next page">
        <Icon name="chevron-right" size={16} />
      </PageLink>
    </nav>
  );
}

function PageLink({
  page,
  disabled,
  buildHref,
  label,
  children,
}: {
  page: number;
  disabled: boolean;
  buildHref: (page: number) => string;
  label: string;
  children: React.ReactNode;
}) {
  if (disabled) {
    return (
      <span className={`${styles.arrow} ${styles.disabled}`} aria-hidden="true">
        {children}
      </span>
    );
  }
  return (
    <Link href={buildHref(page)} className={styles.arrow} aria-label={label}>
      {children}
    </Link>
  );
}
