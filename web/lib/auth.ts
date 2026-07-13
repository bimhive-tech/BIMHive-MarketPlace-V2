/**
 * Client-side auth helpers. Talks to the same-origin session API (Django via the
 * Next proxy). CSRF: we fetch a token cookie first, then send it as X-CSRFToken on
 * state-changing requests. Cookies flow automatically (same origin).
 */
import type { User } from "@/lib/types";

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
  const data = res.status === 204 ? {} : await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new AuthError(data);
  }
  return data as T;
}

export class AuthError extends Error {
  detail: string;
  fields: Record<string, string[]>;
  constructor(data: Record<string, unknown>) {
    const detail =
      (data.detail as string) ||
      (Array.isArray(data.email) ? (data.email as string[])[0] : "") ||
      (Array.isArray(data.password) ? (data.password as string[])[0] : "") ||
      (Array.isArray(data.current_password) ? (data.current_password as string[])[0] : "") ||
      (Array.isArray(data.new_password) ? (data.new_password as string[])[0] : "") ||
      "Something went wrong. Please try again.";
    super(detail);
    this.detail = detail;
    this.fields = data as Record<string, string[]>;
  }
}

export function register(email: string, password: string, fullName: string) {
  return request<User>("/api/auth/register", "POST", { email, password, full_name: fullName });
}

export function login(email: string, password: string) {
  return request<User>("/api/auth/login", "POST", { email, password });
}

export function logout() {
  return request<{ detail: string }>("/api/auth/logout", "POST");
}

export async function me(): Promise<User | null> {
  const res = await fetch("/api/auth/me", { credentials: "include" });
  if (!res.ok) return null;
  return res.json();
}

export interface ProfileUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  profile?: { company?: string; job_title?: string; bio?: string };
}

export function updateProfile(data: ProfileUpdate) {
  return request<User>("/api/auth/me", "PATCH", data);
}

export function changePassword(currentPassword: string, newPassword: string) {
  return request<{ detail: string }>("/api/auth/change-password", "POST", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

export function deleteAccount() {
  return request<void>("/api/auth/me", "DELETE");
}
