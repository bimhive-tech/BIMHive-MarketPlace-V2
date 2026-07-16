/**
 * Client helpers for the staff-only admin API (/api/admin/*). Session cookie is
 * sent automatically; writes include the CSRF token (same pattern as lib/auth).
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
  const data = res.status === 204 ? ({} as T) : await res.json().catch(() => ({}));
  if (!res.ok) throw new AdminApiError(data, res.status);
  return data as T;
}

/** DRF error bodies nest strings inside arbitrarily deep dicts/lists (e.g. a
 * nested serializer field like `media` reports as `{media: [{url: [...]}]}`)
 * — dig in for the first actual message instead of assuming a flat shape. */
function firstErrorMessage(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = firstErrorMessage(item);
      if (found) return found;
    }
  } else if (value && typeof value === "object") {
    for (const nested of Object.values(value as Record<string, unknown>)) {
      const found = firstErrorMessage(nested);
      if (found) return found;
    }
  }
  return "";
}

export class AdminApiError extends Error {
  status: number;
  detail: string;
  fields: Record<string, string[]>;
  constructor(data: Record<string, unknown>, status: number) {
    const detail = firstErrorMessage(data) || "Something went wrong. Please try again.";
    super(detail);
    this.detail = detail;
    this.status = status;
    this.fields = data as Record<string, string[]>;
  }
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, { credentials: "include" });
  if (!res.ok) throw new AdminApiError(await res.json().catch(() => ({})), res.status);
  return res.json();
}

// ── Dashboard ──
export interface AdminStats {
  total: number;
  published: number;
  pending: number;
  draft: number;
  rejected: number;
  top_products: { name: string; slug: string; download_count: number }[];
}
export const getAdminStats = () => getJSON<AdminStats>("/api/admin/stats");

export interface AdminSystemStatus {
  debug_mode: boolean;
  database: string;
  licensing: { pepper_configured: boolean };
  storage: { bucket: string; configured: boolean };
  payments: { stripe_configured: boolean; paypal_configured: boolean };
}
export const getSystemStatus = () => getJSON<AdminSystemStatus>("/api/admin/system-status");

// ── Products ──
export interface AdminProductRow {
  id: number;
  name: string;
  slug: string;
  product_code: string;
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
  cover_image_url: string;
}

export interface AdminProductFeature {
  title: string;
  description: string;
  icon: string;
  sort_order: number;
}
export interface AdminProductMedia {
  media_type: "image" | "video";
  url: string;
  caption: string;
  is_cover: boolean;
  sort_order: number;
}
export interface AdminChangelogItem {
  version: string;
  released_at: string | null;
  notes: string;
  sort_order: number;
}
export interface AdminCompatibilityItem {
  label: string;
  value: string;
  sort_order: number;
}
export interface AdminProductFile {
  id: number;
  revit_version: string;
  version_label: string;
  storage_key: string;
  file_size_bytes: number;
  is_current: boolean;
  download_url: string;
}
export interface AdminDocSection {
  title: string;
  body: string;
  image_url: string;
  sort_order: number;
}
export interface AdminDocumentation {
  title: string;
  summary: string;
  overview: string;
  is_published: boolean;
  sections: AdminDocSection[];
}

export interface AdminProductDetail {
  id: number;
  name: string;
  slug: string;
  product_code: string;
  short_description: string;
  description: string;
  type: string;
  category: number;
  partner: number;
  tags: number[];
  price: string;
  download_count: number;
  default_trial_days: number;
  status: string;
  rejection_note: string;
  visibility: string;
  is_featured: boolean;
  cover_image_url: string;
  version: string;
  released_at: string | null;
  seo_title: string;
  seo_description: string;
  features: AdminProductFeature[];
  media: AdminProductMedia[];
  changelog: AdminChangelogItem[];
  compatibility: AdminCompatibilityItem[];
  documentation: AdminDocumentation | null;
  files: AdminProductFile[];
}

export interface AdminOptions {
  categories: { id: number; name: string }[];
  partners: { id: number; name: string }[];
  tags: { id: number; name: string }[];
  types: { value: string; label: string }[];
}

export const getAdminOptions = () => getJSON<AdminOptions>("/api/admin/options");
export const getAdminProducts = (status = "all") =>
  getJSON<AdminProductRow[]>(`/api/admin/products?status=${status}`);
export const getAdminProduct = (id: number) => getJSON<AdminProductDetail>(`/api/admin/products/${id}`);
export const createProduct = (payload: Record<string, unknown>) =>
  request<AdminProductDetail>("/api/admin/products", "POST", payload);
export const updateProduct = (id: number, payload: Record<string, unknown>) =>
  request<AdminProductDetail>(`/api/admin/products/${id}`, "PATCH", payload);
export const deleteProduct = (id: number) => request<void>(`/api/admin/products/${id}`, "DELETE");

export const uploadProductFile = (productId: number, form: FormData) =>
  request<AdminProductFile>(`/api/admin/products/${productId}/files`, "POST", form, true);
export const deleteProductFile = (fileId: number) =>
  request<void>(`/api/admin/products/files/${fileId}`, "DELETE");

