import type { ReactNode } from "react";

import { Logo } from "@/components/Logo/Logo";
import { WireframeThumb } from "@/components/WireframeThumb/WireframeThumb";

import styles from "./AuthShell.module.css";

interface AuthShellProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <div className={styles.wrap}>
      <div className={styles.formSide}>
        <div className={styles.card}>
          <div className={styles.brand}>
            <Logo />
          </div>
          <h1 className={styles.title}>{title}</h1>
          <p className={styles.subtitle}>{subtitle}</p>
          {children}
          <p className={styles.footer}>{footer}</p>
        </div>
      </div>
      <aside className={styles.artSide} aria-hidden="true">
        <WireframeThumb seed="auth" />
        <div className={styles.artCopy}>
          <p className={styles.artTitle}>Digital tools for smarter construction.</p>
          <p className={styles.artText}>
            Join thousands of AEC professionals building better, faster.
          </p>
        </div>
      </aside>
    </div>
  );
}
