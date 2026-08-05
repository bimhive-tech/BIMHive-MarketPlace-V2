"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { PromoBar } from "@/features/promotions/PromoBar/PromoBar";

/**
 * Wraps pages with the storefront promo bar, header and footer, except on the
 * admin and partner portals, which have their own full-screen chrome. Keeps
 * Header/Footer as server components (passed in as props) while letting us
 * branch on path.
 */
export function SiteChrome({
  header,
  footer,
  children,
}: {
  header: ReactNode;
  footer: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const bare = pathname?.startsWith("/admin-portal") || pathname?.startsWith("/partner-portal");

  if (bare) return <>{children}</>;

  return (
    <>
      {/* Above the sticky header, so it scrolls away once read rather than
          permanently eating vertical space. */}
      <PromoBar />
      {header}
      <main>{children}</main>
      {footer}
    </>
  );
}
