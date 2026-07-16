import Image from "next/image";

import styles from "./PartnerAvatar.module.css";

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "?";
  return words
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
}

interface PartnerAvatarProps {
  name: string;
  logoUrl?: string;
  size?: number;
  className?: string;
}

/** A partner's logo where one's been uploaded, otherwise a deterministic
 * initials badge (first letter of up to two words in the name) — used
 * anywhere a partner needs a visual identity: the product detail "Published
 * by" card, the partner profile editor, the public partner page. */
export function PartnerAvatar({ name, logoUrl, size = 44, className }: PartnerAvatarProps) {
  if (logoUrl) {
    return (
      <span
        className={`${styles.avatar} ${className ?? ""}`}
        style={{ width: size, height: size }}
      >
        <Image src={logoUrl} alt="" fill sizes={`${size}px`} className={styles.img} />
      </span>
    );
  }
  return (
    <span
      className={`${styles.avatar} ${styles.initials} ${className ?? ""}`}
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}
