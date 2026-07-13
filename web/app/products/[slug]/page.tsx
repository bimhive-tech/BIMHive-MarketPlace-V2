import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { Icon, type IconName } from "@/components/Icon/Icon";
import { StarRating } from "@/components/StarRating/StarRating";
import { SITE } from "@/config/site";
import { BuyBox } from "@/features/product/BuyBox/BuyBox";
import { ProductGallery } from "@/features/product/ProductGallery/ProductGallery";
import { ProductTabs } from "@/features/product/ProductTabs/ProductTabs";
import { PublisherCard } from "@/features/product/PublisherCard/PublisherCard";
import { getProduct } from "@/lib/api";
import type { ProductDetail } from "@/lib/types";

import styles from "./page.module.css";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) return { title: "Product not found" };
  return {
    title: product.seo_title || product.name,
    description: product.seo_description || product.short_description,
    openGraph: {
      title: product.seo_title || product.name,
      description: product.seo_description || product.short_description,
      type: "website",
    },
  };
}

const COMPAT_ICON: Record<string, IconName> = {
  Revit: "revit",
  Dynamo: "workflow",
  Platform: "windows",
  Language: "globe",
};

/** Compact pill label: "Windows"/"English" drop the label; others read "Label value". */
function compatLabel(label: string, value: string): string {
  if (!value) return label;
  if (["Platform", "Language", "OS"].includes(label)) return value;
  return `${label} ${value}`;
}

function jsonLd(product: ProductDetail) {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: product.name,
    description: product.short_description,
    applicationCategory: product.category.name,
    operatingSystem: "Windows",
    offers: {
      "@type": "Offer",
      price: product.price,
      priceCurrency: product.currency,
    },
    aggregateRating:
      product.rating_count > 0
        ? {
            "@type": "AggregateRating",
            ratingValue: product.rating_average,
            reviewCount: product.rating_count,
          }
        : undefined,
  };
}

export default async function ProductPage({ params }: PageProps) {
  const { slug } = await params;
  const product = await getProduct(slug);
  if (!product) notFound();

  return (
    <div className={`container ${styles.page}`}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd(product)) }}
      />

      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: product.category.name, href: `/catalog?category=${product.category.slug}` },
          { label: product.name },
        ]}
      />

      <div className={styles.top}>
        <div className={styles.leftCol}>
          <div className={styles.mediaInfoRow}>
            <div className={styles.galleryCol}>
              <ProductGallery media={product.media} name={product.name} slug={product.slug} />
            </div>

            <div className={styles.infoCol}>
              <p className={styles.eyebrow}>{product.partner?.name ?? SITE.name}</p>
              <h1 className={styles.title}>{product.name}</h1>
              <p className={styles.tagline}>{product.short_description}</p>

              <div className={styles.stats}>
                <StarRating value={Number(product.rating_average)} count={product.rating_count} />
                <span className={styles.dot} aria-hidden="true">•</span>
                <span className={styles.downloads}>
                  {product.download_count.toLocaleString()}+ downloads
                </span>
              </div>

              <p className={styles.desc}>{product.description}</p>

              {product.compatibility.length > 0 && (
                <div className={styles.chips}>
                  {product.compatibility.slice(0, 3).map((row) => (
                    <span key={row.id} className={styles.chip}>
                      <Icon name={COMPAT_ICON[row.label] ?? "check"} size={14} />
                      {compatLabel(row.label, row.value)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <ProductTabs product={product} />
        </div>

        <div className={styles.buyCol}>
          <BuyBox product={product} />
          <PublisherCard product={product} />
        </div>
      </div>
    </div>
  );
}
