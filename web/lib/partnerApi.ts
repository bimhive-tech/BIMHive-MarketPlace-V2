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

async function request<T>(path: string, method: string, body?: unknown): Promise<T> {
  const token = await ensureCsrf();
  const res = await fetch(path, {
    method,
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: body ? JSON.stringify(body) : undefined,
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
}

export const getPartnerProfile = () => request<PartnerProfile>("/api/partner/profile", "GET");
export const updatePartnerProfile = (data: Partial<PartnerProfile>) =>
  request<PartnerProfile>("/api/partner/profile", "PATCH", data);
