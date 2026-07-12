import { Icon } from "@/components/Icon/Icon";
import { Pill } from "@/components/Pill/Pill";
import type { ProductDetail } from "@/lib/types";

import styles from "./PublisherCard.module.css";

function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function PublisherCard({ product }: { product: ProductDetail }) {
  const partner = product.partner;
  return (
    <div className={styles.card}>
      <div className={styles.publisher}>
        <span className={styles.avatar}>
          <Icon name="library" size={22} />
        </span>
        <div>
          <p className={styles.pubLabel}>Published by</p>
          <p className={styles.pubName}>
            {partner?.name ?? "BIMHIVE"}
            {partner?.is_verified && <Icon name="check-circle" size={16} className={styles.verified} />}
          </p>
          <p className={styles.pubTagline}>{partner?.tagline ?? "Trusted developer"}</p>
        </div>
      </div>

      <dl className={styles.meta}>
        <div className={styles.row}>
          <dt>Version</dt>
          <dd>{product.version}</dd>
        </div>
        <div className={styles.row}>
          <dt>Released</dt>
          <dd>{formatDate(product.released_at)}</dd>
        </div>
        <div className={styles.row}>
          <dt>Category</dt>
          <dd>{product.category.name}</dd>
        </div>
      </dl>

      {product.tags.length > 0 && (
        <div className={styles.tags}>
          {product.tags.map((tag) => (
            <Pill key={tag.id} tone="gold">
              {tag.name}
            </Pill>
          ))}
        </div>
      )}

      <div className={styles.share}>
        <span className={styles.shareLabel}>Share</span>
        <div className={styles.shareIcons}>
          <Icon name="link" size={18} />
          <Icon name="facebook" size={18} />
          <Icon name="linkedin" size={18} />
          <Icon name="twitter" size={18} />
        </div>
      </div>
    </div>
  );
}
