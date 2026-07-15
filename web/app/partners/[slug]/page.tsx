import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Breadcrumb } from "@/components/Breadcrumb/Breadcrumb";
import { EmptyState } from "@/components/EmptyState/EmptyState";
import { Icon } from "@/components/Icon/Icon";
import { ProductCard } from "@/components/ProductCard/ProductCard";
import { getPartner, getProducts } from "@/lib/api";

import styles from "./page.module.css";

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const partner = await getPartner(slug);
  if (!partner) return { title: "Partner not found" };
  return { title: partner.name, description: partner.tagline || partner.bio || undefined };
}

export default async function PartnerProfilePage({ params }: PageProps) {
  const { slug } = await params;
  const partner = await getPartner(slug);
  if (!partner) notFound();

  const products = await getProducts({ partner: slug });

  return (
    <div className={`container ${styles.page}`}>
      <Breadcrumb items={[{ label: "Home", href: "/" }, { label: "Catalog", href: "/catalog" }, { label: partner.name }]} />

      <header className={styles.head}>
        <span className={styles.avatar}>
          <Icon name="library" size={28} />
        </span>
        <div>
          <p className={styles.name}>
            {partner.name}
            {partner.is_verified && <Icon name="check-circle" size={18} className={styles.verified} />}
          </p>
          {partner.tagline && <p className={styles.tagline}>{partner.tagline}</p>}
          {partner.website && (
            <a href={partner.website} target="_blank" rel="noopener noreferrer" className={styles.website}>
              <Icon name="globe" size={14} />
              {partner.website.replace(/^https?:\/\//, "")}
            </a>
          )}
        </div>
      </header>

      {partner.bio && <p className={styles.bio}>{partner.bio}</p>}

      <h2 className={styles.productsHeading}>
        Products by {partner.name} <span className={styles.count}>({products.length})</span>
      </h2>

      {products.length ? (
        <div className={styles.grid}>
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon="search"
          title="No published products yet"
          text="This publisher doesn't have any live products right now."
          actionLabel="Browse all products"
          actionHref="/catalog"
        />
      )}
    </div>
  );
}
