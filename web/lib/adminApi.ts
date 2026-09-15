/**
 * Client helpers for the staff-only admin API (/api/admin/*). Session cookie is
 * sent automatically; writes include the CSRF token (same pattern as lib/auth).
 */
import type { PlanEnrollment, ProductDetail } from "@/lib/types";

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
  price_label: string;
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
  /** Display-only, struck through beside the real price. Never charged. */
  original_price: string | null;
  monthly_price: string | null;
  yearly_price: string | null;
  download_count: number;
  default_trial_days: number;
  default_trial_hours: number;
  default_trial_minutes: number;
  status: string;
  rejection_note: string;
  visibility: string;
  is_featured: boolean;
  membership_plan: number | null;
  is_hero_featured: boolean;
  hero_sort_order: number;
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
  /** `parent_name` is empty for a top-level category — the picker uses it to
   * group subcategories under the root they belong to. */
  categories: { id: number; name: string; parent_name: string | null }[];
  partners: { id: number; name: string }[];
  tags: { id: number; name: string }[];
  types: { value: string; label: string }[];
  membership_plans: { id: number; name: string; rank: number }[];
  updated_badge_days: number;
  new_badge_days: number;
}

export const getAdminOptions = () => getJSON<AdminOptions>("/api/admin/options");
// `asPartner` scopes a staff+partner caller to only their own partner's
// products — the partner-portal always passes it, so the same account can
// still see every partner's products unfiltered in the admin portal (see
// catalog.admin_api._effective_partner_id).
export const getAdminProducts = (status = "all", asPartner = false) =>
  getJSON<AdminProductRow[]>(`/api/admin/products?status=${status}${asPartner ? "&mine=1" : ""}`);
export const getAdminProduct = (id: number, asPartner = false) =>
  getJSON<AdminProductDetail>(`/api/admin/products/${id}${asPartner ? "?mine=1" : ""}`);
/** The product through the *storefront's* serializer, so the admin preview
 * renders the real thing — works on drafts and hidden products, which
 * /api/products/<slug> refuses to serve. Returns ProductDetail, not the admin
 * write shape. */
export const getProductPreview = (id: number, asPartner = false) =>
  getJSON<ProductDetail>(`/api/admin/products/${id}/preview${asPartner ? "?mine=1" : ""}`);
export const createProduct = (payload: Record<string, unknown>, asPartner = false) =>
  request<AdminProductDetail>(`/api/admin/products${asPartner ? "?mine=1" : ""}`, "POST", payload);
export const updateProduct = (id: number, payload: Record<string, unknown>, asPartner = false) =>
  request<AdminProductDetail>(`/api/admin/products/${id}${asPartner ? "?mine=1" : ""}`, "PATCH", payload);
export const deleteProduct = (id: number, asPartner = false) =>
  request<void>(`/api/admin/products/${id}${asPartner ? "?mine=1" : ""}`, "DELETE");

export const uploadProductFile = (productId: number, form: FormData, asPartner = false) =>
  request<AdminProductFile>(`/api/admin/products/${productId}/files${asPartner ? "?mine=1" : ""}`, "POST", form, true);
export const deleteProductFile = (fileId: number, asPartner = false) =>
  request<void>(`/api/admin/products/files/${fileId}${asPartner ? "?mine=1" : ""}`, "DELETE");

export interface UploadedMedia {
  url: string;
  media_type: "image" | "video";
}
interface MultipartUploadStart {
  upload_id: string;
  key: string;
  media_type: UploadedMedia["media_type"];
  part_size: number;
}

/** Sends a file to Django in small chunks that become one R2 multipart upload.
 * No single request lasts long enough to hit the Next.js proxy timeout or
 * Railway's request cap, so large videos get through. */
