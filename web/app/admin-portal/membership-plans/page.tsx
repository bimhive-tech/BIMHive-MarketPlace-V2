"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { membershipPlansApi, type AdminMembershipPlan } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

function defaultForm() {
  return {
    name: "",
    rank: 1,
    tagline: "",
    description: "",
    monthly_price: "",
    yearly_price: "",
    seats_per_product: 2,
    is_active: true,
    is_featured: false,
    sort_order: 0,
  };
}

type PlanForm = ReturnType<typeof defaultForm>;

export default function AdminMembershipPlansPage() {
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
      monthly_price: row.monthly_price ?? "",
      yearly_price: row.yearly_price ?? "",
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

  async function onDelete(id: number) {
    if (!window.confirm("Delete this plan? Its members lose access immediately.")) return;
    await membershipPlansApi.remove(id);
    load();
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

      {showForm && (
        <div className={styles.formPanel}>
          <div className={styles.formGrid}>
            <input
              className={styles.searchInput}
              placeholder="Name, e.g. Standard"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
            />
            <label className={styles.checkboxRow}>
              Rank (higher = includes lower)
              <input
                className={styles.searchInput}
                type="number"
                min={1}
                value={form.rank}
                onChange={(e) => set("rank", Number(e.target.value))}
              />
            </label>
            <input
              className={styles.searchInput}
              placeholder="Tagline (optional)"
              value={form.tagline}
              onChange={(e) => set("tagline", e.target.value)}
            />
            <label className={styles.checkboxRow}>
              Monthly price
              <input
                className={styles.searchInput}
                type="number"
                step="0.01"
                min={0}
                value={form.monthly_price}
                onChange={(e) => set("monthly_price", e.target.value)}
              />
            </label>
            <label className={styles.checkboxRow}>
              Yearly price
              <input
                className={styles.searchInput}
                type="number"
                step="0.01"
                min={0}
                value={form.yearly_price}
                onChange={(e) => set("yearly_price", e.target.value)}
              />
            </label>
            <label className={styles.checkboxRow}>
              Machines per product
              <input
                className={styles.searchInput}
                type="number"
                min={1}
                value={form.seats_per_product}
                onChange={(e) => set("seats_per_product", Number(e.target.value))}
              />
            </label>
            <textarea
              className={styles.textarea}
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
            />

            <label className={styles.checkboxRow}>
              <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} />
              Active
            </label>
            <label className={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={form.is_featured}
                onChange={(e) => set("is_featured", e.target.checked)}
              />
              Featured on the pricing page
            </label>
          </div>

          <div className={styles.formActions}>
            <button className={styles.primaryBtn} disabled={saving} onClick={onSave}>
              {editingId ? "Save" : "Create"}
            </button>
            <button className={styles.actionBtn} onClick={() => setShowForm(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

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
                <td className={styles.muted}>{row.monthly_price ? `$${row.monthly_price}` : "—"}</td>
                <td className={styles.muted}>{row.yearly_price ? `$${row.yearly_price}` : "—"}</td>
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
                      onClick={() => onDelete(row.id)}
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
    </div>
  );
}
