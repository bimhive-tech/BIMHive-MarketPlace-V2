# Rebuild the BIM Hive Marketplace — greenfield, local-first

You are starting a brand-new webapp: a from-scratch rebuild of the **BIM Hive Marketplace**,
a storefront for Revit/AEC digital tools that also runs the licensing backend those desktop
plugins depend on. This is a NEW repo and a NEW app. We are NOT touching production.

**Attached to this session:** the new UI mockups (homepage, product detail, checkout, admin
add-product), the logo, the hero background image, and `style.md` (the written design system).
Treat `style.md` + the mockups as the design source of truth.

## Start in PLAN MODE. Do not write code until we agree on a plan.
First explore, then produce an architecture + migration plan, confirm the open decisions at the
bottom with me, and only then scaffold.

## Why we're rebuilding
The current marketplace is a Django monolith with server-rendered templates (repo at
`E:\Eng. Ahmed Tamer\bim_hive_marketplace`, deployed on Railway with Postgres + Cloudflare R2,
live at hub.bim-hive.com). It works but we want: much better UI/UX, real SEO, a clean
frontend/backend separation, a cleaner domain model, and all the security hardening baked in
from day one. Study that existing repo for **feature parity** and — most importantly — the
**license API contract** (see Hard Constraints).

## Domain model — ONE "Product" concept (do this from the start)
In v1 there were two overlapping ideas, **"Plugin"** and **"Product"**, that were effectively
the same thing. This caused duplicated fields, duplicated logic, and confusion. In the rebuild
there is exactly **ONE** first-class sellable entity: **Product**.
- A Product may be a Revit plugin, a Dynamo script, a template, a BIM library, a service, etc.
  — differentiated by a `type`/category field, NOT by a separate model.
- Everything hangs off Product: media, pricing, license/product-code, files/downloads,
  documentation, reviews, changelog, compatibility, tags, partner/seller.
- Do NOT create a parallel "Plugin" model or `/plugins/...` routes. Storefront routes are
  `/products/...`.
- When migrating v1 data, **collapse Plugin + Product into the single Product table.**

## Target stack
- **Frontend:** Next.js (App Router, TypeScript, React Server Components) for SSR/SSG SEO.
  Tailwind for styling. Server-rendered product pages with metadata, sitemap, and JSON-LD
  product structured data.
- **Backend:** Django + Django REST Framework as a **headless API** (no server-rendered
  storefront). Keep Django for the ORM, admin, and the licensing logic.
- **DB:** Postgres. **Storage:** Cloudflare R2 (S3-compatible). **Payments:** Stripe.
- Recommend a **monorepo** (`/web` Next.js, `/api` Django) with `docker-compose` for local
  Postgres + MinIO (R2-compatible) so nothing local ever needs the real cloud.

## Hard constraints (do not violate)
1. **Local only, new repo.** Never modify, deploy to, or connect to production. Do NOT use the
   production `DATABASE_URL`, R2 keys, or Railway. Use local Postgres + MinIO and Stripe test
   keys. `.env.example` has **placeholders only** — never commit real secrets.
2. **Preserve the license activation API contract.** Revit plugins already installed on users'
   machines call the marketplace to activate/verify licenses. Breaking this bricks them. Before
   rebuilding, read the existing licensing code (`licensing/api_views.py`, `licensing/services.py`,
   and the Postgres `activate_or_check_online_trial(...)` function) and **document the exact
   contract**: `POST /api/license/activate`, `GET /api/license/products`, request/response JSON,
   product codes, and the `LICENSE_PEPPER`-based fingerprint hashing. Reimplement it
   byte-for-byte compatibly (or lift the licensing app over unchanged). The desktop loader and
   installer generator live in other repos — you don't touch them, you just stay compatible.

## Bake in these security lessons from day one (all were real issues in v1)
- `DEBUG=False` by default; DEBUG never leaks in prod.
- No secrets in the repo or git history — ever. `.env` only, placeholders in `.env.example`.
- **Real payment before fulfillment.** Downloads/licenses are granted ONLY after a Stripe
  webhook confirms payment. No "auto-mark-PAID". (v1 gave paid products away for free.)
