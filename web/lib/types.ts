/** Shapes returned by the Django storefront API (see api/catalog/serializers.py). */

/** DRF's PageNumberPagination envelope — see ProductPagination in api/catalog/views.py. */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  is_staff: boolean;
  date_joined: string;
  profile: {
    company: string;
    job_title: string;
    bio: string;
    avatar_url: string;
    account_type: string;
    profession: string;
    profession_label: string;
    /** ISO 3166-1 alpha-2, e.g. "US". Empty string when unset. */
    country: string;
    country_name: string;
  } | null;
  partner: {
    id: number;
    name: string;
    slug: string;
    status: "pending" | "approved" | "rejected";
    rejection_note: string;
  } | null;
}

/** A category with no children of its own. The storefront taxonomy is two
 * levels: one root ("Revit Plugins") and its subcategories. */
export interface Subcategory {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string;
  parent_slug: string;
  product_count: number;
}

export interface Category extends Subcategory {
  children: Subcategory[];
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

/** A live discount on one product. The product's own price fields stay at list
 * price so the UI can strike them through next to these. */
export interface ProductPromotion {
  label: string;
  headline: string;
  discount_percent: number;
  ends_at: string;
  price: string;
  monthly_price: string | null;
  yearly_price: string | null;
}

/** The site-wide countdown offer above the nav (`/api/promotions/banner`).
 * Always a discount on an All-Access plan — never a per-product sale. */
export interface PromotionBanner {
  id: number;
  badge_label: string;
  headline: string;
  discount_percent: number;
  ends_at: string;
  cta_label: string;
  cta_url: string;
  plan_name: string;
  plan_slug: string;
}

/** A live discount on a membership plan — same shape as ProductPromotion. */
export interface PlanPromotion {
  label: string;
  headline: string;
  discount_percent: number;
  ends_at: string;
  monthly_price: string | null;
  yearly_price: string | null;
}

/** The All-Access tier a product belongs to, if any. */
export interface ProductMembership {
  plan_name: string;
  plan_slug: string;
  monthly_price: string | null;
  /** True when the signed-in viewer's own membership already covers this. */
  included_in_my_plan: boolean;
}

/** A purchasable All-Access tier (`/api/membership/plans`). */
export interface MembershipPlan {
  id: number;
  name: string;
  slug: string;
  rank: number;
  tagline: string;
  description: string;
  monthly_price: string | null;
  yearly_price: string | null;
  currency: string;
  yearly_savings_percent: number | null;
  seats_per_product: number;
  is_featured: boolean;
  /** Live products this tier unlocks, including lower tiers'. */
  product_count: number;
  promotion: PlanPromotion | null;
}

/** The signed-in customer's own membership, universal key included. */
export interface AccountMembership {
  id: string;
  plan_name: string;
  plan_slug: string;
  status: string;
  display_status: string;
  is_usable: boolean;
  billing_period: "monthly" | "yearly";
  license_key: string;
  amount: string;
  currency: string;
  seats_per_product: number;
  started_at: string | null;
  expires_at: string | null;
  cancelled_at: string | null;
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
  monthly_price: string | null;
  yearly_price: string | null;
  is_subscription: boolean;
  currency: string;
  rating_average: string;
  rating_count: number;
  download_count: number;
  category: string;
  category_slug: string;
  is_featured: boolean;
  promotion: ProductPromotion | null;
  membership: ProductMembership | null;
  /** Published recently — see NEW_PRODUCT_BADGE_DAYS in the Django settings. */
  is_new: boolean;
  /** Shipped a new version recently, and no longer new. */
  is_updated: boolean;
  version: string;
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

/** The standalone /docs library — same underlying Documentation row as above,
 * but shaped for a page that isn't already inside a specific product's context. */
export interface DocumentationListItem {
  id: number;
  slug: string;
  title: string;
  summary: string;
  product_name: string;
  product_slug: string;
  product_cover_image_url: string;
}

export interface DocumentationDetail extends DocumentationListItem {
  overview: string;
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

export interface TrialBuild {
  id: string;
  revit_year: string;
}

export interface ProductDetail extends Omit<ProductCard, "category"> {
  description: string;
  is_free: boolean;
  last_release_at: string | null;
  yearly_savings_percent: number | null;
  default_trial_days: number;
  default_trial_hours: number;
  default_trial_minutes: number;
  has_trial: boolean;
  trial_builds: TrialBuild[];
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
  /** What the hero rotates through — discounted products first. */
  spotlight_products: ProductCard[];
}
