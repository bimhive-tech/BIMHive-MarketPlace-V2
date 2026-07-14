/**
 * Client helpers for the signed-in customer's own data (/api/account/*) — orders,
 * licenses, downloads, and claiming free products. Reads need no CSRF token
 * (session cookie alone scopes the query); the one write here (claimFreeProduct)
 * follows the same CSRF-token pattern as lib/auth.ts.
 */
import type { Review } from "@/lib/types";
async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, { credentials: "include" });
  if (!res.ok) throw new Error(`Account API ${path} failed: ${res.status}`);
  return res.json();
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function ensureCsrf(): Promise<string> {
  let token = getCookie("csrftoken");
  if (!token) {
    await fetch("/api/auth/csrf", { credentials: "include" });
    token = getCookie("csrftoken");
  }
  return token ?? "";
}

export class AccountApiError extends Error {
  detail: string;
  status: number;
  constructor(data: Record<string, unknown>, status: number) {
    const firstField = Object.keys(data)[0];
    const detail =
      (data.detail as string) ||
      (firstField && Array.isArray(data[firstField]) ? (data[firstField] as string[])[0] : "") ||
      "Something went wrong. Please try again.";
    super(detail);
    this.detail = detail;
    this.status = status;
  }
}

export interface AccountOrder {
  id: string;
  product_name: string;
  product_code: string;
  amount: string;
  currency: string;
  payment_status: string;
  license_key: string;
  requested_at: string;
  paid_at: string | null;
}
export const getAccountOrders = () => getJSON<AccountOrder[]>("/api/account/orders");

export interface AccountMachine {
  fingerprint_preview: string;
  status: string;
  last_seen_at: string;
  install_count: number;
  plugin_version: string;
}
export interface AccountLicense {
  id: string;
  product_name: string;
  product_code: string;
  payment_status: string;
  license_key: string;
  seats: number;
  requested_at: string;
  paid_at: string | null;
  machines: AccountMachine[];
}
export const getAccountLicenses = () => getJSON<AccountLicense[]>("/api/account/licenses");

export interface AccountDownloadFile {
  id: number;
  revit_version: string;
  version_label: string;
  is_current: boolean;
  download_url: string;
}
export interface AccountDownload {
  id: string;
  product_name: string;
  cover_image_url: string;
  files: AccountDownloadFile[];
}
export const getAccountDownloads = () => getJSON<AccountDownload[]>("/api/account/downloads");

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const token = await ensureCsrf();
  const res = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new AccountApiError(data, res.status);
  return data;
}

export const claimFreeProduct = (slug: string) => postJSON<AccountOrder>("/api/account/claim-free", { slug });

export interface ReviewSubmission {
  rating: number;
  title: string;
  body: string;
}
// Returns the full Review shape (see lib/types.ts) so the caller can render it
// immediately — the product detail page's own fetch is cached for 60s, so
// relying on that to show a just-posted review would leave it invisible for
// up to a minute.
export const submitReview = (productSlug: string, review: ReviewSubmission) =>
  postJSON<Review>(`/api/products/${productSlug}/reviews`, review);
