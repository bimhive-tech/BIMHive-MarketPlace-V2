"use client";

import { useEffect, useState } from "react";

import { useConfirm } from "@/components/ConfirmDialog/useConfirm";
import { Icon } from "@/components/Icon/Icon";
import { Modal } from "@/components/Modal/Modal";
import { Pill } from "@/components/Pill/Pill";
import {
  AdminCheckbox,
  AdminField,
  AdminFormGrid,
  AdminInput,
  AdminSelect,
} from "@/features/admin/AdminForm/AdminForm";
import {
  createAdminLicenseCode,
  getAdminLicenseCodes,
  getAdminLicenseOptions,
  revokeAdminLicenseCode,
  type AdminLicenseCode,
  type AdminLicenseProductOption,
} from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  unredeemed: "warning",
  redeemed: "success",
  revoked: "error",
};

const EMPTY_FORM = { product: "", seats: "1", duration_days: "365", lifetime: false, note: "" };

type CodeForm = typeof EMPTY_FORM;

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function LicenseCodesPanel() {
  const [codes, setCodes] = useState<AdminLicenseCode[] | null>(null);
  const [products, setProducts] = useState<AdminLicenseProductOption[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CodeForm>(EMPTY_FORM);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const { confirm, dialog } = useConfirm();

  function load() {
    setCodes(null);
    getAdminLicenseCodes().then(setCodes).catch(() => setCodes([]));
  }

  useEffect(() => {
    load();
    getAdminLicenseOptions().then((o) => setProducts(o.products)).catch(() => setProducts([]));
  }, []);

  function set<K extends keyof CodeForm>(key: K, value: CodeForm[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function openForm() {
    setForm(EMPTY_FORM);
    setError("");
    setShowForm(true);
  }

  async function onGenerate() {
    setError("");
    if (!form.product) {
      setError("Choose which product this code is for.");
      return;
    }
    setSaving(true);
    try {
      await createAdminLicenseCode({
        product: form.product,
        seats: Number(form.seats) || 1,
        duration_days: form.lifetime ? null : Number(form.duration_days) || null,
        note: form.note.trim(),
      });
      setShowForm(false);
      load();
    } catch {
      setError("Could not generate a code — please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function onRevoke(item: AdminLicenseCode) {
    const confirmed = await confirm({
      title: `Revoke ${item.code}?`,
      message: "Nobody will be able to redeem it. This can't be undone.",
      confirmLabel: "Revoke",
      danger: true,
    });
    if (!confirmed) return;
    setBusyId(item.id);
    try {
      const updated = await revokeAdminLicenseCode(item.id);
      setCodes((list) => list?.map((c) => (c.id === item.id ? updated : c)) ?? null);
    } finally {
      setBusyId(null);
    }
  }

  async function onCopy(code: string, id: string) {
    await navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId((current) => (current === id ? null : current)), 1500);
  }

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <p className={styles.sub}>
          Generate a single-use code for one product with its own seat count and duration — hand it to
          anyone, and whoever redeems it on their account gets a real license for exactly that long.
        </p>
        <button className={styles.primaryBtn} onClick={openForm}>
          <Icon name="plus" size={16} />
          Generate Code
        </button>
      </div>

      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title="Generate a license code"
        description="Single use. Whoever redeems it gets a real license on their own account."
        footer={
          <>
            <button className={styles.actionBtn} onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button className={styles.primaryBtn} disabled={saving} onClick={onGenerate}>
              {saving ? "Generating…" : "Generate"}
            </button>
          </>
        }
      >
        <AdminFormGrid>
          <AdminField label="Product" wide>
            <AdminSelect value={form.product} onChange={(e) => set("product", e.target.value)}>
              <option value="">Select a product</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </AdminSelect>
          </AdminField>
          <AdminField label="Seats" hint="Machines it can activate at once.">
            <AdminInput type="number" min={1} value={form.seats} onChange={(e) => set("seats", e.target.value)} />
          </AdminField>
          <AdminField label="Duration (days)" hint={form.lifetime ? "Lifetime is on." : "From the day it's redeemed."}>
            <AdminInput
              type="number"
              min={1}
              disabled={form.lifetime}
              value={form.duration_days}
              onChange={(e) => set("duration_days", e.target.value)}
            />
          </AdminField>
          <AdminCheckbox
            wide
            label="Lifetime"
            hint="Never expires."
            checked={form.lifetime}
            onChange={(v) => set("lifetime", v)}
          />
          <AdminField label="Note" hint="Who it's for. Only staff see this." wide>
            <AdminInput value={form.note} onChange={(e) => set("note", e.target.value)} />
          </AdminField>
          {error && <p className={styles.error}>{error}</p>}
        </AdminFormGrid>
      </Modal>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Code</th>
              <th>Product</th>
              <th>Seats</th>
              <th>Duration</th>
              <th>Status</th>
              <th>Redeemed by</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {codes?.map((c) => (
              <tr key={c.id}>
                <td>
                  <span className={styles.mono}>{c.code}</span>
                  {c.note && <div className={styles.muted}>{c.note}</div>}
                </td>
                <td>
                  <strong>{c.product_name}</strong>
                  <div className={`${styles.muted} ${styles.mono}`}>{c.product_code}</div>
                </td>
                <td className={styles.muted}>{c.seats}</td>
                <td className={styles.muted}>{c.duration_days ? `${c.duration_days} days` : "Lifetime"}</td>
                <td>
                  <Pill tone={STATUS_TONE[c.status] ?? "neutral"}>{c.status}</Pill>
                </td>
                <td className={styles.muted}>{c.redeemed_by_email || "—"}</td>
                <td className={styles.muted}>{formatDate(c.created_at)}</td>
                <td>
                  <div className={styles.actionRow}>
                    <button className={styles.iconBtn} aria-label="Copy code" onClick={() => onCopy(c.code, c.id)}>
                      <Icon name={copiedId === c.id ? "check" : "copy"} size={16} />
                    </button>
                    {c.status === "unredeemed" && (
                      <button className={styles.actionBtn} disabled={busyId === c.id} onClick={() => onRevoke(c)}>
                        Revoke
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {codes === null && <p className={styles.state}>Loading license codes…</p>}
        {codes?.length === 0 && <p className={styles.state}>No license codes generated yet.</p>}
      </div>

      {codes && codes.length > 0 && (
        <p className={styles.count}>
          Showing {codes.length} {codes.length === 1 ? "code" : "codes"}
        </p>
      )}

      {dialog}
    </div>
  );
}
