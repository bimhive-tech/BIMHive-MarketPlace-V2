"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { CompatibilityTab } from "@/features/admin/ProductForm/CompatibilityTab";
import { DocumentationTab } from "@/features/admin/ProductForm/DocumentationTab";
import { FilesTab } from "@/features/admin/ProductForm/FilesTab";
import { InstallerBuildTab } from "@/features/admin/ProductForm/InstallerBuildTab";
import { MediaTab } from "@/features/admin/ProductForm/MediaTab";
import {
  AdminApiError,
  createProduct,
  deleteProduct,
  getAdminOptions,
  getAdminProduct,
  updateProduct,
  type AdminChangelogItem,
  type AdminCompatibilityItem,
  type AdminDocumentation,
  type AdminOptions,
  type AdminProductFeature,
  type AdminProductFile,
  type AdminProductMedia,
} from "@/lib/adminApi";

import styles from "./ProductForm.module.css";

type TabId = "info" | "media" | "pricing" | "files" | "installer" | "compatibility" | "documentation" | "seo";
const TABS: { id: TabId; label: string }[] = [
  { id: "info", label: "Product Information" },
  { id: "media", label: "Media & Previews" },
  { id: "pricing", label: "Pricing & License" },
  { id: "files", label: "Files & Downloads" },
  { id: "installer", label: "Installer Build" },
  { id: "compatibility", label: "Compatibility" },
  { id: "documentation", label: "Documentation" },
  { id: "seo", label: "SEO & Settings" },
];

const EMPTY_DOCUMENTATION: AdminDocumentation = {
  title: "",
  summary: "",
  overview: "",
  is_published: false,
  sections: [],
};

const MAX_SHORT = 150;
const MAX_DESC = 5000;

const SAVE_ACTION_LABEL: Record<string, string> = {
  draft: "Save Draft",
  pending: "Submit for Review",
  published: "Publish",
  rejected: "Save",
};

const EMPTY_FORM = {
  name: "",
  short_description: "",
  description: "",
  type: "plugin",
  category: "",
  partner: "",
  product_code: "",
  price: "0",
  default_trial_days: "30",
  status: "published",
  rejection_note: "",
  visibility: "public",
  is_featured: false,
  seo_title: "",
  seo_description: "",
};

interface ProductFormProps {
  productId?: number;
  /** "partner" restricts the Status options to draft/pending (only staff can
   * publish or reject — see catalog.admin_api.AdminProductDetailSerializer),
   * hides the Partner picker in favor of the caller's own org, and routes
   * saves/redirects through /partner-portal instead of /admin-portal. */
  mode?: "admin" | "partner";
  /** Shown in place of the Partner dropdown in partner mode. */
  partnerName?: string;
}

