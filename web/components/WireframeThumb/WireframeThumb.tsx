/**
 * Brand signature visual: a light architectural wireframe with a single gold hex
 * accent (style.md §9 "line art + one gold accent"). This is the intentional
 * on-brand preview shown until a seller uploads real product artwork to R2 — not a
 * greyed-out placeholder. Pure SVG, deterministic per product so scenes vary.
 */
import styles from "./WireframeThumb.module.css";

interface WireframeThumbProps {
  seed?: string;
  label?: string;
  className?: string;
}

function hash(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) & 0xffff;
  return h;
}

export function WireframeThumb({ seed = "bimhive", label, className }: WireframeThumbProps) {
  const h = hash(seed);
  const variant = h % 3;

  return (
    <div className={`${styles.wrap} ${className ?? ""}`} role="img" aria-label={label || "Product preview"}>
      <svg viewBox="0 0 400 300" className={styles.svg} preserveAspectRatio="xMidYMid slice">
        {/* isometric ground grid */}
        <g className={styles.grid}>
          {Array.from({ length: 7 }).map((_, i) => (
            <line key={`a${i}`} x1={-40 + i * 80} y1={300} x2={120 + i * 80} y2={40} />
          ))}
          {Array.from({ length: 7 }).map((_, i) => (
            <line key={`b${i}`} x1={440 + i * -80} y1={300} x2={280 + i * -80} y2={40} />
          ))}
        </g>

        {/* extruded building cluster (varies per product) */}
        <g className={styles.build} transform={`translate(${20 + variant * 12} 0)`}>
          <path d="M120 210 V120 L180 92 V182 Z" />
          <path d="M180 182 V92 L244 122 V212 Z" />
          <path d="M120 120 L180 92 L244 122 L184 150 Z" />
          <path d="M244 212 V150 L292 130 V192 Z" />
          <path d="M244 150 L292 130 L292 130" />
          <path d="M96 224 V168 L120 158 V214 Z" />
        </g>

        {/* single gold hex accent (echoes the brand monogram) */}
        <g className={styles.hex} transform="translate(296 78)">
          <path d="M0 0 l30 17 v34 l-30 17 -30 -17 v-34 z" />
          <path d="M0 0 v68 M-30 17 l30 17 30 -17" className={styles.hexInner} />
        </g>
      </svg>
    </div>
  );
}
