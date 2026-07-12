# BIMHIVE — Design & UI/UX Style Guide

This document describes the visual language and interface patterns used across BIMHIVE — a marketplace for AEC/BIM digital tools. It covers the customer-facing storefront (home, product detail, checkout) and the internal admin dashboard (product management, forms). This is a **design reference**, not a code spec — it describes what things look like and where they live, so any implementation stays visually consistent.

---

## 1. Brand Personality

- **Feel:** professional, trustworthy, technical-but-approachable. Sits between "enterprise SaaS" and "creative marketplace."
- **Metaphor:** the brand mark is a 3D gold hexagonal "B" monogram, echoed in the homepage hero as a large architectural wireframe illustration (thin gray isometric building lines) with the gold mark floating over it. This wireframe/blueprint motif is the primary decorative device — use sparingly, only in hero/marketing moments, never as background noise behind functional UI.
- **Two distinct "modes" of the product share one visual language but different densities:**
  - **Storefront** — spacious, marketing-forward, generous whitespace, imagery-led.
  - **Admin dashboard** — dense, data-forward, table/card-driven, utilitarian.

---

## 2. Color Palette

### Brand / Primary
| Swatch | Approx. Hex | Usage |
|---|---|---|
| Gold / Bronze (primary) | `#C0A065` (mid), `#B8945A` (text/darker), `#C7AC80` (light) | Primary buttons, active tab underlines, links, prices, star ratings, selected-radio fill, icon accents |
| Cream / Sand tint | `#F7F1E9` – `#F9FAF9` | Selected sidebar row background, callout/notice boxes, subtle highlight backgrounds |

The gold is muted and slightly warm/brass — **not** a bright yellow-gold. It reads as premium/architectural rather than playful. It is used deliberately and sparingly: one primary action per view, never as a large fill background.

### Neutrals
| Swatch | Approx. Hex | Usage |
|---|---|---|
| Black / near-black | `#000000`–`#1A1A1A` | Headlines, primary headings, key numbers |
| Body gray | `#4A4A4A`–`#5A5A5A` | Body copy, descriptions |
| Muted gray | `#8D8F93` | Secondary/supporting text, subtitles, metadata, timestamps |
| Border/divider gray | `#E5E5E5`–`#ECECEC` | Card borders, table rows, input borders, section dividers |
| Off-white surface | `#F9FAFB` | App shell backgrounds (admin sidebar, page canvas behind cards) |
| Pure white | `#FFFFFF` | Card/panel surfaces, content backgrounds |

### Semantic / Status Colors
Used exclusively for status pills, badges, and inline confirmations — always as a **light tint background + saturated text of the same hue**, never a solid saturated fill:

| Status | Background | Text |
|---|---|---|
| Success / Published | `#E1F1E2` | `#3F7A4E` (green) |
| Warning / Pending | `#FEF1DC` | `#D57F42` (amber/orange) |
| Error / Rejected | `#FDE8E6` | `#C54B4F` (red) |
| Neutral / Draft | `#F0F0F0` | `#6B6B6B` (gray) — sometimes just plain text, no pill |

---

## 3. Typography

- **Typeface:** a clean, modern geometric/grotesque sans-serif (visually similar to Inter, Söhne, or Public Sans) used for everything — no serif, no display font.
- **Hierarchy:**
  - **Hero headline:** very large, bold, black, tight line-height, two-line wrap with one accent word in brand gold (e.g., "Digital tools for **smarter** construction.")
  - **Page/section titles:** large, bold, black (e.g., "Featured Products," "Products," "Checkout")
  - **Card/product titles:** medium, bold, black
  - **Body copy:** regular weight, medium gray, comfortable line-height
  - **Meta/support text:** small, muted gray (ratings counts, timestamps, helper text under labels)
  - **Eyebrow/section labels (admin sidebar):** extra-small, uppercase, letter-spaced, gray (e.g., "OVERVIEW," "PRODUCTS & CONTENT," "SETTINGS")
- **Numerals:** prices and stat-card numbers are large and bold, given visual priority over their labels.
- **Links:** brand gold, no underline by default; often paired with a small trailing arrow (e.g., "View all products →").

---

## 4. Layout Patterns

### Storefront shell
- Fixed top navigation bar (see §5) on every page.
- Content area uses a **left sidebar + main content** split on the homepage (category list + featured grid) but narrows to a **breadcrumb + centered content** layout on product/checkout pages.
- Generous outer margins and section spacing (~40–60px between major sections).
- Hero sections combine text (left) + illustration (right) in a 50/50 split.

### Admin dashboard shell
- Persistent **left sidebar** (fixed width, ~210px) with grouped, labeled navigation sections.
- **Top bar** above content: global search (with keyboard-shortcut hint), notifications bell, help icon, user avatar/name/role menu — right-aligned.
- Main content area: page title + subtitle at top-left, primary action button top-right, then horizontal **tab strip**, then a row of **stat/metric cards**, then a **filter/search bar**, then the primary **data table**, then supporting secondary panels (recent activity, top-performers) at the bottom in a 2-column split.
- Detail/edit forms (e.g., Add New Product) use a **two-column layout**: wide left column for the form fields organized under tabs, narrower right column as a persistent "settings rail" (Publishing status, visibility, product type, additional toggles) — this rail mirrors the storefront's right-hand purchase box pattern.

### Consistent cross-page structural rule
Any page with a primary object (product, order) puts **the object's core content on the left/center** and **the actions/status/meta on the right**, in a sticky-feeling card. This applies to: product detail (info left, buy-box right), checkout (form left, order summary right), and add-product (form left, publishing settings right).

---

## 5. Navigation

