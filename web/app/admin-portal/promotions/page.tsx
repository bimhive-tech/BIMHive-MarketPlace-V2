"use client";

import { useEffect, useState } from "react";

import { useConfirm } from "@/components/ConfirmDialog/useConfirm";
import { Icon } from "@/components/Icon/Icon";
import { Modal } from "@/components/Modal/Modal";
import { Pill } from "@/components/Pill/Pill";
import {
  AdminCheckbox,
  AdminCheckGroup,
  AdminField,
  AdminFormGrid,
  AdminInput,
  AdminSelect,
} from "@/features/admin/AdminForm/AdminForm";
import {
  getAdminOptions,
  getAdminProducts,
  promotionsApi,
  type AdminOptions,
  type AdminProductRow,
  type AdminPromotion,
} from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";
import promo from "./promotions.module.css";

const SCOPES: { value: AdminPromotion["scope"]; label: string }[] = [
  { value: "plan", label: "One All-Access plan (shows in the countdown bar)" },
  { value: "all", label: "Every product" },
  { value: "category", label: "One category (and its subcategories)" },
  { value: "products", label: "Selected products only" },
];

/** `datetime-local` inputs want "YYYY-MM-DDTHH:mm" in local time, not an ISO
 * string with a zone — this is the round-trip both ways. */
