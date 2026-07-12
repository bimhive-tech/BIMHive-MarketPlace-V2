/**
 * Server-side API client. Runs in React Server Components, so it talks to Django
 * directly via API_INTERNAL_URL (not the browser proxy). See ARCHITECTURE §3.
 */
import type { HomeData, ProductCard, ProductDetail } from "@/lib/types";

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

export function getProducts(params?: { category?: string; type?: string }) {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return getJSON<ProductCard[]>(`/api/products/${qs ? `?${qs}` : ""}`);
}

export async function getProduct(slug: string): Promise<ProductDetail | null> {
  try {
    return await getJSON<ProductDetail>(`/api/products/${slug}/`);
  } catch {
    return null;
  }
}
