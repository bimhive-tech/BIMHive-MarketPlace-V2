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

async function ensureCsrf(forceRefresh = false): Promise<string> {
  let token = forceRefresh ? null : getCookie("csrftoken");
  if (!token) {
    await fetch("/api/auth/csrf", { credentials: "include" });
    token = getCookie("csrftoken");
  }
  return token ?? "";
}

function isCsrfFailure(status: number, data: Record<string, unknown>): boolean {
  return status === 403 && String(data.detail ?? "").startsWith("CSRF Failed");
}

async function request<T>(path: string, method: string, body?: unknown, allowRetry = true): Promise<T> {
  const token = await ensureCsrf();
  const res = await fetch(path, {
    method,
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = res.status === 204 ? {} : await res.json().catch(() => ({}));
  if (!res.ok) {
    // A csrftoken cookie that's present but no longer accepted used to be a
    // dead end: ensureCsrf only refetched when there was *no* cookie, so every
    // write went on sending the same rejected token and failing the same way.
    // Retrying once against a fresh token is safe — DRF rejects CSRF during
    // authentication, before the view runs, so the first attempt changed
    // nothing.
    if (allowRetry && isCsrfFailure(res.status, data)) {
      await ensureCsrf(true);
      return request<T>(path, method, body, false);
    }
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

// Client components that show the signed-in state (AuthNav's navbar avatar)
// fetch `me()` once on mount and have no other way to learn a *different*
// component just signed the user in/out — a client-side route change alone
// doesn't remount them or re-run their effects. This is a tiny pub/sub so
// any such component can ask to be told right when it happens, instead of
// staying stale until a full page reload.
const AUTH_CHANGE_EVENT = "bimhive:auth-changed";

function notifyAuthChanged() {
  if (typeof window !== "undefined") window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

export function onAuthChanged(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(AUTH_CHANGE_EVENT, callback);
  return () => window.removeEventListener(AUTH_CHANGE_EVENT, callback);
}

export interface SignupOption {
  value: string;
  label: string;
}

export interface CountryOption {
  code: string;
  name: string;
}

/** The profession/country/university dropdowns' contents — backend-driven so
 * the lists only ever need to change in one place (see
 * accounts.api.SignupOptionsView). */
export async function getSignupOptions(): Promise<{
  professions: SignupOption[];
  countries: CountryOption[];
  universities: string[];
}> {
  const res = await fetch("/api/auth/signup-options");
  if (!res.ok) return { professions: [], countries: [], universities: [] };
  const data = await res.json();
  // Tolerates an older backend that predates the university list.
  return { universities: [], ...data };
}

export interface RegisterInput {
  email: string;
  password: string;
  fullName: string;
  /** Required — regional pricing is keyed off this. */
  country: string;
  /** Optional. */
  profession?: string;
  isStudent?: boolean;
  /** Optional, students only. Free text — the dropdown offers "Other". */
  university?: string;
  /** Optional, non-students only. */
  company?: string;
}

export async function register(input: RegisterInput) {
  const user = await request<User>("/api/auth/register", "POST", {
    email: input.email,
    password: input.password,
    full_name: input.fullName,
    country: input.country,
    profession: input.profession || "",
    is_student: input.isStudent ?? false,
    university: input.university || "",
    company: input.company || "",
  });
  notifyAuthChanged();
  return user;
}

export async function login(email: string, password: string) {
  const user = await request<User>("/api/auth/login", "POST", { email, password });
  notifyAuthChanged();
  return user;
}

/**
 * Ends the session, then reloads onto the homepage.
 *
 * The full navigation is the point, not laziness. Clearing local state
 * optimistically and routing client-side let the UI claim a logged-out state
 * the server had never agreed to: the signed-out header painted, the auth-change
 * listeners re-ran me(), that came back 200 because the session was still
 * alive, and the nav flipped straight back — a flash of "Log in / Sign up" and
 * then nothing, with the user still signed in after a hard refresh. A real page
 * load re-reads me() from the server for every component at once, so what's on
 * screen afterwards is whatever is actually true.
 *
 * The POST's failure is swallowed for the same reason: signing out shouldn't
 * depend on it succeeding (a session can already be dead server-side), and the
 * reload will show the truth either way rather than a state we guessed at.
 */
export async function logout(): Promise<void> {
  try {
    await request<{ detail: string }>("/api/auth/logout", "POST");
  } catch {
    // Intentionally swallowed — see above.
  }
  // No notifyAuthChanged() here: the listeners would fire a me() request into
  // a page that is already unloading, which is exactly the race above.
  window.location.assign("/");
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
  profile?: {
    company?: string;
    job_title?: string;
    bio?: string;
    profession?: string;
    country?: string;
    is_student?: boolean;
    university?: string;
  };
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

export interface AccountSession {
  id: string;
  ip_address: string;
  user_agent: string;
  expires_at: string;
  is_current: boolean;
}

export async function getSessions(): Promise<AccountSession[]> {
  const res = await fetch("/api/auth/sessions", { credentials: "include" });
  if (!res.ok) throw new AuthError(await res.json().catch(() => ({})));
  return res.json();
}

export function revokeSession(id: string) {
  return request<{ detail: string }>(`/api/auth/sessions/${encodeURIComponent(id)}/revoke`, "POST");
}
