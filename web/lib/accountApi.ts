/**
 * Client helpers for the signed-in customer's own data (/api/account/*) — orders,
 * licenses, downloads. Read-only (GET), so no CSRF token is needed; the session
 * cookie alone scopes every query to request.user server-side.
 */
async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, { credentials: "include" });
  if (!res.ok) throw new Error(`Account API ${path} failed: ${res.status}`);
  return res.json();
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
