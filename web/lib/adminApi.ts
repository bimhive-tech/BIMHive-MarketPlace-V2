/**
 * Client helpers for the staff-only admin API (/api/admin/*). Session cookie is
 * sent automatically; POSTs include the CSRF token (same pattern as lib/auth).
 */
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

export interface AdminStats {
  total: number;
  published: number;
  pending: number;
  draft: number;
  rejected: number;
  top_products: { name: string; slug: string; download_count: number }[];
}

export interface AdminProductRow {
  id: number;
  name: string;
  slug: string;
  type: string;
  short_description: string;
  category: string;
  partner: string;
  partner_verified: boolean;
  price: string;
  status: string;
  download_count: number;
  rating_average: string;
  rating_count: number;
  updated_at: string;
}

export interface AdminOptions {
  categories: { id: number; name: string }[];
  partners: { id: number; name: string }[];
  tags: { id: number; name: string }[];
  types: { value: string; label: string }[];
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, { credentials: "include" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

export const getAdminStats = () => getJSON<AdminStats>("/api/admin/stats");
export const getAdminOptions = () => getJSON<AdminOptions>("/api/admin/options");
export const getAdminProducts = (status = "all") =>
  getJSON<AdminProductRow[]>(`/api/admin/products?status=${status}`);

export async function createProduct(payload: Record<string, unknown>): Promise<AdminProductRow> {
  const token = await ensureCsrf();
  const res = await fetch("/api/admin/products", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(JSON.stringify(data));
  return data;
}