### Storefront top nav
Left-to-right: logo + wordmark → search bar (pill-shaped, gray fill, icon right) → text nav links with dropdown chevrons (Categories, Solutions, Resources) → cart icon (with item-count badge) → "Log in" (plain text) → "Sign up" (solid gold button, top-right corner, highest visual priority in the bar).

### Admin sidebar
Grouped into labeled sections (OVERVIEW / PRODUCTS & CONTENT / SUPPORT / SETTINGS) separated by vertical whitespace, no dividing lines. Each item = icon + label. The active item gets: gold icon/text color, a soft cream background pill, and (implied) a left accent edge. Inactive items are plain gray icon + dark text. Items with pending counts show a small numeral to the right (e.g., "Support Tickets 12").

### Breadcrumbs
Small, gray, chevron-separated, with the current page in gold/bold (e.g., `Home > Revit Plugins > BIM OneClick`, or `Cart > Checkout > Confirmation`). Used on product, checkout, and admin sub-pages — not on the homepage or top-level admin list pages.

---

## 6. Core Components

**Buttons**
- Primary: solid gold fill, white text, medium-rounded corners (~8px), used once per view for the single most important action ("Sign up," "Add to Cart," "Pay $—," "Submit for Review").
- Secondary: white fill, gold border + gold text ("Browse Solutions," "Buy Now," "Save as Draft").
- Tertiary/text: no border/fill, gold text only, often with an icon (cart glyph, arrow).

**Cards**
- White surface, thin light-gray border, small corner radius (~8–12px), no heavy shadow — flat and clean rather than skeuomorphic.
- Product cards: image on top (square/landscape), title, short description, price (bold, larger), star rating + review count, small circular gold-outline cart-add button bottom-right.

**Status pills / badges**
- Small, fully-rounded (pill) shape, tinted background per §2 semantic table, bold small-caps-weight text. Used in tables (order/product status) and on tags (e.g., "Productivity," "Automation").

**Tabs**
- Flat text row, generous horizontal spacing, active tab marked by a gold underline + gold (or bold black) text; inactive tabs plain gray text, no border.

**Forms**
- Labeled fields, label above input, gray placeholder text, light border input fields with rounded corners, optional live character counters bottom-right of textareas ("0/150").
- Radio/checkbox options for multi-choice settings are rendered as **selectable bordered rows** (not bare radio buttons) — each row has a title + one-line helper description, and the selected row gets a gold border/gold-filled radio dot.
- Repeatable field groups (e.g., "Key Features") show paired inputs with a trash-icon to remove and a dashed/outlined "+ Add" button to append another row.
- Rich text areas include a minimal toolbar (paragraph style, bold/italic/underline, lists, link, image, code) directly above the editable area.

**Tables (admin)**
- Header row in muted gray uppercase-ish labels, plain white row background, thin row dividers, hover-friendly row height with a small thumbnail + title/subtitle combo in the first column, status pill column, and a trailing actions column (edit pencil icon + overflow "…" menu).
- Pagination sits bottom-left as a result-count string ("Showing 1 to 10 of 124 products") and bottom-right as page-number controls with prev/next chevrons.

**Ratings**
- Gold star icons, numeric average shown large/bold when it's the focal element (product page), or small inline next to a star icon in list/card contexts. Rating breakdowns use horizontal gold-filled bars per star level with a percentage.

**Callout / info boxes**
- Soft cream or light tint background, no harsh border, small icon on the left, used for reassurance/guarantee messages ("30-Day Money Back Guarantee," "Products require admin approval before going live").

---

## 7. Iconography

- Consistent **outline/line-style icon set** throughout (not filled/glyph icons) — thin stroke weight, matches the light, technical feel of the brand.
- Icons are always paired with text, rarely standalone except for universal actions (cart, search, notification bell, edit pencil).
- Category and feature icons are simple line pictograms relevant to their label (a broom for "Model Cleanup," an eye for "View Management," a document for "Documentation").

---

## 8. Spacing, Radius & Elevation

- **Corner radius:** small-to-medium throughout (roughly 6–12px) — buttons, cards, inputs, pills all share a consistent soft-rounded language; pills/badges are fully rounded.
- **Elevation:** almost flat design — borders do more work than shadows. Shadows, where present, are very soft and only used to lift primary action panels (e.g., the checkout payment box) slightly off the page.
- **Density:** storefront pages breathe (large gaps between sections); admin screens are compact and data-dense (tight row heights, small gaps) to maximize information per screen.

---

## 9. Imagery & Illustration Style

- Product thumbnails: clean line-art/wireframe renders of building models and UI screenshots — monochrome/grayscale line drawings rather than photography, keeping the whole marketplace visually cohesive regardless of who the third-party seller is.
- Hero/marketing imagery: abstract architectural wireframes (isometric building outlines) in light gray, with the gold hexagon brand mark as the single point of color — this "line art + one gold accent" combination is the signature visual trick of the brand and can be reused for other marketing moments (empty states, onboarding, email headers).

---

## 10. Interaction & State Conventions

- **Selected/active state** (nav item, sidebar category, radio card, tab): gold accent applied to text/icon/border/underline + a soft cream background where relevant. This is the single consistent "you are here / this is chosen" signal across the whole product.
- **Primary emphasis per screen:** exactly one solid-gold button per view; everything else competing for attention is downgraded to an outline or text link.
- **Trust reinforcement:** security/guarantee micro-copy (lock icons, "Secure Checkout," "30-Day Money Back Guarantee," "Verified" partner badges) appears near every commitment point (add-to-cart, pay button, seller listing) — this is a deliberate, repeated pattern, not incidental copy.
