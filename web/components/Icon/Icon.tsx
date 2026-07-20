/**
 * Line-style icon set (thin stroke, matches the brand's technical feel — style.md §7).
 * Add new glyphs to PATHS; everything is a single-color stroke that inherits currentColor.
 */
import styles from "./Icon.module.css";

export type IconName =
  | "search" | "cart" | "chevron-down" | "chevron-right" | "chevron-left"
  | "star" | "users" | "award" | "shield" | "download" | "arrow-right"
  | "check" | "check-circle" | "lock" | "link" | "play" | "bell" | "help"
  | "grid" | "puzzle" | "bolt" | "workflow" | "library" | "template"
  | "graduation-cap" | "plug" | "wrench" | "broom" | "eye" | "document"
  | "database" | "chart" | "share" | "hash" | "layers" | "refresh"
  | "windows" | "globe" | "revit" | "facebook" | "linkedin" | "twitter"
  | "logout" | "trash" | "camera" | "plus" | "edit" | "more-horizontal" | "filter" | "x"
  | "upload" | "video" | "image" | "grip-vertical" | "wallet" | "copy" | "clock";

/** Each entry is the inner markup of a 24x24 viewBox, stroked. */
const PATHS: Record<IconName, string> = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  cart: '<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2 3h3l2.4 12.2a1.5 1.5 0 0 0 1.5 1.2h8.2a1.5 1.5 0 0 0 1.5-1.2L22 7H6"/>',
  "chevron-down": '<path d="m6 9 6 6 6-6"/>',
  "chevron-right": '<path d="m9 6 6 6-6 6"/>',
  "chevron-left": '<path d="m15 6-6 6 6 6"/>',
  star: '<path d="m12 3 2.6 5.6 6 .8-4.4 4.2 1.1 6L12 17l-5.3 2.6 1.1-6L3.4 9.4l6-.8z"/>',
  users: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 5.5a3.2 3.2 0 0 1 0 6.3M21 20a6 6 0 0 0-4-5.7"/>',
  award: '<circle cx="12" cy="9" r="5"/><path d="m8.5 13.5-1.5 6 5-2.5 5 2.5-1.5-6"/>',
  shield: '<path d="M12 3 5 6v5c0 4.5 3 8 7 9 4-1 7-4.5 7-9V6z"/><path d="m9.5 12 1.8 1.8 3.5-3.6"/>',
  download: '<path d="M12 3v11m0 0 4-4m-4 4-4-4"/><path d="M5 20h14"/>',
  "arrow-right": '<path d="M4 12h15m0 0-5-5m5 5-5 5"/>',
  check: '<path d="m5 12 4.5 4.5L19 7"/>',
  "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.3 2.3 4.7-4.8"/>',
  lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  link: '<path d="M10 13a4 4 0 0 0 6 .5l2-2a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 11a4 4 0 0 0-6-.5l-2 2A4 4 0 0 0 11.7 18l1-1"/>',
  play: '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7l6-3.5z"/>',
  bell: '<path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6"/><path d="M10 20a2 2 0 0 0 4 0"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.8.4-1 .9-1 1.7"/><path d="M12 17h.01"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  puzzle: '<path d="M10 4h4v3a2 2 0 1 0 4 0h2v4h-3a2 2 0 1 0 0 4h3v4h-4v-3a2 2 0 1 0-4 0v3H6v-4h3a2 2 0 1 0 0-4H6V7h4z"/>',
  bolt: '<path d="M13 3 5 13h6l-2 8 8-10h-6z"/>',
  workflow: '<rect x="3" y="4" width="6" height="5" rx="1.5"/><rect x="15" y="15" width="6" height="5" rx="1.5"/><path d="M6 9v4a3 3 0 0 0 3 3h6"/>',
  library: '<path d="M5 4h3v16H5zM10 4h3v16h-3z"/><path d="m16 5 3 .8-3.2 14-3-.8z"/>',
  template: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 9h16M9 9v11"/>',
  "graduation-cap": '<path d="M12 5 3 9l9 4 9-4z"/><path d="M7 11v4c0 1.5 2.5 2.5 5 2.5s5-1 5-2.5v-4"/>',
  plug: '<path d="M9 3v5M15 3v5"/><path d="M7 8h10v3a5 5 0 0 1-10 0z"/><path d="M12 16v5"/>',
  wrench: '<path d="M15 6a4 4 0 0 0-5 5L4 17l3 3 6-6a4 4 0 0 0 5-5l-2.5 2.5L14 9l1.5-3z"/>',
  broom: '<path d="m14 4-6 6 3 3 6-6z"/><path d="m8 10-4 4 1 5 5 1 4-4"/>',
  eye: '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="2.5"/>',
  document: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
  database: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.7 3 3 7 3s7-1.3 7-3V6"/><path d="M5 12c0 1.7 3 3 7 3s7-1.3 7-3"/>',
  chart: '<path d="M4 4v16h16"/><path d="m8 14 3-3 3 2 4-5"/>',
  share: '<circle cx="6" cy="12" r="2.2"/><circle cx="18" cy="6" r="2.2"/><circle cx="18" cy="18" r="2.2"/><path d="m8 11 8-4M8 13l8 4"/>',
  hash: '<path d="M6 9h14M4 15h14M10 4 8 20M16 4l-2 16"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
  refresh: '<path d="M4 12a8 8 0 0 1 13.5-5.8L20 8"/><path d="M20 4v4h-4"/><path d="M20 12a8 8 0 0 1-13.5 5.8L4 16"/><path d="M4 20v-4h4"/>',
  windows: '<path d="M3 5.5 10.5 4v7H3zM12 3.7 21 2v9h-9zM3 13h7.5v7L3 18.5zM12 13h9v9l-9-1.7z"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18"/>',
  revit: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 16V9h4a2.5 2.5 0 0 1 0 5H9m4 0 3 3"/>',
  facebook: '<path d="M14 8h2V5h-2a3 3 0 0 0-3 3v2H9v3h2v6h3v-6h2l1-3h-3V8.5A.5.5 0 0 1 14 8z"/>',
  linkedin: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 11v6M8 8v.01M12 17v-4a2 2 0 0 1 4 0v4"/>',
  twitter: '<path d="M21 6.5c-.7.3-1.4.5-2.2.6a3.8 3.8 0 0 0 1.7-2.1c-.8.5-1.6.8-2.5 1a3.8 3.8 0 0 0-6.5 3.5A10.8 10.8 0 0 1 4 5.3a3.8 3.8 0 0 0 1.2 5.1c-.6 0-1.2-.2-1.7-.5a3.8 3.8 0 0 0 3 3.8c-.5.1-1 .2-1.6.1a3.8 3.8 0 0 0 3.6 2.6A7.6 7.6 0 0 1 3 18.5 10.7 10.7 0 0 0 20 9.5c.8-.6 1.4-1.3 1.9-2z"/>',
  logout: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 8l-4 4 4 4"/><path d="M6 12h12"/>',
  trash: '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/><path d="M10 11v6M14 11v6"/>',
  camera: '<path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  edit: '<path d="M4 20h4l11-11a2 2 0 0 0 0-3l-1-1a2 2 0 0 0-3 0L4 16z"/><path d="M13.5 6.5 17.5 10.5"/>',
  "more-horizontal": '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>',
  filter: '<path d="M4 6h16M7 12h10M10 18h4"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  upload: '<path d="M12 21V10m0 0-4 4m4-4 4 4"/><path d="M5 4h14"/>',
  video: '<rect x="3" y="6" width="12" height="12" rx="2"/><path d="m15 10 6-3v10l-6-3z"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="m4 17 5-5 4 4 3-3 4 4"/>',
  "grip-vertical": '<circle cx="9" cy="6" r="1.3"/><circle cx="15" cy="6" r="1.3"/><circle cx="9" cy="12" r="1.3"/><circle cx="15" cy="12" r="1.3"/><circle cx="9" cy="18" r="1.3"/><circle cx="15" cy="18" r="1.3"/>',
  wallet: '<path d="M4 7a2 2 0 0 1 2-2h11a1 1 0 0 1 0 2H6a1 1 0 0 0 0 2h13a1 1 0 0 1 1 1v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><circle cx="16.5" cy="14" r="1.3"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
};

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  strokeWidth?: number;
  filled?: boolean;
}

export function Icon({ name, size = 20, className, strokeWidth = 1.6, filled = false }: IconProps) {
  return (
    <svg
      className={`${styles.icon} ${className ?? ""}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: PATHS[name] ?? "" }}
    />
  );
}
