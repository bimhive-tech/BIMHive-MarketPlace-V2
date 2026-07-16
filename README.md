# BIM Hive Marketplace V2

A marketplace for Revit/AEC digital tools (plugins, Dynamo scripts, templates, BIM libraries,
services) that also runs the **licensing backend** the shipped desktop plugins depend on.

- **Frontend:** Next.js (App Router, TypeScript, RSC) — `/web`
- **Backend:** Django + Django REST Framework (headless API) — `/api`
- **Database:** PostgreSQL · **Storage:** Cloudflare R2 (MinIO locally) · **Payments:** Stripe + PayPal
- **Styling:** CSS Modules + design tokens (no Tailwind/Bootstrap)

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design, [`CLAUDE.md`](CLAUDE.md) for project
rules, and [`style.md`](style.md) + [`design/`](design/) for the design system.

---

## Prerequisites

- Node.js 22+ and npm 10+
- Python 3.13 (backend) — 3.14 is not yet supported by the Django/psycopg wheels
- Docker (for local Postgres + MinIO)

---

## Quick start (local dev)

```bash
# 1. Secrets — copy the template and fill in real values
cp .env.example .env

# 2. Local infra: Postgres + MinIO
docker compose -f infra/docker-compose.yml up -d

# 3. Backend (/api)
cd api
py -3.13 -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_marketplace   # realistic sample catalog
python manage.py runserver 8000

# 4. Frontend (/web) — in a second terminal
cd web
npm install
npm run dev                      # http://localhost:3000
```

The Next.js dev server proxies `/api/*` to Django on `:8000`, so the app runs on a single origin at
`http://localhost:3000`.

---

## Environment variables

All config comes from `.env` (see [`.env.example`](.env.example) for the full annotated list). Key
groups: Django core, `DATABASE_URL`, Cloudflare R2, licensing (`LICENSE_PEPPER`), and payments
(Stripe/PayPal). **Never commit `.env`.**

---

## Project structure

```
/web      Next.js frontend (routes, components, features, styles/tokens, lib/api)
/api      Django backend (catalog, licensing, accounts, reviews)
/infra    docker-compose (Postgres + MinIO), deploy config
design/   brand assets + UI mockups (design source of truth)
```

## Routes (built so far)

**Storefront**: `/` (home), `/catalog` (browse + category filter), `/products/<slug>` (detail).
**Cart**: `/cart` (real, localStorage-backed), `/checkout` (honest "coming soon" stub — no fake
payment flow until Stripe/PayPal are wired).
**Auth**: `/login`, `/signup` (session cookies, CSRF-protected).
**Account** (auth-gated, shared sidebar shell): `/account` (overview), `/account/licenses`,
`/account/orders`, `/account/downloads`, `/account/profile` (full profile editor: name/company/
job title/bio, change email, change password, delete account, plus a "Become a Seller"/"Partner"
tab whose label and content track the account's seller-application state).
**Become a seller**: `/sell` (marketing landing page — its sidebar promo on the homepage hides
itself once the visitor already has a seller application), `/sell/apply` (auth-gated application
form — company name + logo upload). Submitting creates a `Partner` in "pending" status linked to
the user's account; BIMHive staff approve or reject it from the admin Partners page.
**Partner portal** (auth-gated to users with a linked `Partner`, own full-screen chrome — no
storefront header/footer): `/partner-portal` (dashboard: product + revenue stats, recent sales),
`/partner-portal/products` (list/create/edit — scoped to the caller's own partner even for a
staff+partner account, and partners can only save draft or submit for review, never self-publish),
`/partner-portal/sales` (read-only order history for their own products, no customer PII),
`/partner-portal/profile` (edit company tagline/bio/website + logo — a real image upload with
removal, not a URL field; no logo falls back to an initials avatar everywhere the partner's
identity is shown, e.g. a product's "Published by" card). Everything except Partner Profile is
hidden/gated until the seller application is approved.
**Admin portal** (staff-gated, separate from Django's `/admin`): `/admin-portal` (dashboard),
`/admin-portal/products` (list/create/edit, full form incl. media/features/changelog/compatibility/
files), `/admin-portal/{orders,customers,reviews,licenses}`, `/admin-portal/{categories,tags,
partners,collections}` (taxonomy CRUD — Partners includes a Pending/Approved/Rejected review queue
for seller applications), `/admin-portal/settings` (live system status),
`/admin-portal/settings/{users,roles}` (role-based staff access).

## API endpoints

- Storefront: `GET /api/home`, `/api/products/`, `/api/products/<slug>/`, `/api/categories/`, `/api/collections/`
- Auth: `GET /api/auth/csrf`, `GET|PATCH|DELETE /api/auth/me`, `POST /api/auth/{register,login,logout,change-password}`
- Admin (staff): `GET /api/admin/{stats,options,system-status}`; `GET|POST /api/admin/products`,
  `GET|PATCH|DELETE /api/admin/products/<id>`, file upload at `/api/admin/products/<id>/files`;
  CRUD at `/api/admin/{categories,tags,partners,collections,roles}`; `GET /api/admin/{licenses,orders,
  users,customers,reviews}` plus their action routes (revoke/restore/extend a license, set an order's
  status, update a user's role). A product's `product_code` auto-syncs to its licensing SKU on save
  (see `catalog/signals.py`) — creating/editing/publishing a product is immediately reflected in what
  the activation API will authorize.
- Partner self-service (auth-gated): `POST /api/partner/apply` (become a seller — company name +
  optional logo, creates a pending `Partner`), `GET|PATCH /api/partner/profile` (reachable at any
  application status), `GET /api/partner/sales` (approved partners only — own orders/revenue, no
  customer PII). Product/file/media CRUD is shared with staff via the `/api/admin/products*` routes
  (`IsStaffOrPartner` scopes a non-staff caller to their own approved partner automatically).
- **Licensing (byte-compatible, do not change): `GET /api/license/products`, `POST /api/license/activate`**

## Admin / test access

A staff user is seeded for local admin access: `admin@bimhive.ai` / `BimHiveAdmin!2026`
(create/rotate with `python manage.py shell`). Sign in, then open `/admin-portal`.

---

## Testing

```bash
cd api && pytest          # includes golden-master tests for the license API contract
```

---

## Deployment (Railway)

Two services only: **Postgres** and **one combined web service** built from the root
[`Dockerfile`](Dockerfile). See [`ARCHITECTURE.md`](ARCHITECTURE.md) §3.

The image is a 3-stage build: compile the Next.js frontend to a standalone bundle, install
Python dependencies, then a slim runtime with both Node and Python. [`scripts/start.sh`](scripts/start.sh)
runs migrations + `collectstatic`, then starts gunicorn privately on `127.0.0.1:8000` and Next.js
publicly on Railway's `$PORT` — Next proxies `/api`, `/admin`, and `/static` to Django internally
(see `web/next.config.mjs`), so only one port is ever exposed.

**Setup:**
1. Create a Railway project, add a **Postgres** database, and a second service pointing at this
   repo (Railway auto-detects the root `Dockerfile` and `railway.json`).
2. Set the web service's environment variables (ask Claude for the current list, or see
   `.env.example` — every var there except the local-dev-only defaults is required in prod).
3. Deploy. `healthcheckPath` in `railway.json` is `/`, so Railway won't cut traffic over until
   both Next.js and Django (via SSR calling the API) are actually serving.

**Local Docker test** (optional, needs Docker Desktop running):
```bash
docker build -t bimhive .
docker run -p 3000:3000 --env-file .env -e PORT=3000 bimhive
```
