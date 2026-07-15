import Link from "next/link";

import { Icon } from "@/components/Icon/Icon";
import { ResourcesPanel } from "@/components/Header/ResourcesPanel";
import { SolutionsPanel } from "@/components/Header/SolutionsPanel";
import { Logo } from "@/components/Logo/Logo";
import { MegaMenu } from "@/components/MegaMenu/MegaMenu";
import { NAV_LINKS } from "@/config/site";
import { AuthNav } from "@/features/auth/AuthNav/AuthNav";
import { CartLink } from "@/features/cart/CartLink/CartLink";

import styles from "./Header.module.css";

export function Header() {
  return (
    <header className={styles.header}>
      <div className={`container ${styles.inner}`}>
        <Logo />

        <form className={styles.search} role="search" action="/catalog">
          <Icon name="search" size={18} className={styles.searchIcon} />
          <input
            name="q"
            className={styles.searchInput}
            placeholder="Search for plugins, tools, and automation..."
            aria-label="Search"
          />
        </form>

        <nav className={styles.nav} aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <Link key={link.label} href={link.href} className={styles.navLink}>
              {link.label}
            </Link>
          ))}
          <MegaMenu label="Solutions">
            <SolutionsPanel />
          </MegaMenu>
          <MegaMenu label="Resources">
            <ResourcesPanel />
          </MegaMenu>
        </nav>

        <div className={styles.actions}>
          <CartLink />
          <AuthNav />
        </div>
      </div>
    </header>
  );
}
