import Image from "next/image";
import Link from "next/link";

import { SITE } from "@/config/site";

import styles from "./Logo.module.css";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className={styles.logo} aria-label={`${SITE.name} home`}>
      <Image src="/brand/logo.png" alt="" width={40} height={40} className={styles.mark} priority />
      <span className={styles.word}>{SITE.name}</span>
    </Link>
  );
}