- **Server-authoritative trials.** Trial length comes from product config, never trusted from
  the client. (v1 trusted client-sent trial days.)
- Rate-limit the license and auth endpoints; lockout on repeated failed logins.
- HSTS + secure cookies enforced in prod in code (not just env vars).
- Downloads served via **short-lived signed R2 URLs**; the download endpoint is auth- and
  entitlement-gated (guessing a direct URL must 302 to login).
- Consider **RSA-signing the license activation response** server-side (private key server-only,
  public key embedded in the loader) so a patched loader can't self-authorize. Flag in the plan.
- Installers need Authenticode code-signing (SSL.com OV was the chosen path) — note it, out of
  scope for the web build.

## Feature parity (everything is a Product)
- Catalog: products, categories, collections, search, featured & popular sections.
- Product detail: tabs for Overview, Features, Reviews, Compatibility, Documentation, Support;
  media gallery; changelog ("What's New"); publisher/partner card; tags; ratings.
- **Documentation system** (per-product docs: summary, overview, how-to-use steps, screenshots,
  release history — already exists in v1 and is populated; migrate it).
- Licensing: online trials + the activation API above; per-product trial config.
- Checkout & payments: cart, Stripe checkout, order summary, receipts, 30-day-guarantee copy,
  license tiers (single user / team seats).
- Auth: signup/login, user roles, seller and admin dashboards.
- Blog + Knowledge Base.

## Admin requirements (design these in — v1 pain points)
- **Product Code** is a first-class field on the "Pricing & License" tab, shown prominently and
  **immutable once the product has gone live**, with a warning that changing it breaks activation
  for every installed copy in the field. (v1 had a product-code mismatch bug.)
- **Files & Downloads must be multi-variant** — files keyed by Revit version (e.g. 2024 + 2025),
  and the download endpoint serves the right one. A single upload slot is not enough for the
  real catalog.
- Add a **Licenses** section to the admin (currently missing): look up / extend / revoke /
  re-issue a license, and see its fingerprint + trial state. (In v1 this was only possible by
  hand-editing the DB.)
- The **Documentation editor** pre-fills the doc `summary` from the product's short description
  and clearly labels them as distinct, so the "placeholder summary" bug from v1 can't recur.
- Keep the good v1-mockup admin patterns: Draft/Public/Hidden, Submit-for-Review + admin
  approval, Partners/sellers, Roles & Permissions, repeatable Key Features.

## Design direction
Follow `style.md` and the attached mockups exactly. Build a small **design-token set first**
(colors as CSS variables, an 8-pt spacing scale, a type scale with weights/line-heights, radius
scale) so the whole site reads as one system. Note: verify the gold's contrast — muted gold on
white for link/price **text** and white text on a gold **button** likely fail WCAG AA; use a
darker gold for text-on-white and near-black-or-darker-gold for the primary button, keeping the
bright gold for fills/icons/underlines. Decide light-only vs dark mode up front.

## First-session deliverables
1. A short `ARCHITECTURE.md` plan + the confirmed decisions below.
2. Monorepo scaffold + `docker-compose` (Postgres + MinIO) running locally.
3. Django API up with the licensing contract documented and stubbed/ported.
4. Next.js frontend running with design tokens, the homepage, and ONE product detail page wired
   to the API. Verify it renders locally before expanding.

## Open decisions — confirm with me during planning
- Monorepo vs two separate repos? (I recommend monorepo.)
- Data: migrate v1 Postgres content (products, docs, users, licenses) into the new schema, or
  start fresh with a seed script? (I lean toward migrating products + docs, fresh for the rest.)
- Payments: Stripe only to start, or Stripe + PayPal + ACH as the mockup shows?
- Auth: keep Django sessions behind the API, or move to token/JWT for the Next.js client?
- Licensing app: lift over unchanged (safest for compatibility) or reimplement?
