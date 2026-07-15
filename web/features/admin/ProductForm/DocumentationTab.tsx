import { Icon } from "@/components/Icon/Icon";
import type { AdminDocumentation } from "@/lib/adminApi";

import styles from "./ProductForm.module.css";

interface DocumentationTabProps {
  documentation: AdminDocumentation;
  setDocumentation: (updater: (doc: AdminDocumentation) => AdminDocumentation) => void;
}

export function DocumentationTab({ documentation: doc, setDocumentation }: DocumentationTabProps) {
  function set<K extends keyof AdminDocumentation>(key: K, value: AdminDocumentation[K]) {
    setDocumentation((d) => ({ ...d, [key]: value }));
  }

  function updateSection(i: number, patch: Partial<AdminDocumentation["sections"][number]>) {
    setDocumentation((d) => ({
      ...d,
      sections: d.sections.map((s, idx) => (idx === i ? { ...s, ...patch } : s)),
    }));
  }

  return (
    <div className={styles.panel}>
      <label className={styles.label}>
        Documentation Title
        <input
          className={styles.input}
          value={doc.title}
          onChange={(e) => set("title", e.target.value)}
          placeholder="e.g. BIM OneClick Documentation"
        />
        <span className={styles.hint}>
          Leave blank to keep the Documentation tab hidden on the product page — a title is what turns it on.
        </span>
      </label>

      <label className={styles.label}>
        Summary
        <textarea
          className={styles.textarea}
          rows={2}
          value={doc.summary}
          onChange={(e) => set("summary", e.target.value)}
          placeholder="A one-line summary, distinct from the product's short description"
        />
      </label>

      <label className={styles.label}>
        Overview
        <textarea
          className={styles.textarea}
          rows={5}
          value={doc.overview}
          onChange={(e) => set("overview", e.target.value)}
          placeholder="Getting-started overview shown above the sections below"
        />
      </label>

      <label className={styles.checkboxRow}>
        <input type="checkbox" checked={doc.is_published} onChange={(e) => set("is_published", e.target.checked)} />
        Published — visible on the product page
      </label>

      <div className={styles.features}>
        <p className={styles.label}>Sections</p>
        {doc.sections.map((section, i) => (
          <div key={i} className={styles.changelogRow}>
            <input
              className={styles.input}
              value={section.title}
              onChange={(e) => updateSection(i, { title: e.target.value })}
              placeholder="Section title, e.g. Installation"
            />
            <textarea
              className={styles.textarea}
              rows={3}
              value={section.body}
              onChange={(e) => updateSection(i, { body: e.target.value })}
              placeholder="Section content"
            />
            <button
              className={styles.iconBtn}
              aria-label="Remove section"
              onClick={() =>
                setDocumentation((d) => ({ ...d, sections: d.sections.filter((_, idx) => idx !== i) }))
              }
            >
              <Icon name="trash" size={16} />
            </button>
          </div>
        ))}
        <button
          className={styles.addBtn}
          onClick={() =>
            setDocumentation((d) => ({
              ...d,
              sections: [...d.sections, { title: "", body: "", image_url: "", sort_order: d.sections.length }],
            }))
          }
        >
          <Icon name="plus" size={14} /> Add Section
        </button>
      </div>
    </div>
  );
}
