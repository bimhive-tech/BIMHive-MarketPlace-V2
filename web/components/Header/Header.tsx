import Link from "next/link";

import { Button } from "@/components/Button/Button";
import { Icon } from "@/components/Icon/Icon";
import { Logo } from "@/components/Logo/Logo";
import { NAV_LINKS } from "@/config/site";

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
              <Icon name="chevron-down" size={16} />
            </Link>
          ))}
        </nav>

        <div className={styles.actions}>
          <Link href="/cart" className={styles.cart} aria-label="Cart">
            <Icon name="cart" size={22} />
          </Link>
          <Link href="/login" className={styles.login}>
            Log in
          </Link>
          <Button href="/signup" size="md">
            Sign up
          </Button>
        </div>
      </div>
    </header>
  );
}
