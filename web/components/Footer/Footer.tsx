import Link from "next/link";

import { Logo } from "@/components/Logo/Logo";
import { SITE } from "@/config/site";

import styles from "./Footer.module.css";

const COLUMNS = [
  {
    heading: "Marketplace",
    links: [
      { label: "All Products", href: "/catalog" },
      { label: "Collections", href: "/collections" },
      { label: "Become a Seller", href: "/sell" },
    ],
  },
  {
    heading: "Resources",
    links: [
      { label: "Documentation", href: "/docs" },
      { label: "Knowledge Base", href: "/knowledge" },
      { label: "Blog", href: "/blog" },
    ],
  },
  {
    heading: "Company",
    links: [
      { label: "About", href: "/about" },
      { label: "Contact", href: "/contact" },
      { label: "FAQ", href: "/faq" },
    ],
  },
  {
    heading: "Legal",
    links: [
      { label: "Terms of Service", href: "/terms" },
      { label: "Privacy Policy", href: "/privacy" },
      { label: "Refund Policy", href: "/refunds" },
    ],
  },
];

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.inner}`}>
        <div className={styles.brand}>
          <Logo />
          <p className={styles.tagline}>{SITE.description}</p>
        </div>

        <div className={styles.columns}>
          {COLUMNS.map((col) => (
            <nav key={col.heading} className={styles.column} aria-label={col.heading}>
              <h4 className={styles.heading}>{col.heading}</h4>
              {col.links.map((link) => (
                <Link key={link.label} href={link.href} className={styles.link}>
                  {link.label}
                </Link>
              ))}
            </nav>
          ))}
        </div>
      </div>

      <div className={`container ${styles.bottom}`}>
        <span>
          © {new Date().getFullYear()} {SITE.name}. All rights reserved.
        </span>
      </div>
    </footer>
  );
}
