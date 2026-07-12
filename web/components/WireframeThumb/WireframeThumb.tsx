/**
 * Brand signature: a light architectural wireframe with a single gold hex accent
 * (style.md §9 "line art + one gold accent"). Used as the on-brand product visual
 * until real artwork is uploaded to R2. Pure SVG — no external assets.
 */
import styles from "./WireframeThumb.module.css";

interface WireframeThumbProps {
  seed?: string;
  label?: string;
  className?: string;
}

/** Small deterministic hash so each product gets a stable, slightly different scene. */
function hash(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) & 0xffff;
  return h;
}

export function WireframeThumb({ seed = "bimhive", label, className }: WireframeThumbProps) {
  const h = hash(seed);
  const rot = (h % 8) - 4; // subtle -4..3deg tilt variation
  const cols = 3 + (h % 3);

  return (
    <div className={`${styles.wrap} ${className ?? ""}`} role="img" aria-label={label || "Product preview"}>
      <svg viewBox="0 0 400 300" className={styles.svg} style={{ ["--rot" as string]: `${rot}deg` }}>
        {/* isometric floor grid */}
        <g className={styles.lines}>
          {Array.from({ length: cols }).map((_, i) => (
            <line key={`v${i}`} x1={60 + i * 70} y1={70} x2={20 + i * 70} y2={250} />
          ))}
          {Array.from({ length: 4 }).map((_, i) => (
            <line key={`h${i}`} x1={30} y1={110 + i * 40} x2={370} y2={90 + i * 40} />
          ))}
          {/* extruded volumes */}
          <path d="M120 200 V120 L180 95 V175 Z" />
          <path d="M180 175 V95 L240 120 V200 Z" />
          <path d="M120 120 L180 95 L240 120 L180 145 Z" />
          <path d="M250 210 V150 L295 132 V192 Z" />
        </g>
        {/* single gold hex accent */}
        <g className={styles.hex}>
          <path d="M300 70 l26 15 v30 l-26 15 -26-15 v-30 z" />
          <path d="M300 70 v60 M274 85 l26 15 26-15" className={styles.hexInner} />
        </g>
      </svg>
    </div>
  );
}
