"use client";

import { useEffect, useState } from "react";

import { useConfirm } from "@/components/ConfirmDialog/useConfirm";
import { Icon } from "@/components/Icon/Icon";
import { Modal } from "@/components/Modal/Modal";
import { formatPrice } from "@/config/site";
import {
  AdminCheckbox,
  AdminField,
  AdminFormGrid,
  AdminInput,
  AdminSelect,
  AdminTextarea,
} from "@/features/admin/AdminForm/AdminForm";
import { membershipPlansApi, type AdminMembershipPlan } from "@/lib/adminApi";
import type { PlanEnrollment } from "@/lib/types";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

/** Mirrors membership.MembershipPlan.Enrollment. */
const ENROLLMENT_OPTIONS: { value: PlanEnrollment; label: string }[] = [
  { value: "self_serve", label: "Join online" },
  { value: "request", label: "By request (Contact us)" },
  { value: "included", label: "Included for everyone (no sign-up)" },
];

function defaultForm() {
  return {
    name: "",
    rank: 1,
    tagline: "",
    description: "",
    features: "",
    enrollment: "self_serve" as PlanEnrollment,
    monthly_price: "",
    yearly_price: "",
    original_monthly_price: "",
    original_yearly_price: "",
    currency: "USD",
    seats_per_product: 2,
    is_active: true,
    is_featured: false,
    sort_order: 0,
  };
}

type PlanForm = ReturnType<typeof defaultForm>;

