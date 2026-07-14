# BIM Hive Marketplace V2 — Architecture

A greenfield rebuild of the BIM Hive Marketplace: a storefront for Revit/AEC digital tools that
**also runs the licensing backend** already-shipped desktop plugins call to activate and verify
licenses. This document is the durable architecture reference; day-to-day setup lives in
[`README.md`](README.md).

---

## 1. Goals & constraints

- **Better UI/UX + real SEO** — server-rendered storefront with metadata, sitemap, JSON-LD.
- **Clean front/back separation** — Django is a headless API; Next.js owns all rendering.
- **One clean domain model** — exactly one sellable entity, `Product`. No Plugin-vs-Product split.
- **Do not break the field** — the license activation HTTP contract stays byte-compatible so plugins
  already installed on customers' machines keep working.
- **Security from day one** — see §7.
- **Two Railway services only** — Postgres + one combined web service (front + back together).

---

## 2. Repository layout (monorepo)

```
/web      Next.js (App Router, TypeScript, RSC) — storefront, account, admin UI
/api      Django + Django REST Framework — headless API, ORM, licensing, payments, admin actions
/infra    docker-compose (Postgres + MinIO), process manager, deploy config
```

Root holds shared config: `.env` (real, git-ignored), `.env.example` (placeholders), this file,
`README.md`, `CLAUDE.md`, `style.md`, `design/`.

---

## 3. Runtime topology

**Local dev** — three processes:
- Postgres + MinIO via `docker-compose` (`/infra`).
- Django dev server on `:8000` (serves `/api/*`, `/admin/*`).
- Next.js dev server on `:3000`; `next.config` rewrites proxy `/api/*` → `:8000`.

**Production (Railway)** — exactly two services:
1. **Postgres.**
2. **One web service** running both apps in a single container: gunicorn (Django) + `next start`,
   supervised by a lightweight process manager. Next.js is the public entrypoint and proxies
   `/api/*` to Django on localhost. Front + back therefore share one origin → simple cookies, no
   cross-site CORS in prod.

---

## 4. Domain model (single `Product`)

Django apps under `/api`:

| App | Responsibility |
|---|---|
| `catalog` | **`Product`** (the one sellable entity) + `Category`, `Collection`, `Tag`, `Partner`, `ProductMedia`, `KeyFeature`, `ChangelogEntry`, `CompatibilityEntry`, `ProductFile` (multi-variant, keyed by Revit version), `Documentation` + `DocSection`. |
| `licensing` | `MachineLicense`, `LicenseEvent`, and the activation/products API. Points at `catalog.Product` via `product_code`. |
| `orders` | `Order`, `OrderItem`, `Payment`, Stripe + PayPal webhooks. Fulfillment only after confirmed payment. |
| `accounts` | Custom `User`, `Profile`, roles/permissions, addresses, payment methods, sessions. |
| `reviews` | Product ratings & reviews. |
| `support` | Support tickets. |
| `content` | Blog + Knowledge Base. |

**`Product` key fields:** `type` (plugin/script/template/library/service — replaces the old Plugin
model), `product_code` (unique, **immutable once live**), `default_trial_days`, status
(Draft/Pending/Published/Rejected/Hidden), visibility, price, currency, featured, ratings aggregate.

---

## 5. License API compatibility (critical)

Two endpoints installed plugins depend on — kept **byte-identical**:

- `GET /api/license/products` → `[{code, name, revitYear, defaultTrialDays}]`
- `POST /api/license/activate` (CSRF-exempt, **no trailing slash**)
  - request: `{productCode, machineFingerprintHash, trialMinutes?, trialDays?, fingerprintVersion?,
    pluginVersion?, machineData?, licenseKey?, ipAddress?}`
  - response: `{authorized, status, message, startedAt, expiresAt, remainingSeconds}`

Rules preserved exactly:
- Fingerprint hash = `SHA256("<machineFingerprintHash>|<LICENSE_PEPPER>")`, hex, **uppercased**.
- Trial length is **server-authoritative** — clamped to the product's `default_trial_days`.
- Per-IP fixed-window rate limiting, **fail-open** on cache errors.
- Status vocabulary: `paid` / `active` / `expired` / `blocked` / `cancelled` / `rate_limited` /
  `bad_request`.

Compatibility data (product `code` strings, existing `machine_licenses`, `license_events`) lives in
the **legacy installer-generator DB**, not the marketplace DB. A one-time management command imports
it into V2. **V2's `LICENSE_PEPPER` must equal production's** or every field fingerprint mismatches.
Both endpoints are covered by golden-master tests that assert the exact JSON.

---

## 6. Storage & payments

- **Storage:** Cloudflare R2 (S3-compatible) via boto3. Local dev uses MinIO. Downloads are served
  as **short-lived signed URLs** behind an auth + entitlement gate; guessing a direct URL 302s to
  login.
- **Payments:** Card + ACH via Stripe (Payment Element); PayPal via the PayPal SDK. Every rail is
  **webhook-gated** — licenses/downloads are granted only after a confirmed payment webhook.

---

## 7. Security baseline

- `DJANGO_DEBUG=False` by default in prod; enforced in code.
- Secrets only in `.env` (git-ignored); `.env.example` has placeholders. `.gitignore` blocks `.env*`.
- Real payment before fulfillment (no auto-mark-PAID).
- Server-authoritative trials.
- Rate-limited license + auth endpoints; lockout on repeated failed logins.
- HSTS + Secure/httpOnly/SameSite cookies enforced in code in prod.
- Auth = same-origin session cookies (DRF SessionAuth), CSRF on state-changing requests.

---

## 8. Styling & frontend conventions

- **CSS Modules** (`Component.module.css` co-located) over a **design-token** layer
  (`web/styles/tokens.css`): colors, 8-pt spacing scale, type scale, radius scale, motion tokens.
  No Tailwind/Bootstrap, no inline styles.
- WCAG-safe gold usage: darker gold (`#B8945A`) for text/links on white; bright gold for
  fills/icons/underlines; near-black or darker gold for primary buttons.
- Animations via Framer Motion (orchestrated) + CSS transitions (simple), all gated by
  `prefers-reduced-motion: reduce`.
- Light mode only for v1.