const uploadProductMediaInParts = async (productId: number, file: File, asPartner: boolean): Promise<UploadedMedia> => {
  const base = `/api/admin/products/${productId}/media-upload`;
  const query = asPartner ? "?mine=1" : "";
  const start = await request<MultipartUploadStart>(`${base}/start${query}`, "POST", {
    filename: file.name,
    content_type: file.type,
    size: file.size,
  });
  const ref = { upload_id: start.upload_id, key: start.key };

  try {
    const parts: { part_number: number; etag: string }[] = [];
    for (let offset = 0, partNumber = 1; offset < file.size; offset += start.part_size, partNumber++) {
      const form = new FormData();
      form.append("upload_id", ref.upload_id);
      form.append("key", ref.key);
      form.append("part_number", String(partNumber));
      form.append("chunk", file.slice(offset, offset + start.part_size), file.name);
      const { etag } = await request<{ etag: string }>(`${base}/part${query}`, "POST", form, true);
      parts.push({ part_number: partNumber, etag });
    }
    const { url } = await request<{ url: string }>(`${base}/complete${query}`, "POST", { ...ref, parts });
    return { url, media_type: start.media_type };
  } catch (err) {
    await request(`${base}/abort${query}`, "POST", ref).catch(() => undefined);
    throw err;
  }
};

/** Server-side upload: browser -> Django -> R2. Used when a direct PUT to R2
 * is blocked (bucket has no CORS rule). Videos go in chunks; images are small
 * enough for one request. */
const uploadProductMediaViaServer = (productId: number, file: File, asPartner: boolean) => {
  if (file.type.startsWith("video/")) return uploadProductMediaInParts(productId, file, asPartner);
  const form = new FormData();
  form.append("file", file);
  return request<UploadedMedia>(
    `/api/admin/products/${productId}/media-upload${asPartner ? "?mine=1" : ""}`,
    "POST",
    form,
    true,
  );
};
/** Uploads the file bytes straight to R2, not through this app's own server —
 * Django only ever handles a small JSON request for a presigned URL. A large
 * video routed through the full browser -> Railway -> Next.js -> Django ->
 * R2 chain in one request was silently failing (Railway's edge hard-caps any
 * single request at ~5 minutes, independent of this app's own settings); a
 * direct PUT to R2 isn't subject to that at all. */
export const uploadProductMedia = async (productId: number, file: File, asPartner = false): Promise<UploadedMedia> => {
  const { upload_url, url, media_type } = await request<{ upload_url: string; url: string; media_type: "image" | "video" }>(
    `/api/admin/products/${productId}/media-upload-url${asPartner ? "?mine=1" : ""}`,
    "POST",
    { filename: file.name, content_type: file.type, size: file.size },
  );

  // A CORS rejection from the bucket never produces a response — fetch just
  // throws. Fall back to uploading through this app, which needs no CORS.
  const putRes = await fetch(upload_url, { method: "PUT", body: file, headers: { "Content-Type": file.type } }).catch(
    () => null,
  );
  if (!putRes) return uploadProductMediaViaServer(productId, file, asPartner);
  if (!putRes.ok) {
    throw new AdminApiError({ detail: "The upload to storage failed. Please try again." }, putRes.status);
  }
  return { url, media_type };
};

// ── Taxonomy: Categories / Tags / Partners ──
export interface AdminCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
  parent: number | null;
  parent_name: string;
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

export interface AdminPromotion {
  id: number;
  name: string;
  badge_label: string;
  headline: string;
  cta_label: string;
  cta_url: string;
  discount_percent: number;
  scope: "all" | "category" | "products" | "plan";
  category: number | null;
  category_name: string;
  products: number[];
  plan: number | null;
  plan_name: string;
  starts_at: string;
  ends_at: string;
  is_active: boolean;
  show_countdown: boolean;
  priority: number;
  /** Server-computed: inside its window AND active right now. */
  is_live: boolean;
}

export interface AdminMembershipPlan {
  id: number;
  name: string;
  slug: string;
  rank: number;
  tagline: string;
  description: string;
  /** One checklist item per line. */
  features: string;
  enrollment: PlanEnrollment;
  monthly_price: string | null;
  yearly_price: string | null;
  original_monthly_price: string | null;
  original_yearly_price: string | null;
  currency: string;
  seats_per_product: number;
  is_active: boolean;
  is_featured: boolean;
  sort_order: number;
  /** Products assigned to this exact tier (not cumulative). */
  product_count: number;
  member_count: number;
}

export interface AdminMembership {
  id: string;
  user_email: string;
  plan: number;
  plan_name: string;
  status: string;
  display_status: string;
  billing_period: "monthly" | "yearly";
  license_key: string;
  amount: string;
  currency: string;
  started_at: string | null;
  expires_at: string | null;
  cancelled_at: string | null;
  /** Products this universal key has actually been activated on. */
  granted_count: number;
  note: string;
}

