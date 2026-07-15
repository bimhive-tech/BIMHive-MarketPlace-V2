"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";
import type { DocumentationListItem } from "@/lib/types";

import styles from "./page.module.css";

export function DocsBrowser({ docs }: { docs: DocumentationListItem[] }) {
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return docs;
    return docs.filter((doc) =>
      [doc.title, doc.summary, doc.product_name].some((field) => field.toLowerCase().includes(q)),
    );
  }, [docs, query]);

  return (
    <>
      <label className={styles.search}>
        <Icon name="search" size={18} className={styles.searchIcon} />
        <input
          className={styles.searchInput}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documentation by product, guide, or keyword..."
          aria-label="Search documentation"
        />
      </label>

      {results.length ? (
        <div className={styles.grid}>
          {results.map((doc) => (
            <Link key={doc.id} href={`/docs/${doc.slug}`} className={styles.card}>
              <span className={styles.thumb}>
                {doc.product_cover_image_url ? (
                  <Image src={doc.product_cover_image_url} alt="" fill sizes="64px" className={styles.thumbImg} />
                ) : (
                  <WireframeThumb seed={doc.product_slug} />
                )}
              </span>
              <span className={styles.cardBody}>
                <span className={styles.productName}>{doc.product_name}</span>
                <span className={styles.docTitle}>{doc.title}</span>
                {doc.summary && <span className={styles.summary}>{doc.summary}</span>}
              </span>
              <Icon name="chevron-right" size={18} className={styles.arrow} />
            </Link>
          ))}
        </div>
      ) : (
        <div className={styles.noResults}>
          <Icon name="search" size={28} className={styles.noResultsIcon} />
          <p className={styles.noResultsTitle}>No matching documentation</p>
          <p className={styles.noResultsText}>Nothing matched &quot;{query}&quot;. Try a different product name or keyword.</p>
          <button type="button" className={styles.clearBtn} onClick={() => setQuery("")}>
            Clear search
          </button>
        </div>
      )}
    </>
  );
}