export default function AdminMembershipPlansPage() {
  const { confirm, dialog } = useConfirm();
  const [rows, setRows] = useState<AdminMembershipPlan[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<PlanForm>(defaultForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function load() {
    membershipPlansApi.list().then(setRows).catch(() => setRows([]));
  }

  useEffect(load, []);

  function set<K extends keyof PlanForm>(key: K, value: PlanForm[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function startNew() {
    setEditingId(null);
    // Ranks after the highest existing plan by default — a new tier is
    // usually being added above the others, and rank is what decides
    // cumulative coverage (see MembershipPlan.covers_plan).
    const nextRank = (rows ?? []).reduce((max, p) => Math.max(max, p.rank), 0) + 1;
    setForm({ ...defaultForm(), rank: nextRank });
    setError("");
    setShowForm(true);
  }

  function startEdit(row: AdminMembershipPlan) {
    setEditingId(row.id);
    setForm({
      name: row.name,
      rank: row.rank,
      tagline: row.tagline,
      description: row.description,
      features: row.features,
      enrollment: row.enrollment,
      monthly_price: row.monthly_price ?? "",
      yearly_price: row.yearly_price ?? "",
      original_monthly_price: row.original_monthly_price ?? "",
      original_yearly_price: row.original_yearly_price ?? "",
      currency: row.currency,
      seats_per_product: row.seats_per_product,
      is_active: row.is_active,
      is_featured: row.is_featured,
      sort_order: row.sort_order,
    });
    setError("");
    setShowForm(true);
  }

  async function onSave() {
    if (!form.name.trim()) return;
    setSaving(true);
    setError("");
    const payload = {
      ...form,
      monthly_price: form.monthly_price || null,
      yearly_price: form.yearly_price || null,
      original_monthly_price: form.original_monthly_price || null,
      original_yearly_price: form.original_yearly_price || null,
    };
    try {
      if (editingId) await membershipPlansApi.update(editingId, payload);
      else await membershipPlansApi.create(payload);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save this plan.");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(row: AdminMembershipPlan) {
    // Deliberately doesn't promise members lose access: the plan FK is
    // PROTECT, so a tier anyone has ever been on can't be deleted at all —
    // the API says so in a real message, surfaced below.
    const confirmed = await confirm({
      title: `Delete ${row.name}?`,
      message: "Only possible if nobody has ever been on it. Otherwise, uncheck Active to retire it.",
      confirmLabel: "Delete",
      danger: true,
    });
    if (!confirmed) return;
    setError("");
    try {
      await membershipPlansApi.remove(row.id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete this plan.");
    }
  }

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Membership Plans</h1>
          <p className={styles.sub}>
            Tiers for All-Access. A higher rank includes everything the lower ranks do — assign each
            product its lowest qualifying tier on the product form.
          </p>
        </div>
        <button className={styles.primaryBtn} onClick={startNew}>
          <Icon name="plus" size={16} />
          New Plan
        </button>
      </header>

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title={editingId ? `Edit ${form.name || "plan"}` : "New membership plan"}
        description="A higher rank includes everything the lower ranks do."
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
          <AdminField label="Plan name" hint="Shown on the pricing page.">
            <AdminInput
              placeholder="e.g. Pro"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
            />
          </AdminField>
          <AdminField label="Rank" hint="0 = Free. Higher tiers include everything the lower ones do.">
            <AdminInput
              type="number"
              min={0}
              value={form.rank}
              onChange={(e) => set("rank", Number(e.target.value))}
            />
          </AdminField>

          <AdminField label="Tagline" hint="One line under the plan name. Optional.">
            <AdminInput
              placeholder="Everything a small team needs"
              value={form.tagline}
              onChange={(e) => set("tagline", e.target.value)}
            />
          </AdminField>
          <AdminField label="Currency" hint="Three-letter code, e.g. USD.">
            <AdminInput
              maxLength={8}
              value={form.currency}
              onChange={(e) => set("currency", e.target.value.toUpperCase())}
            />
          </AdminField>

          <AdminField label="How people join" hint="Decides the pricing card's button." wide>
            <AdminSelect
              value={form.enrollment}
              onChange={(e) => set("enrollment", e.target.value as PlanEnrollment)}
            >
              {ENROLLMENT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </AdminSelect>
          </AdminField>

          <AdminField label="Monthly price" hint="0 makes it free to join. Blank = not sold monthly.">
            <AdminInput
              type="number"
              step="0.01"
              min={0}
              placeholder="—"
              value={form.monthly_price}
              onChange={(e) => set("monthly_price", e.target.value)}
            />
          </AdminField>
          <AdminField label="Yearly price" hint="Below 12× the monthly price to earn a savings badge.">
            <AdminInput
              type="number"
              step="0.01"
              min={0}
              placeholder="—"
              value={form.yearly_price}
              onChange={(e) => set("yearly_price", e.target.value)}
            />
          </AdminField>

          <AdminField label="Original monthly price" hint="Shown crossed out beside the real price. Never charged.">
            <AdminInput
              type="number"
              step="0.01"
              min={0}
              placeholder="None"
              value={form.original_monthly_price}
              onChange={(e) => set("original_monthly_price", e.target.value)}
            />
          </AdminField>
          <AdminField label="Original yearly price" hint="Shown crossed out beside the real price. Never charged.">
            <AdminInput
              type="number"
              step="0.01"
              min={0}
              placeholder="None"
              value={form.original_yearly_price}
              onChange={(e) => set("original_yearly_price", e.target.value)}
            />
          </AdminField>

          <AdminField label="Machines per product" hint="Seats a member gets on each covered product.">
            <AdminInput
              type="number"
              min={1}
              value={form.seats_per_product}
              onChange={(e) => set("seats_per_product", Number(e.target.value))}
            />
          </AdminField>
          <AdminField label="Sort order" hint="Ties are broken by rank, then name.">
            <AdminInput
              type="number"
              min={0}
              value={form.sort_order}
              onChange={(e) => set("sort_order", Number(e.target.value))}
            />
          </AdminField>

          <AdminField label="What's included" hint="One item per line — shown as the card's checklist." wide>
            <AdminTextarea
              rows={4}
              placeholder={"Priority support\nRequest new tools"}
              value={form.features}
              onChange={(e) => set("features", e.target.value)}
            />
          </AdminField>

          <AdminField label="Description" hint="The longer pitch on the pricing page. Optional." wide>
            <AdminTextarea
              placeholder="What this tier includes and who it's for."
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </AdminField>

          <AdminCheckbox
            label="Active"
            hint="Inactive tiers stay valid for existing members but can't be bought."
            checked={form.is_active}
            onChange={(v) => set("is_active", v)}
          />
          <AdminCheckbox
            label="Featured"
            hint="Highlighted as the recommended plan."
            checked={form.is_featured}
            onChange={(v) => set("is_featured", v)}
          />
        </AdminFormGrid>
      </Modal>

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Plan</th>
              <th>Rank</th>
              <th>Monthly</th>
              <th>Yearly</th>
              <th>Products</th>
              <th>Members</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.name}</strong>
                  {row.is_featured && <span className={styles.count}> · Featured</span>}
                  {!row.is_active && <span className={styles.count}> · Inactive</span>}
                </td>
                <td className={styles.mono}>{row.rank}</td>
                <td className={styles.muted}>
                  {row.monthly_price ? formatPrice(row.monthly_price, row.currency) : "—"}
                </td>
                <td className={styles.muted}>
                  {row.yearly_price ? formatPrice(row.yearly_price, row.currency) : "—"}
                </td>
                <td className={styles.muted}>{row.product_count}</td>
                <td className={styles.muted}>{row.member_count}</td>
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
        {rows === null && <p className={styles.state}>Loading plans…</p>}
        {rows?.length === 0 && <p className={styles.state}>No membership plans yet.</p>}
      </div>

      {dialog}
    </div>
  );
}