export const categoriesApi = crud<AdminCategory>("/api/admin/categories");
export const promotionsApi = crud<AdminPromotion>("/api/admin/promotions");
export const membershipPlansApi = crud<AdminMembershipPlan>("/api/admin/membership-plans");

export const getAdminMemberships = () => getJSON<AdminMembership[]>("/api/admin/memberships");
/** Ends a membership and revokes every license its universal key opened. */
export const revokeMembership = (id: string, status: string) =>
  request<AdminMembership>(`/api/admin/memberships/${id}/revoke`, "POST", { status });
/** Turns one back on — also the way to test the flow without a live payment. */
export const reinstateMembership = (id: string) =>
  request<AdminMembership>(`/api/admin/memberships/${id}/reinstate`, "POST", {});
export const tagsApi = crud<AdminTag>("/api/admin/tags");
export const partnersApi = crud<AdminPartner>("/api/admin/partners");

// ── Licenses ──
export interface AdminLicense {
  id: string;
  product_code: string;
  product_name: string;
  user_email: string;
  license_key: string;
  seats: number;
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
export const releaseLicense = (id: string) =>
  request<AdminLicense>(`/api/admin/licenses/${id}/release`, "POST");

// ── Orders ──
export interface AdminOrder {
  id: string;
  product_name: string;
  product_code: string;
  user_email: string;
  license_key: string;
  seats: number;
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
export const setOrderSeats = (id: string, seats: number) =>
  request<AdminOrder>(`/api/admin/orders/${id}/seats`, "POST", { seats });

// ── License codes ──
export interface AdminLicenseCode {
  id: string;
  code: string;
  product: string;
  product_name: string;
  product_code: string;
  seats: number;
  duration_days: number | null;
  status: "unredeemed" | "redeemed" | "revoked";
  note: string;
  redeemed_by_email: string;
  created_at: string;
  redeemed_at: string | null;
}
export interface NewAdminLicenseCode {
  product: string;
  seats: number;
  duration_days: number | null;
  note: string;
}
export const getAdminLicenseCodes = (params?: { product?: string; status?: string }) => {
  const qs = new URLSearchParams(
    Object.entries(params ?? {}).reduce<Record<string, string>>((acc, [k, v]) => {
      if (v !== undefined) acc[k] = String(v);
      return acc;
    }, {}),
  ).toString();
  return getJSON<AdminLicenseCode[]>(`/api/admin/license-codes${qs ? `?${qs}` : ""}`);
};
export const createAdminLicenseCode = (payload: NewAdminLicenseCode) =>
  request<AdminLicenseCode>("/api/admin/license-codes", "POST", payload);
export const revokeAdminLicenseCode = (id: string) =>
  request<AdminLicenseCode>(`/api/admin/license-codes/${id}/revoke`, "POST");

export interface AdminLicenseProductOption {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}
export const getAdminLicenseOptions = () =>
  getJSON<{ products: AdminLicenseProductOption[] }>("/api/admin/licenses/options");

// ── Users / Customers / Roles ──
export interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  date_joined: string;
  role: number | null;
  role_name: string;
  order_count: number;
}
export const getAdminUsers = (search = "") =>
  getJSON<AdminUser[]>(`/api/admin/users${search ? `?search=${encodeURIComponent(search)}` : ""}`);
export const updateAdminUser = (
  id: number,
  payload: { role?: number | null; is_active?: boolean; is_staff?: boolean; is_superuser?: boolean },
) => request<AdminUser>(`/api/admin/users/${id}`, "PATCH", payload);

// Genuinely separate from AdminUser/getAdminUsers — Customers is a read-only,
// permission-gated view (no is_staff/role), not the same sensitive endpoint
// Users management uses. See api/accounts/admin_api.py::AdminCustomerListView.
export interface AdminCustomer {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  date_joined: string;
  order_count: number;
}
export const getAdminCustomers = (search = "") =>
  getJSON<AdminCustomer[]>(`/api/admin/customers${search ? `?search=${encodeURIComponent(search)}` : ""}`);

export interface AdminRole {
  id: number;
  name: string;
  description: string;
  grants_staff_access: boolean;
  permissions: string[];
  user_count: number;
}
export const rolesApi = crud<AdminRole>("/api/admin/roles");

// Mirrors api/accounts/permissions.py::ADMIN_PERMISSIONS exactly — kept in
// sync by convention, same as AdminSidebar's own hardcoded section list.
// Grouped for the Roles & Permissions checklist UI.
export const ADMIN_PERMISSIONS: { key: string; label: string; group: string }[] = [
  { key: "dashboard.view", label: "View Dashboard", group: "Overview" },
  { key: "activity.view", label: "View Activity", group: "Overview" },
  { key: "orders.manage", label: "Manage Orders", group: "Overview" },
  { key: "customers.view", label: "View Customers", group: "Overview" },
  { key: "reviews.moderate", label: "Moderate Reviews", group: "Overview" },
  { key: "licenses.manage", label: "Manage Licenses", group: "Overview" },
  { key: "memberships.manage", label: "Manage Memberships", group: "Overview" },
  { key: "products.manage", label: "Manage Products", group: "Products & Content" },
  { key: "promotions.manage", label: "Manage Promotions", group: "Products & Content" },
  { key: "membership_plans.manage", label: "Manage Membership Plans", group: "Products & Content" },
  { key: "categories.manage", label: "Manage Categories", group: "Products & Content" },
  { key: "tags.manage", label: "Manage Tags", group: "Products & Content" },
  { key: "partners.manage", label: "Manage Partners", group: "Products & Content" },
];

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

// ── Plugin builds (auto-generated installers — see /api-docs or installer/README) ──
export interface PluginResourceFile {
  id: string;
  kind: "resource" | "dependency";
  original_filename: string;
  destination_path: string;
  sort_order: number;
}
export interface PluginBuild {
  id: string;
  product: number;
  product_name: string;
  revit_year: string;
  plugin_version: string;
  dll_filename: string;
  addin_filename: string;
  scope: "perUser" | "perMachine";
  resource_files: PluginResourceFile[];
  created_at: string;
  updated_at: string;
}
export interface DestinationOption {
  token: string;
  scope: string;
  label: string;
  hint: string;
}

const mineParam = (asPartner: boolean, hasQuery = false) => (asPartner ? `${hasQuery ? "&" : "?"}mine=1` : "");

export const getPluginBuilds = (productId: number, asPartner = false) =>
  getJSON<PluginBuild[]>(`/api/admin/products/${productId}/plugin-builds${mineParam(asPartner)}`);
export const createPluginBuild = (productId: number, revitYear: string, asPartner = false) =>
  request<PluginBuild>(
    `/api/admin/products/${productId}/plugin-builds${mineParam(asPartner)}`,
    "POST",
    { revit_year: revitYear },
  );
export const updatePluginBuild = (id: string, payload: { plugin_version?: string }, asPartner = false) =>
  request<PluginBuild>(`/api/admin/plugin-builds/${id}${mineParam(asPartner)}`, "PATCH", payload);
export const deletePluginBuild = (id: string, asPartner = false) =>
  request<void>(`/api/admin/plugin-builds/${id}${mineParam(asPartner)}`, "DELETE");
export const uploadPluginDll = (id: string, file: File, asPartner = false) => {
  const form = new FormData();
  form.append("file", file);
  return request<PluginBuild>(`/api/admin/plugin-builds/${id}/dll${mineParam(asPartner)}`, "POST", form, true);
};
export const uploadPluginAddin = (id: string, file: File, asPartner = false) => {
  const form = new FormData();
  form.append("file", file);
  return request<PluginBuild>(`/api/admin/plugin-builds/${id}/addin${mineParam(asPartner)}`, "POST", form, true);
};
export const uploadPluginResource = (
  id: string,
  file: File,
  destinationPath: string,
  kind: "resource" | "dependency",
  asPartner = false,
) => {
  const form = new FormData();
  form.append("file", file);
  form.append("destination_path", destinationPath);
  form.append("kind", kind);
  return request<PluginResourceFile>(
    `/api/admin/plugin-builds/${id}/resources${mineParam(asPartner)}`,
    "POST",
    form,
    true,
  );
};
export const deletePluginResource = (buildId: string, resourceId: string, asPartner = false) =>
  request<void>(
    `/api/admin/plugin-builds/${buildId}/resources/${resourceId}${mineParam(asPartner)}`,
    "DELETE",
  );
export const getDestinationOptions = () =>
  getJSON<DestinationOption[]>("/api/admin/plugin-builds/destination-options");