function toLocalInput(iso: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function fromLocalInput(value: string): string {
  return value ? new Date(value).toISOString() : "";
}

/** The concrete "applies to" cell — the plan/category name when there is one,
 * rather than just the generic scope label. */
function scopeSummary(row: AdminPromotion): string {
  if (row.scope === "plan") return row.plan_name ? `${row.plan_name} plan` : "A plan";
  if (row.scope === "category") return row.category_name || "A category";
  if (row.scope === "products") return `${row.products.length} product${row.products.length === 1 ? "" : "s"}`;
  return "Every product";
}

function defaultForm() {
  const now = new Date();
  const inAWeek = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  return {
    name: "",
    badge_label: "SPECIAL OFFER",
    headline: "",
    cta_label: "",
    cta_url: "",
    discount_percent: 20,
    scope: "plan" as AdminPromotion["scope"],
    category: "",
    products: [] as number[],
    plan: "",
    starts_at: toLocalInput(now.toISOString()),
    ends_at: toLocalInput(inAWeek.toISOString()),
    is_active: true,
    show_countdown: true,
    priority: 0,
  };
}

type PromotionForm = ReturnType<typeof defaultForm>;

export default function AdminPromotionsPage() {
  const [rows, setRows] = useState<AdminPromotion[] | null>(null);
  const [options, setOptions] = useState<AdminOptions | null>(null);
  const [products, setProducts] = useState<AdminProductRow[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<PromotionForm>(defaultForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { confirm, dialog } = useConfirm();

  function load() {
    promotionsApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(() => {
    load();
    getAdminOptions().then(setOptions).catch(() => setOptions(null));
    getAdminProducts().then(setProducts).catch(() => setProducts([]));
  }, []);

  function set<K extends keyof PromotionForm>(key: K, value: PromotionForm[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function startNew() {
    setEditingId(null);
    setForm(defaultForm());
    setError("");
    setShowForm(true);
  }

  function startEdit(row: AdminPromotion) {
    setEditingId(row.id);
    setForm({
      name: row.name,
      badge_label: row.badge_label,
      headline: row.headline,
      cta_label: row.cta_label,
      cta_url: row.cta_url,
      discount_percent: row.discount_percent,
      scope: row.scope,
      category: row.category ? String(row.category) : "",
      products: row.products,
      plan: row.plan ? String(row.plan) : "",
      starts_at: toLocalInput(row.starts_at),
      ends_at: toLocalInput(row.ends_at),
      is_active: row.is_active,
      show_countdown: row.show_countdown,
      priority: row.priority,
    });
    setError("");
    setShowForm(true);
  }

  async function onSave() {
    if (!form.name.trim() || !form.headline.trim()) {
      setError("A promotion needs a name and a headline.");
      return;
    }
    setSaving(true);
    setError("");
    const payload = {
      ...form,
      category: form.scope === "category" && form.category ? Number(form.category) : null,
      products: form.scope === "products" ? form.products : [],
      plan: form.scope === "plan" && form.plan ? Number(form.plan) : null,
      // Only a plan-scoped promotion can drive the countdown bar — the
      // server rejects the flag otherwise (see catalog.admin_api
      // .PromotionSerializer.validate), so keep the two in sync here too.
      show_countdown: form.scope === "plan" && form.show_countdown,
      starts_at: fromLocalInput(form.starts_at),
      ends_at: fromLocalInput(form.ends_at),
    };
    try {
      if (editingId) await promotionsApi.update(editingId, payload);
      else await promotionsApi.create(payload);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save this promotion.");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(row: AdminPromotion) {
    const confirmed = await confirm({
      title: `Delete ${row.name}?`,
      message: "Prices it discounts go back to normal immediately.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    try {
      await promotionsApi.remove(row.id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this promotion.");
    }
  }

  function toggleProduct(id: number) {
    setForm((f) => ({
      ...f,
      products: f.products.includes(id) ? f.products.filter((p) => p !== id) : [...f.products, id],
    }));
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Promotions</h1>
          <p className={styles.sub}>
            Time-boxed discounts. Prices drop while a promotion runs and go back to normal on their
            own when it ends — no follow-up needed. Only a plan-scoped promotion can show in the
            countdown bar above the nav; product/category/all-product discounts still apply on the
            storefront, just not up there.
          </p>
        </div>
        <button className={styles.primaryBtn} onClick={startNew}>
          <Icon name="plus" size={16} />
          New Promotion
        </button>
      </header>

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        size="lg"
        title={editingId ? `Edit ${form.name || "promotion"}` : "New promotion"}
        description="Prices drop while it runs and return to normal on their own when it ends."
        footer={
          <>
            <button className={styles.actionBtn} onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button className={styles.primaryBtn} disabled={saving} onClick={onSave}>
              {saving ? "Saving…" : editingId ? "Save" : "Create"}
            </button>
          </>
        }
      >
        <AdminFormGrid>
          {error && <p className={`${styles.error} ${promo.fullRow}`}>{error}</p>}
          <AdminField label="Internal name" hint="Only staff see this.">
            <AdminInput placeholder="e.g. Launch week" value={form.name} onChange={(e) => set("name", e.target.value)} />
          </AdminField>
          <AdminField label="Badge label" hint="The small tag on discounted prices.">
            <AdminInput
              placeholder="e.g. SPECIAL OFFER"
              value={form.badge_label}
              onChange={(e) => set("badge_label", e.target.value)}
            />
          </AdminField>
          <AdminField label="Headline" hint="What customers read beside the discount." wide>
            <AdminInput
              placeholder="e.g. This price won't last long..."
              value={form.headline}
              onChange={(e) => set("headline", e.target.value)}
            />
          </AdminField>

          <AdminField label="Discount %" hint="1 to 100. 100 makes what it covers free.">
            <AdminInput
              type="number"
              min={1}
              max={100}
              value={form.discount_percent}
              onChange={(e) => set("discount_percent", Number(e.target.value))}
            />
          </AdminField>
          <AdminField label="Applies to">
            <AdminSelect value={form.scope} onChange={(e) => set("scope", e.target.value as AdminPromotion["scope"])}>
              {SCOPES.map((scope) => (
                <option key={scope.value} value={scope.value}>
                  {scope.label}
                </option>
              ))}
            </AdminSelect>
          </AdminField>

          {form.scope === "plan" && (
            <AdminField label="Plan" wide>
              <AdminSelect value={form.plan} onChange={(e) => set("plan", e.target.value)}>
                <option value="">Pick a plan</option>
                {options?.membership_plans.map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name}
                  </option>
                ))}
              </AdminSelect>
            </AdminField>
          )}

          {form.scope === "category" && (
            <AdminField label="Category" hint="Its subcategories are included." wide>
              <AdminSelect value={form.category} onChange={(e) => set("category", e.target.value)}>
                <option value="">Pick a category</option>
                {options?.categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.parent_name ? `— ${c.name}` : c.name}
                  </option>
                ))}
              </AdminSelect>
            </AdminField>
          )}

          {form.scope === "products" && (
            <AdminCheckGroup title="Products in this promotion">
              {products.map((product) => (
                <AdminCheckbox
                  key={product.id}
                  label={product.name}
                  checked={form.products.includes(product.id)}
                  onChange={() => toggleProduct(product.id)}
                />
              ))}
            </AdminCheckGroup>
          )}

          <AdminField label="Starts">
            <AdminInput type="datetime-local" value={form.starts_at} onChange={(e) => set("starts_at", e.target.value)} />
          </AdminField>
          <AdminField label="Ends">
            <AdminInput type="datetime-local" value={form.ends_at} onChange={(e) => set("ends_at", e.target.value)} />
          </AdminField>

          <AdminField label="Banner button label" hint="Optional.">
            <AdminInput value={form.cta_label} onChange={(e) => set("cta_label", e.target.value)} />
          </AdminField>
          <AdminField label="Banner button link" hint="e.g. /catalog. Optional.">
            <AdminInput value={form.cta_url} onChange={(e) => set("cta_url", e.target.value)} />
          </AdminField>

          <AdminCheckbox
            label="Active"
            hint="Switch it off without changing its dates."
            checked={form.is_active}
            onChange={(v) => set("is_active", v)}
          />
          {form.scope === "plan" && (
            <AdminCheckbox
              label="Show in the countdown bar"
              hint="The strip above the nav. Plan promotions only."
              checked={form.show_countdown}
              onChange={(v) => set("show_countdown", v)}
            />
          )}
        </AdminFormGrid>
      </Modal>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Promotion</th>
              <th>Off</th>
              <th>Applies to</th>
              <th>Window</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.name}</strong>
                  <div className={styles.muted}>{row.headline}</div>
                </td>
                <td className={promo.discount}>−{row.discount_percent}%</td>
                <td className={styles.muted}>{scopeSummary(row)}</td>
                <td className={promo.window}>
                  {new Date(row.starts_at).toLocaleDateString()} →{" "}
                  {new Date(row.ends_at).toLocaleDateString()}
                </td>
                <td>
                  {row.is_live ? (
                    <Pill tone="success">Live</Pill>
                  ) : row.is_active ? (
                    <Pill tone="warning">Scheduled</Pill>
                  ) : (
                    <Pill>Off</Pill>
                  )}
                </td>
                <td>
                  <div className={styles.actionRow}>
                    <button className={styles.iconBtn} aria-label="Edit" onClick={() => startEdit(row)}>
                      <Icon name="edit" size={16} />
                    </button>
                    <button
                      className={`${styles.iconBtn} ${styles.iconBtnDanger}`}
                      aria-label="Delete"
                      onClick={() => onDelete(row)}
                    >
                      <Icon name="trash" size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows === null && <p className={styles.state}>Loading promotions…</p>}
        {rows?.length === 0 && <p className={styles.state}>No promotions yet.</p>}
      </div>

      {dialog}
    </div>
  );
}