export function ProductForm({ productId, mode = "admin", partnerName }: ProductFormProps) {
  const router = useRouter();
  const asPartner = mode === "partner";
  const basePath = asPartner ? "/partner-portal" : "/admin-portal";
  const isEdit = productId != null;
  const [options, setOptions] = useState<AdminOptions | null>(null);
  const [tab, setTab] = useState<TabId>("info");
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(!isEdit);
  const [downloadCount, setDownloadCount] = useState(0);
  // Starts as the route's productId (edit page) and is filled in once an
  // unsaved "add new" form silently auto-saves as a draft on first upload —
  // see ensureSaved() below.
  const [savedId, setSavedId] = useState<number | undefined>(productId);

  const [form, setForm] = useState(() => ({
    ...EMPTY_FORM,
    status: mode === "partner" ? "pending" : "published",
  }));
  const [tags, setTags] = useState<number[]>([]);
  const [features, setFeatures] = useState<AdminProductFeature[]>([
    { title: "", description: "", icon: "", sort_order: 0 },
  ]);
  const [media, setMedia] = useState<AdminProductMedia[]>([]);
  const [changelog, setChangelog] = useState<AdminChangelogItem[]>([]);
  const [compatibility, setCompatibility] = useState<AdminCompatibilityItem[]>([]);
  const [documentation, setDocumentation] = useState<AdminDocumentation>(EMPTY_DOCUMENTATION);
  const [files, setFiles] = useState<AdminProductFile[]>([]);

  useEffect(() => {
    getAdminOptions().then(setOptions).catch(() => setError("Could not load form options."));
  }, []);

  useEffect(() => {
    if (!isEdit) return;
    getAdminProduct(productId!, asPartner)
      .then((p) => {
        setForm({
          name: p.name,
          short_description: p.short_description,
          description: p.description,
          type: p.type,
          category: String(p.category),
          partner: String(p.partner),
          product_code: p.product_code,
          price: p.price,
          default_trial_days: String(p.default_trial_days),
          status: p.status,
          rejection_note: p.rejection_note,
          visibility: p.visibility,
          is_featured: p.is_featured,
          seo_title: p.seo_title,
          seo_description: p.seo_description,
        });
        setTags(p.tags);
        setFeatures(p.features.length ? p.features : [{ title: "", description: "", icon: "", sort_order: 0 }]);
        setMedia(p.media);
        setChangelog(p.changelog);
        setCompatibility(p.compatibility);
        setDocumentation(p.documentation ?? EMPTY_DOCUMENTATION);
        setFiles(p.files);
        setDownloadCount(p.download_count);
        setLoaded(true);
      })
      .catch(() => setError("Could not load this product."));
  }, [isEdit, productId]);

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function setFeature(i: number, key: keyof AdminProductFeature, value: string) {
    setFeatures((list) => list.map((f, idx) => (idx === i ? { ...f, [key]: value } : f)));
  }

  function toggleTag(id: number) {
    setTags((t) => (t.includes(id) ? t.filter((x) => x !== id) : [...t, id]));
  }

  function buildPayload(status: string) {
    return {
      name: form.name.trim(),
      short_description: form.short_description.trim(),
      description: form.description.trim(),
      type: form.type,
      category: Number(form.category),
      // Partner mode never shows this field — the server force-scopes it to
      // the caller's own org and ignores anything sent here (see
      // AdminProductDetailSerializer.validate), so there's nothing to send.
      ...(mode === "admin" ? { partner: Number(form.partner) } : {}),
      product_code: form.product_code.trim(),
      price: form.price || "0",
      default_trial_days: Number(form.default_trial_days) || 30,
      status,
      // Only staff can write this (see validate()); a partner's edits to it
      // are silently ignored server-side, so there's no point sending it.
      ...(mode === "admin" ? { rejection_note: form.rejection_note } : {}),
      visibility: form.visibility,
      is_featured: form.is_featured,
      seo_title: form.seo_title.trim(),
      seo_description: form.seo_description.trim(),
      tags,
      features: features.filter((f) => f.title.trim()).map((f, i) => ({ ...f, sort_order: i })),
      media: media.map((m, i) => ({ ...m, sort_order: i })),
      changelog: changelog.filter((c) => c.version.trim()).map((c, i) => ({ ...c, sort_order: i })),
      compatibility: compatibility.filter((c) => c.label.trim()).map((c, i) => ({ ...c, sort_order: i })),
      // A blank title means "no documentation yet" — send null so the backend
      // deletes any existing row instead of rejecting an empty-but-required title.
      documentation: documentation.title.trim()
        ? {
            ...documentation,
            sections: documentation.sections
              .filter((s) => s.title.trim())
              .map((s, i) => ({ ...s, sort_order: i })),
          }
        : null,
    };
  }

  async function submit(status: string) {
    setError("");
    if (!form.name.trim() || !form.short_description.trim() || !form.description.trim()) {
      setError("Name, short description, and full description are required.");
      setTab("info");
      return;
    }
    if (!form.category || (mode === "admin" && !form.partner)) {
      setError(mode === "admin" ? "Please choose a category and a partner." : "Please choose a category.");
      setTab("info");
      return;
    }
    setSaving(true);
    try {
      if (savedId != null) {
        await updateProduct(savedId, buildPayload(status), asPartner);
      } else {
        const created = await createProduct(buildPayload(status), asPartner);
        router.push(`${basePath}/products/${created.id}/edit`);
        router.refresh();
        return;
      }
      router.push(`${basePath}/products`);
      router.refresh();
    } catch (err) {
      setError(err instanceof AdminApiError ? err.detail : "Could not save the product.");
      if (err instanceof AdminApiError && err.fields.product_code) setTab("pricing");
    } finally {
      setSaving(false);
    }
  }

  // Files/media uploads need a real product id to attach to. If the form
  // hasn't been saved yet, silently create it as a draft (without navigating
  // away, so in-progress edits and tab state survive) and reuse that id for
  // every upload from then on.
  async function ensureSaved(): Promise<number | null> {
    if (savedId != null) return savedId;
    if (!form.name.trim() || !form.short_description.trim() || !form.description.trim()) {
      setError("Name, short description, and full description are required before uploading files.");
      setTab("info");
      return null;
    }
    if (!form.category || (mode === "admin" && !form.partner)) {
      setError(
        mode === "admin"
          ? "Please choose a category and a partner before uploading files."
          : "Please choose a category before uploading files.",
      );
      setTab("info");
      return null;
    }
    setError("");
    try {
      const created = await createProduct(buildPayload("draft"), asPartner);
      setSavedId(created.id);
      return created.id;
    } catch (err) {
      setError(err instanceof AdminApiError ? err.detail : "Could not save the product.");
      return null;
    }
  }

  async function onDelete() {
    if (!savedId) return;
    const confirmed = window.confirm(`Delete "${form.name}"? This cannot be undone.`);
    if (!confirmed) return;
    setDeleting(true);
    try {
      await deleteProduct(savedId, asPartner);
      router.push(`${basePath}/products`);
      router.refresh();
    } catch {
      setError("Could not delete this product.");
      setDeleting(false);
    }
  }

  if (isEdit && !loaded) {
    return <p className={styles.loading}>Loading product…</p>;
  }

  return (
    <div className={styles.wrap}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>{isEdit ? `Edit ${form.name || "Product"}` : "Add New Product"}</h1>
          <p className={styles.sub}>
            {isEdit ? "Update this product's details." : "Create a new product to sell on the BIMHIVE marketplace."}
          </p>
        </div>
        <div className={styles.headActions}>
          {savedId != null && (
            <button className={styles.deleteBtn} disabled={deleting} onClick={onDelete}>
              {deleting ? "Deleting…" : "Delete"}
            </button>
          )}
          <button className={styles.secondaryBtn} disabled={saving} onClick={() => submit("draft")}>
            Save as Draft
          </button>
          {/* Respects whatever's picked in the Status dropdown (Publishing panel) —
              previously this always forced "pending" regardless of that selection,
              so choosing "Published" there had no effect and products could never
              actually go live from this form. */}
          <button className={styles.primaryBtn} disabled={saving} onClick={() => submit(form.status)}>
            {saving ? "Saving…" : SAVE_ACTION_LABEL[form.status] ?? "Save"}
          </button>
        </div>
      </header>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.layout}>
        <div className={styles.formCol}>
          <div className={styles.tabs} role="tablist">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                className={`${styles.tab} ${tab === t.id ? styles.tabActive : ""}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === "info" && (
            <div className={styles.panel}>
              <label className={styles.label}>
                Product Name <span className={styles.req}>*</span>
                <input className={styles.input} value={form.name} maxLength={100} onChange={(e) => set("name", e.target.value)} placeholder="Enter product name" />
              </label>

              <label className={styles.label}>
                Short Description <span className={styles.req}>*</span>
                <textarea className={styles.textarea} rows={2} maxLength={MAX_SHORT} value={form.short_description} onChange={(e) => set("short_description", e.target.value)} placeholder="A short tagline that describes your product in one line" />
                <span className={styles.counter}>{form.short_description.length}/{MAX_SHORT}</span>
              </label>

              <label className={styles.label}>
                Full Description <span className={styles.req}>*</span>
                <textarea className={styles.textarea} rows={6} maxLength={MAX_DESC} value={form.description} onChange={(e) => set("description", e.target.value)} placeholder="Describe your product, its features, benefits, and how it helps users." />
                <span className={styles.counter}>{form.description.length}/{MAX_DESC}</span>
              </label>

              <div className={styles.row}>
                <label className={styles.label}>
                  Category <span className={styles.req}>*</span>
                  <select className={styles.input} value={form.category} onChange={(e) => set("category", e.target.value)}>
                    <option value="">Select a category</option>
                    {options?.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </label>
                {mode === "partner" ? (
                  <label className={styles.label}>
                    Partner
                    <input className={styles.input} value={partnerName ?? ""} disabled />
                  </label>
                ) : (
                  <label className={styles.label}>
                    Partner <span className={styles.req}>*</span>
                    <select className={styles.input} value={form.partner} onChange={(e) => set("partner", e.target.value)}>
                      <option value="">Select a partner</option>
                      {options?.partners.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                  </label>
                )}
              </div>

              <div className={styles.label}>
                Tags
                <div className={styles.tagCloud}>
                  {options?.tags.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      className={`${styles.tagChip} ${tags.includes(t.id) ? styles.tagChipActive : ""}`}
                      onClick={() => toggleTag(t.id)}
                    >
                      {t.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className={styles.features}>
                <p className={styles.label}>Key Features</p>
                {features.map((f, i) => (
                  <div key={i} className={styles.featureRow}>
                    <input className={styles.input} value={f.title} onChange={(e) => setFeature(i, "title", e.target.value)} placeholder="e.g. Automate sheet creation" />
                    <input className={styles.input} value={f.description} onChange={(e) => setFeature(i, "description", e.target.value)} placeholder="Save time by automating repetitive tasks." />
                    <button className={styles.iconBtn} aria-label="Remove feature" onClick={() => setFeatures((l) => l.filter((_, idx) => idx !== i))}>
                      <Icon name="trash" size={16} />
                    </button>
                  </div>
                ))}
                <button className={styles.addBtn} onClick={() => setFeatures((l) => [...l, { title: "", description: "", icon: "", sort_order: l.length }])}>
                  <Icon name="plus" size={14} /> Add Feature
                </button>
              </div>

              <div className={styles.features}>
                <p className={styles.label}>What&apos;s New (Changelog)</p>
                {changelog.map((c, i) => (
                  <div key={i} className={styles.changelogRow}>
                    <input
                      className={styles.input}
                      value={c.version}
                      onChange={(e) =>
                        setChangelog((l) => l.map((row, idx) => (idx === i ? { ...row, version: e.target.value } : row)))
                      }
                      placeholder="Version, e.g. 2.1.0"
                    />
                    <textarea
                      className={styles.textarea}
                      rows={2}
                      value={c.notes}
                      onChange={(e) =>
                        setChangelog((l) => l.map((row, idx) => (idx === i ? { ...row, notes: e.target.value } : row)))
                      }
                      placeholder="One bullet per line"
                    />
                    <button
                      className={styles.iconBtn}
                      aria-label="Remove entry"
                      onClick={() => setChangelog((l) => l.filter((_, idx) => idx !== i))}
                    >
                      <Icon name="trash" size={16} />
                    </button>
                  </div>
                ))}
                <button
                  className={styles.addBtn}
                  onClick={() =>
                    setChangelog((l) => [...l, { version: "", released_at: null, notes: "", sort_order: l.length }])
                  }
                >
                  <Icon name="plus" size={14} /> Add Release
                </button>
              </div>
            </div>
          )}

          {tab === "media" && (
            <MediaTab
              media={media}
              setMedia={setMedia}
              productId={savedId}
              ensureSaved={ensureSaved}
              asPartner={asPartner}
            />
          )}

          {tab === "pricing" && (
            <div className={styles.panel}>
              <label className={styles.label}>
                Product Code {downloadCount > 0 && <Icon name="lock" size={14} />}
                <input
                  className={styles.input}
                  value={form.product_code}
                  disabled={downloadCount > 0}
                  onChange={(e) => set("product_code", e.target.value)}
                  placeholder="Auto-generated from the name if left blank"
                />
                <span className={downloadCount > 0 ? styles.warnHint : styles.hint}>
                  {downloadCount > 0
                    ? "Immutable — this product has real downloads. Changing it would break activation for every installed copy in the field."
                    : "The code the desktop plugin sends to activate. Leave blank to auto-generate from the name."}
                </span>
              </label>
              <div className={styles.row}>
                <label className={styles.label}>
                  Price (USD)
                  <input className={styles.input} type="number" min="0" step="0.01" value={form.price} onChange={(e) => set("price", e.target.value)} />
                </label>
                <label className={styles.label}>
                  Product Type
                  <select className={styles.input} value={form.type} onChange={(e) => set("type", e.target.value)}>
                    {options?.types.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </label>
              </div>
              <label className={styles.label}>
                Default Trial Days
                <input className={styles.input} type="number" min="0" value={form.default_trial_days} onChange={(e) => set("default_trial_days", e.target.value)} />
                <span className={styles.hint}>The server caps activation trials at this length.</span>
              </label>
            </div>
          )}

          {tab === "files" && (
            <FilesTab
              productId={savedId}
              files={files}
              setFiles={setFiles}
              ensureSaved={ensureSaved}
              asPartner={asPartner}
            />
          )}

          {tab === "installer" && (
            <InstallerBuildTab productId={savedId} ensureSaved={ensureSaved} asPartner={asPartner} />
          )}

          {tab === "compatibility" && (
            <CompatibilityTab compatibility={compatibility} setCompatibility={setCompatibility} />
          )}

          {tab === "documentation" && (
            <DocumentationTab documentation={documentation} setDocumentation={setDocumentation} />
          )}

          {tab === "seo" && (
            <div className={styles.panel}>
              <label className={styles.label}>
                SEO Title
                <input className={styles.input} value={form.seo_title} maxLength={180} onChange={(e) => set("seo_title", e.target.value)} placeholder="Defaults to the product name" />
              </label>
              <label className={styles.label}>
                SEO Description
                <textarea className={styles.textarea} rows={3} maxLength={300} value={form.seo_description} onChange={(e) => set("seo_description", e.target.value)} placeholder="Defaults to the short description" />
              </label>
            </div>
          )}
        </div>

        <aside className={styles.rail}>
          <div className={styles.railCard}>
            <h2 className={styles.railTitle}>Publishing</h2>
            <label className={styles.label}>
              Status
              <select className={styles.input} value={form.status} onChange={(e) => set("status", e.target.value)}>
                {/* Not manually selectable — only rendered so the product's real
                    current status shows accurately instead of the browser
                    silently falling back to the first option. */}
                {form.status === "draft" && <option value="draft">Draft</option>}
                <option value="pending">Pending Review</option>
                {mode === "admin" ? (
                  <>
                    <option value="published">Published</option>
                    <option value="rejected">Rejected</option>
                  </>
                ) : (
                  <>
                    {form.status === "published" && <option value="published">Published</option>}
                    {form.status === "rejected" && <option value="rejected">Rejected</option>}
                  </>
                )}
              </select>
              <span className={styles.hint}>
                {mode === "partner"
                  ? "Only BIMHive staff can publish or reject — choose Pending Review to submit for approval."
                  : 'Use "Save as Draft" below to keep this private while you work.'}
              </span>
            </label>

            {form.status === "rejected" && (
              <label className={styles.label}>
                Rejection Note
                {mode === "admin" ? (
                  <textarea
                    className={styles.textarea}
                    rows={3}
                    value={form.rejection_note}
                    onChange={(e) => set("rejection_note", e.target.value)}
                    placeholder="Let the partner know what to fix before resubmitting."
                  />
                ) : (
                  <p className={styles.warnHint}>{form.rejection_note || "No note was left."}</p>
                )}
              </label>
            )}
            <p className={styles.label}>Visibility</p>
            <label className={`${styles.optionRow} ${form.visibility === "public" ? styles.optionActive : ""}`}>
              <input type="radio" name="visibility" checked={form.visibility === "public"} onChange={() => set("visibility", "public")} />
              <span><strong>Public</strong><br /><span className={styles.hint}>Visible to all marketplace users</span></span>
            </label>
            <label className={`${styles.optionRow} ${form.visibility === "hidden" ? styles.optionActive : ""}`}>
              <input type="radio" name="visibility" checked={form.visibility === "hidden"} onChange={() => set("visibility", "hidden")} />
              <span><strong>Hidden</strong><br /><span className={styles.hint}>Only accessible via direct link</span></span>
            </label>
            <label className={styles.checkboxRow}>
              <input type="checkbox" checked={form.is_featured} onChange={(e) => set("is_featured", e.target.checked)} />
              Featured product
            </label>
          </div>
          <div className={styles.notice}>
            <Icon name="shield" size={18} />
            Products require admin approval before going live on the marketplace.
          </div>
        </aside>
      </div>
    </div>
  );
}
