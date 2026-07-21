"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import { StarRating } from "@/components/StarRating/StarRating";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";
import { ProductRowActions } from "@/features/admin/ProductRowActions/ProductRowActions";
import { getAdminProducts, type AdminProductRow } from "@/lib/adminApi";

import styles from "./products.module.css";

const TABS = [
  { key: "all", label: "All Products" },
  { key: "published", label: "Published" },
  { key: "draft", label: "Draft" },
  { key: "pending", label: "Pending Review" },
  { key: "rejected", label: "Rejected" },
];

const STATUS_TONE: Record<string, "success" | "warning" | "error" | "neutral"> = {
  published: "success",
  pending: "warning",
  rejected: "error",
  draft: "neutral",
};

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function AdminProductsPage() {
  const [tab, setTab] = useState("all");
  const [rows, setRows] = useState<AdminProductRow[] | null>(null);

  useEffect(() => {
    setRows(null);
    getAdminProducts(tab).then(setRows).catch(() => setRows([]));
  }, [tab]);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Products</h1>
          <p className={styles.sub}>Manage all plugins, tools, and digital products on BIMHIVE.</p>
        </div>
        <Link href="/admin-portal/products/new" className={styles.primaryBtn}>
          <Icon name="arrow-right" size={16} />
          Add New Product
        </Link>
      </header>

      <div className={styles.tabs} role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            className={`${styles.tab} ${tab === t.key ? styles.tabActive : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Product</th>
              <th>Partner</th>
              <th>Category</th>
              <th>Price</th>
              <th>Status</th>
              <th>Downloads</th>
              <th>Rating</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <div className={styles.product}>
                    <span className={styles.thumb}>
                      {row.cover_image_url ? (
                        <Image src={row.cover_image_url} alt="" fill sizes="48px" className={styles.thumbImg} />
                      ) : (
                        <WireframeThumb seed={row.slug} />
                      )}
                    </span>
                    <span className={styles.productText}>
                      <Link href={`/admin-portal/products/${row.id}/edit`} className={styles.productName}>
                        {row.name}
                      </Link>
                      <span className={styles.productDesc}>{row.short_description}</span>
                    </span>
                  </div>
                </td>
                <td>
                  <span className={styles.partner}>
                    {row.partner || "—"}
                    {row.partner_verified && <Icon name="check-circle" size={14} className={styles.verified} />}
                  </span>
                </td>
                <td className={styles.muted}>{row.category}</td>
                <td className={styles.price}>{row.price_label}</td>
                <td>
                  <Pill tone={STATUS_TONE[row.status] ?? "neutral"}>{row.status}</Pill>
                </td>
                <td className={styles.muted}>
                  {row.download_count ? `${row.download_count.toLocaleString()}+` : "—"}
                </td>
                <td>
                  {row.rating_count ? (
                    <StarRating value={Number(row.rating_average)} size={14} showValue />
                  ) : (
                    <span className={styles.muted}>—</span>
                  )}
                </td>
                <td className={styles.muted}>{formatDate(row.updated_at)}</td>
                <td>
                  <ProductRowActions
                    productId={row.id}
                    editHref={`/admin-portal/products/${row.id}/edit`}
                    isPlugin={row.type === "plugin"}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {rows === null && <p className={styles.state}>Loading products…</p>}
        {rows?.length === 0 && <p className={styles.state}>No products in this view.</p>}
      </div>

      {rows && rows.length > 0 && (
        <p className={styles.count}>
          Showing {rows.length} {rows.length === 1 ? "product" : "products"}
        </p>
      )}
    </div>
  );
}
