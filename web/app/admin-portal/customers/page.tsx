"use client";

import { useEffect, useState } from "react";

import { Pill } from "@/components/Pill/Pill";
import { getAdminCustomers, type AdminUser } from "@/lib/adminApi";

import styles from "@/features/admin/AdminTable/AdminTable.module.css";

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function AdminCustomersPage() {
  const [rows, setRows] = useState<AdminUser[] | null>(null);

  useEffect(() => {
    getAdminCustomers().then(setRows).catch(() => setRows([]));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Customers</h1>
          <p className={styles.sub}>Everyone with an account on the marketplace.</p>
        </div>
      </header>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Customer</th>
              <th>Email</th>
              <th>Orders</th>
              <th>Status</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((row) => (
              <tr key={row.id}>
                <td>
                  <strong>{row.full_name}</strong>
                </td>
                <td className={styles.muted}>{row.email}</td>
                <td className={styles.muted}>{row.order_count}</td>
                <td>
                  <Pill tone={row.is_active ? "success" : "neutral"}>
                    {row.is_active ? "Active" : "Inactive"}
                  </Pill>
                </td>
                <td className={styles.muted}>{formatDate(row.date_joined)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {rows === null && <p className={styles.state}>Loading customers…</p>}
        {rows?.length === 0 && <p className={styles.state}>No customers yet.</p>}
      </div>

      {rows && rows.length > 0 && (
        <p className={styles.count}>
          Showing {rows.length} {rows.length === 1 ? "customer" : "customers"}
        </p>
      )}
    </div>
  );
}
