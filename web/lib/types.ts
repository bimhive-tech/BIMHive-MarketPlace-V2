/** Shapes returned by the Django storefront API (see api/catalog/serializers.py). */

export interface Category {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string;
  product_count: number;
}

export interface Collection {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string;
  product_count: number;
  is_featured: boolean;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
}

export interface Partner {
  id: number;
  name: string;
  slug: string;
  tagline: string;
  bio: string;
  logo_url: string;
  website: string;
  is_verified: boolean;
}

export interface ProductCard {
  id: number;
  name: string;
  slug: string;
  type: string;
  short_description: string;
  cover_image_url: string;
  price: string;
  price_label: string;
  currency: string;
  rating_average: string;
  rating_count: number;
  download_count: number;
  category: string;
  category_slug: string;
  is_featured: boolean;
}

export interface KeyFeature {
  id: number;
  title: string;
  description: string;
  icon: string;
  sort_order: number;
}

export interface ChangelogEntry {
  id: number;
  version: string;
  released_at: string | null;
  notes: string[];
}

export interface CompatibilityEntry {
  id: number;
  label: string;
  value: string;
  sort_order: number;
}

export interface ProductMedia {
  id: number;
  media_type: "image" | "video";
  url: string;
  caption: string;
  is_cover: boolean;
  sort_order: number;
}

export interface DocSection {
  id: number;
  title: string;
  body: string;
  image_url: string;
  sort_order: number;
}

export interface Documentation {
  id: number;
  slug: string;
  title: string;
  summary: string;
  overview: string;
  is_published: boolean;
  sections: DocSection[];
}

export interface Review {
  id: number;
  author_name: string;
  rating: number;
  title: string;
  body: string;
  is_verified_purchase: boolean;
  created_at: string;
}

export interface RatingBreakdownRow {
  stars: number;
  count: number;
  percent: number;
}

export interface ProductDetail extends Omit<ProductCard, "category"> {
  description: string;
  team_price: string | null;
  team_seats: number;
  default_trial_days: number;
  version: string;
  released_at: string | null;
  rating_breakdown: RatingBreakdownRow[];
  seo_title: string;
  seo_description: string;
  category: Category;
  partner: Partner | null;
  tags: Tag[];
  media: ProductMedia[];
  features: KeyFeature[];
  changelog: ChangelogEntry[];
  compatibility: CompatibilityEntry[];
  documentation: Documentation | null;
  reviews: Review[];
}

export interface HomeData {
  categories: Category[];
  featured_products: ProductCard[];
  collections: Collection[];
}
