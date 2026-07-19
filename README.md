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
- .NET SDK 9+ and the WiX v5 CLI, only if you're building/testing the auto-generated installer
  pipeline (`installer/`):
  ```bash
  dotnet tool install --global wix --version 5.0.2   # v7+ requires accepting a paid maintenance fee — avoid it
  wix extension add -g WixToolset.UI.wixext/5.0.2
  ```

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
/api      Django backend (catalog, licensing, accounts, reviews, installer)
/infra    docker-compose (Postgres + MinIO), deploy config
design/   brand assets + UI mockups (design source of truth)
```

## Routes (built so far)

**Storefront**: `/` (home), `/catalog` (browse + category filter), `/products/<slug>` (detail).
**Cart**: `/cart` (real, localStorage-backed), `/checkout` (honest "coming soon" stub — no fake
payment flow until Stripe/PayPal are wired).
**Auth**: `/login`, `/signup` (session cookies, CSRF-protected).
**Account** (auth-gated, shared sidebar shell): `/account` (overview), `/account/licenses` (license
keys, bound machines, and a "this isn't my computer anymore" self-service reactivation that frees
a machine binding so the license can activate on a new PC — rate-limited to once every 90 days),
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
files/**Installer Build** — upload a compiled `.dll` + `.addin` manifest per Revit year plus any
resource/dependency files, and BIMHive packages them into a real signed `.msi` automatically; see
"Auto-generated installers" below), `/admin-portal/{orders,customers,reviews,licenses}`,
`/admin-portal/{categories,tags,partners,collections}` (taxonomy CRUD — Partners includes a
Pending/Approved/Rejected review queue for seller applications), `/admin-portal/settings` (live
system status), `/admin-portal/settings/{users,roles}` (role-based staff access). The same
Installer Build tab is available to partners on their own products in `/partner-portal/products`.

## Auto-generated installers

Partners/staff no longer hand-build `.msi` installers with a separate desktop tool. On the
**Installer Build** tab of a product's edit page:
1. Upload the compiled `.dll` and `.addin` manifest for each Revit year you support.
2. Optionally add resource/dependency files, each with a destination:
   - `{ADDIN_DIR}` — per-user, no install prompt, lands in `%APPDATA%\Autodesk\Revit\Addins\<year>\`.
   - `{INSTALL_DIR}` — machine-wide, lands in `%ProgramFiles%\BIMHive\<Plugin Name>\`; using this at
     all makes the whole installer per-machine (Windows Installer scope is package-level, so it
     can't be mixed component-by-component).
3. Click **Build Installer** — the backend generates a WiX v5 source file and shells out to the
   `wix` CLI (see Prerequisites) to produce a real `.msi`, then wires it into the product's normal
   downloads automatically.

When a customer downloads a build produced this way, `/api/account/downloads/<id>/get` zips the
`.msi` together with a `<productCode>.key` file containing their own license key (already issued at
purchase time), instead of a bare redirect — no copy-pasting a key by hand. A manually-uploaded
product file (not built by this pipeline) keeps the old plain-redirect behavior.

See `installer/` (models, `wxs_generator.py`, `builder.py`, `api.py`) — and the project's licensing
reference notes for the legacy tool this replaces and why (unstable `UpgradeCode`/`Version` per
build, unsigned client-trusted activation response).

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
- Installer builds (staff/partner, same `?mine=1` scoping as products): `GET|POST
  /api/admin/products/<id>/plugin-builds`, `GET|PATCH|DELETE /api/admin/plugin-builds/<id>`,
  file uploads at `/api/admin/plugin-builds/<id>/{dll,addin,resources}`,
  `DELETE /api/admin/plugin-builds/<id>/resources/<id>`, `POST /api/admin/plugin-builds/<id>/build`
  (runs the WiX packaging pipeline synchronously and returns status + build log),
  `GET /api/admin/plugin-builds/destination-options` (the `{ADDIN_DIR}`/`{INSTALL_DIR}` tokens +
  their real on-disk hint text — single source of truth shared with the frontend).
- Account: `POST /api/account/licenses/machines/<id>/reactivate` (release a machine binding so the
  license can activate on a new PC — self-service, rate-limited).
- **Licensing (byte-compatible, do not change): `GET /api/license/products`, `POST /api/license/activate`**
  — the response now additionally includes a `signature` field (HMAC over the decision fields,
  keyed by `LICENSE_SIGNING_KEY`) when that env var is set; this is purely additive; older shipped
  plugins that don't read it are unaffected.

## Admin / test access

A staff user is seeded for local admin access: `admin@bimhive.ai` / `BimHiveAdmin!2026`
(create/rotate with `python manage.py shell`). Sign in, then open `/admin-portal`.

---

## Testing

```bash
cd api && pytest          # includes golden-master tests for the license API contract
```

`installer/test_builder.py` runs real WiX builds (no mocking) end to end — needs the WiX CLI on
PATH (see Prerequisites). The rest of the suite doesn't touch WiX and runs anywhere.

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
