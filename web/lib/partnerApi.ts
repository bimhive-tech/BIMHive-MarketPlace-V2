/**
 * Client helpers for the partner self-service API (/api/partner/*). Session
 * cookie is sent automatically; writes include the CSRF token (same pattern
 * as lib/adminApi.ts and lib/auth.ts).
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

async function request<T>(path: string, method: string, body?: unknown, isForm = false): Promise<T> {
  const token = await ensureCsrf();
  const headers: Record<string, string> = { "X-CSRFToken": token };
  if (!isForm) headers["Content-Type"] = "application/json";
  const res = await fetch(path, {
    method,
    credentials: "include",
    headers,
    body: body ? (isForm ? (body as FormData) : JSON.stringify(body)) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new PartnerApiError(data, res.status);
  return data as T;
}

export class PartnerApiError extends Error {
  status: number;
  detail: string;
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

export interface PartnerProfile {
  id: number;
  name: string;
  slug: string;
  tagline: string;
  bio: string;
  logo_url: string;
  website: string;
  is_verified: boolean;
  status: "pending" | "approved" | "rejected";
  rejection_note: string;
}

export const getPartnerProfile = () => request<PartnerProfile>("/api/partner/profile", "GET");
export const updatePartnerProfile = (data: Partial<PartnerProfile>) =>
  request<PartnerProfile>("/api/partner/profile", "PATCH", data);

export const applyToBecomeSeller = (companyName: string, logo: File | null) => {
  const form = new FormData();
  form.append("company_name", companyName);
  if (logo) form.append("logo", logo);
  return request<PartnerProfile>("/api/partner/apply", "POST", form, true);
};

export interface PartnerSale {
  id: string;
  product_name: string;
  amount: string;
  currency: string;
  payment_status: string;
  requested_at: string;
  paid_at: string | null;
}
export interface PartnerSalesSummary {
  total_revenue: string;
  order_count: number;
  orders: PartnerSale[];
}
export const getPartnerSales = () => request<PartnerSalesSummary>("/api/partner/sales", "GET");
