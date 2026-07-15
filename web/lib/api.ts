/**
 * Server-side API client. Runs in React Server Components, so it talks to Django
 * directly via API_INTERNAL_URL (not the browser proxy). See ARCHITECTURE §3.
 */
import type {
  Category,
  Collection,
  DocumentationDetail,
  DocumentationListItem,
  HomeData,
  Partner,
  ProductCard,
  ProductDetail,
} from "@/lib/types";

const API_BASE = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";

async function getJSON<T>(path: string, revalidate = 60): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    next: { revalidate },
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getHome() {
  return getJSON<HomeData>("/api/home");
}

export function getProducts(params?: { category?: string; type?: string; q?: string; collection?: string; partner?: string }) {
  const clean = Object.fromEntries(
    Object.entries(params ?? {}).filter(([, v]) => v),
  ) as Record<string, string>;
  const qs = new URLSearchParams(clean).toString();
  return getJSON<ProductCard[]>(`/api/products${qs ? `?${qs}` : ""}`);
}

export function getCategories() {
  return getJSON<Category[]>("/api/categories");
}

export async function getProduct(slug: string): Promise<ProductDetail | null> {
  try {
    return await getJSON<ProductDetail>(`/api/products/${slug}`);
  } catch {
    return null;
  }
}

export function getCollections() {
  return getJSON<Collection[]>("/api/collections");
}

export async function getCollection(slug: string): Promise<Collection | null> {
  try {
    return await getJSON<Collection>(`/api/collections/${slug}`);
  } catch {
    return null;
  }
}

export async function getPartner(slug: string): Promise<Partner | null> {
  try {
    return await getJSON<Partner>(`/api/partners/${slug}`);
  } catch {
    return null;
  }
}

export function getDocumentationList() {
  return getJSON<DocumentationListItem[]>("/api/documentation");
}

export async function getDocumentation(slug: string): Promise<DocumentationDetail | null> {
  try {
    return await getJSON<DocumentationDetail>(`/api/documentation/${slug}`);
  } catch {
    return null;
  }
}