export interface UploadedMedia {
  url: string;
  media_type: "image" | "video";
}
export const uploadProductMedia = (productId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return request<UploadedMedia>(`/api/admin/products/${productId}/media-upload`, "POST", form, true);
};

// ── Taxonomy: Categories / Tags / Partners / Collections ──
export interface AdminCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
  parent: number | null;
  sort_order: number;
  product_count: number;
}
export interface AdminTag {
  id: number;
  name: string;
  slug: string;
  product_count: number;
}
export interface AdminPartner {
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
  product_count: number;
  owner_email: string;
}
export interface AdminCollection {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
  is_featured: boolean;
  sort_order: number;
  products: number[];
  product_count: number;
}

// No trailing slash: the Next.js dev proxy strips it before forwarding to
// Django, so the routers are configured trailing_slash=False to match (see
// catalog/admin_urls.py).
function crud<T>(basePath: string) {
  return {
    list: () => getJSON<T[]>(basePath),
    create: (payload: Partial<T>) => request<T>(basePath, "POST", payload),
    update: (id: number, payload: Partial<T>) => request<T>(`${basePath}/${id}`, "PATCH", payload),
    remove: (id: number) => request<void>(`${basePath}/${id}`, "DELETE"),
  };
}

export const categoriesApi = crud<AdminCategory>("/api/admin/categories");
export const tagsApi = crud<AdminTag>("/api/admin/tags");
export const partnersApi = crud<AdminPartner>("/api/admin/partners");
export const collectionsApi = crud<AdminCollection>("/api/admin/collections");

// ── Licenses ──
export interface AdminLicense {
  id: string;
  product_code: string;
  product_name: string;
  user_email: string;
  license_key: string;
  fingerprint_preview: string;
  fingerprint_version: string;
  status: string;
  started_at: string;
  expires_at: string;
  first_seen_at: string;
  last_seen_at: string;
  install_count: number;
  plugin_version: string;
}
export const getAdminLicenses = (params?: { search?: string; status?: string }) => {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return getJSON<AdminLicense[]>(`/api/admin/licenses${qs ? `?${qs}` : ""}`);
};
export const revokeLicense = (id: string) =>
  request<AdminLicense>(`/api/admin/licenses/${id}/revoke`, "POST");
export const restoreLicense = (id: string) =>
  request<AdminLicense>(`/api/admin/licenses/${id}/restore`, "POST");
export const extendLicense = (id: string, days: number) =>
  request<AdminLicense>(`/api/admin/licenses/${id}/extend`, "POST", { days });

// ── Orders ──
export interface AdminOrder {
  id: string;
  product_name: string;
  product_code: string;
  user_email: string;
  license_key: string;
  amount: string;
  currency: string;
  payment_status: string;
  company_name: string;
  contact_email: string;
  requested_at: string;
  paid_at: string | null;
}
export const getAdminOrders = (status = "all") =>
  getJSON<AdminOrder[]>(`/api/admin/orders?status=${status}`);
export const setOrderStatus = (id: string, action: "restore" | "revoke" | "refund") =>
  request<AdminOrder>(`/api/admin/orders/${id}/status`, "POST", { action });

// ── Users / Customers / Roles ──
export interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
  role: number | null;
  role_name: string;
  order_count: number;
}
export const getAdminUsers = (search = "") =>
  getJSON<AdminUser[]>(`/api/admin/users${search ? `?search=${encodeURIComponent(search)}` : ""}`);
export const getAdminCustomers = () => getJSON<AdminUser[]>("/api/admin/customers");
export const updateAdminUser = (id: number, payload: { role?: number | null; is_active?: boolean; is_staff?: boolean }) =>
  request<AdminUser>(`/api/admin/users/${id}`, "PATCH", payload);

export interface AdminRole {
  id: number;
  name: string;
  description: string;
  grants_staff_access: boolean;
  user_count: number;
}
export const rolesApi = crud<AdminRole>("/api/admin/roles");

// ── Reviews ──
export interface AdminReview {
  id: number;
  product: number;
  product_name: string;
  author_name: string;
  rating: number;
  title: string;
  body: string;
  is_verified_purchase: boolean;
  created_at: string;
}
export const getAdminReviews = () => getJSON<AdminReview[]>("/api/admin/reviews");
export const deleteAdminReview = (id: number) => request<void>(`/api/admin/reviews/${id}`, "DELETE");

// ── Activity log ──
export interface AdminActivityEntry {
  id: number;
  actor_label: string;
  verb: string;
  target_label: string;
  metadata: Record<string, unknown>;
  created_at: string;
}
export const getAdminActivity = (params?: {
  actor?: string;
  verb?: string;
  date_from?: string;
  date_to?: string;
}) => {
  const clean = Object.fromEntries(Object.entries(params ?? {}).filter(([, v]) => v)) as Record<string, string>;
  const qs = new URLSearchParams(clean).toString();
  return getJSON<AdminActivityEntry[]>(`/api/admin/activity${qs ? `?${qs}` : ""}`);
};
