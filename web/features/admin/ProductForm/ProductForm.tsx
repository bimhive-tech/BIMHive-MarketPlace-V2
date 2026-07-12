"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { createProduct, getAdminOptions, type AdminOptions } from "@/lib/adminApi";

import styles from "./ProductForm.module.css";

type TabId = "info" | "pricing" | "seo";
const TABS: { id: TabId; label: string }[] = [
  { id: "info", label: "Product Information" },
  { id: "pricing", label: "Pricing & License" },
  { id: "seo", label: "SEO & Settings" },
];

interface Feature {
  title: string;
  description: string;
}

const MAX_SHORT = 150;
const MAX_DESC = 5000;

export function ProductForm() {
  const router = useRouter();
  const [options, setOptions] = useState<AdminOptions | null>(null);
  const [tab, setTab] = useState<TabId>("info");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    name: "",
    short_description: "",
    description: "",
    type: "plugin",
    category: "",
    partner: "",
    price: "0",
    team_price: "",
    team_seats: "5",
    default_trial_days: "30",
    status: "draft",
    visibility: "public",
    seo_title: "",
    seo_description: "",
  });
  const [features, setFeatures] = useState<Feature[]>([{ title: "", description: "" }]);

  useEffect(() => {
    getAdminOptions().then(setOptions).catch(() => setError("Could not load form options."));
  }, []);

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function setFeature(i: number, key: keyof Feature, value: string) {
    setFeatures((list) => list.map((f, idx) => (idx === i ? { ...f, [key]: value } : f)));
  }

  async function submit(status: "draft" | "pending") {
    setError("");
    if (!form.name.trim() || !form.short_description.trim() || !form.description.trim()) {
      setError("Name, short description, and full description are required.");
      setTab("info");
      return;
    }
    if (!form.category || !form.partner) {
      setError("Please choose a category and a partner.");
      setTab("info");
      return;
    }
    setSaving(true);
    try {
      await createProduct({
        name: form.name.trim(),
        short_description: form.short_description.trim(),
        description: form.description.trim(),
        type: form.type,
        category: Number(form.category),
        partner: Number(form.partner),
        price: form.price || "0",
        team_price: form.team_price ? form.team_price : null,
        team_seats: Number(form.team_seats) || 5,
        default_trial_days: Number(form.default_trial_days) || 30,
        status,
        visibility: form.visibility,
        seo_title: form.seo_title.trim(),
        seo_description: form.seo_description.trim(),
        features: features.filter((f) => f.title.trim()),
      });
      router.push("/admin-portal/products");
      router.refresh();
    } catch {
      setError("Could not save the product. Please review the fields and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Add New Product</h1>
          <p className={styles.sub}>Create a new product to sell on the BIMHIVE marketplace.</p>
        </div>
        <div className={styles.headActions}>
          <button className={styles.secondaryBtn} disabled={saving} onClick={() => submit("draft")}>
            Save as Draft
          </button>
          <button className={styles.primaryBtn} disabled={saving} onClick={() => submit("pending")}>
            {saving ? "Submitting…" : "Submit for Review"}
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
                <label className={styles.label}>
                  Partner <span className={styles.req}>*</span>
                  <select className={styles.input} value={form.partner} onChange={(e) => set("partner", e.target.value)}>
                    <option value="">Select a partner</option>
                    {options?.partners.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </label>
              </div>

              <div className={styles.features}>
                <p className={styles.label}>Key Features</p>
                {features.map((f, i) => (
                  <div key={i} className={styles.featureRow}>
                    <input className={styles.input} value={f.title} onChange={(e) => setFeature(i, "title", e.target.value)} placeholder="e.g. Automate sheet creation" />
                    <input className={styles.input} value={f.description} onChange={(e) => setFeature(i, "description", e.target.value)} placeholder="Save time by automating repetitive tasks." />
                    <button className={styles.iconBtn} aria-label="Remove feature" onClick={() => setFeatures((l) => l.filter((_, idx) => idx !== i))}>
                      <Icon name="wrench" size={16} />
                    </button>
                  </div>
                ))}
                <button className={styles.addBtn} onClick={() => setFeatures((l) => [...l, { title: "", description: "" }])}>
                  <Icon name="check" size={14} /> Add Feature
                </button>
              </div>
            </div>
          )}

          {tab === "pricing" && (
            <div className={styles.panel}>
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
              <div className={styles.row}>
                <label className={styles.label}>
                  Team Price (optional)
                  <input className={styles.input} type="number" min="0" step="0.01" value={form.team_price} onChange={(e) => set("team_price", e.target.value)} placeholder="e.g. 199.00" />
                </label>
                <label className={styles.label}>
                  Team Seats
                  <input className={styles.input} type="number" min="1" value={form.team_seats} onChange={(e) => set("team_seats", e.target.value)} />
                </label>
              </div>
              <label className={styles.label}>
                Default Trial Days
                <input className={styles.input} type="number" min="0" value={form.default_trial_days} onChange={(e) => set("default_trial_days", e.target.value)} />
                <span className={styles.hint}>The server caps activation trials at this length.</span>
              </label>
            </div>
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
                <option value="draft">Draft</option>
                <option value="pending">Pending Review</option>
                <option value="published">Published</option>
              </select>
              <span className={styles.hint}>Drafts are only visible to you and your team.</span>
            </label>
            <p className={styles.label}>Visibility</p>
            <label className={`${styles.optionRow} ${form.visibility === "public" ? styles.optionActive : ""}`}>
              <input type="radio" name="visibility" checked={form.visibility === "public"} onChange={() => set("visibility", "public")} />
              <span><strong>Public</strong><br /><span className={styles.hint}>Visible to all marketplace users</span></span>
            </label>
            <label className={`${styles.optionRow} ${form.visibility === "hidden" ? styles.optionActive : ""}`}>
              <input type="radio" name="visibility" checked={form.visibility === "hidden"} onChange={() => set("visibility", "hidden")} />
              <span><strong>Hidden</strong><br /><span className={styles.hint}>Only accessible via direct link</span></span>
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
