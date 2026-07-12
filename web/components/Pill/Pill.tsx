import type { ReactNode } from "react";

import styles from "./Pill.module.css";

type Tone = "neutral" | "success" | "warning" | "error" | "gold";

export function Pill({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return <span className={`${styles.pill} ${styles[tone]}`}>{children}</span>;
}
