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
- NSIS (`makensis`), only if you're building/testing the auto-generated installer pipeline
  (`installer/`) — Windows: `winget install NSIS.NSIS`; Debian/Ubuntu/Docker: `apt-get install nsis`.

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
**Cart**: `/cart` (real, localStorage-backed), `/checkout` (real order review + "Complete Purchase" —
see "Checkout" below for why there's no card field yet), `/checkout/confirmation` (thank-you page).
**Auth**: `/login`, `/signup` (session cookies, CSRF-protected).
**Account** (auth-gated, shared sidebar shell): `/account` (overview), `/account/licenses` (license
keys, bound machines, a seat-usage indicator when a purchase allows more than one machine — each
seat activates on one machine, once, with no customer self-service way to move it; see "Licensing"
below), `/account/orders`, `/account/downloads`, `/account/profile` (full profile editor: name/company/
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
resource/dependency files, and BIMHive packages them into a real `.exe` installer automatically; see
"Auto-generated installers" below), `/admin-portal/{orders,customers,reviews,licenses}`,
`/admin-portal/{categories,tags,partners,collections}` (taxonomy CRUD — Partners includes a
Pending/Approved/Rejected review queue for seller applications), `/admin-portal/settings` (live
system status), `/admin-portal/settings/{users,roles}` (role-based staff access). The same
Installer Build tab is available to partners on their own products in `/partner-portal/products`.

## Auto-generated installers (built on demand, never cached)

Only relevant to **Revit Plugin** products (`Product.type == "plugin"`) — for any other product
type (Dynamo Script, Template, BIM Library, Service, Other) the tab doesn't show at all, and
Files & Downloads is the only delivery mechanism. Switching a product's Product Type dropdown
(Pricing & License tab) live shows/hides the Installer Build tab without needing to save first;
the backend rejects a build for a non-plugin product either way (`installer/api.py`).

Partners/staff no longer hand-build installers with a separate desktop tool — but there's
also no "Build Installer" step or cached artifact anymore. The **Installer Build** tab on a
product's edit page is upload-only:
1. Upload the compiled `.dll` and `.addin` manifest for each Revit year you support.
2. Optionally add resource/dependency files, each with a destination:
   - `{ADDIN_DIR}` — per-user, no install prompt, lands in `%APPDATA%\Autodesk\Revit\Addins\<year>\`.
   - `{INSTALL_DIR}` — machine-wide, lands in `%ProgramFiles%\BIMHive\<Plugin Name>\`; using this at
     all makes the whole installer per-machine (Windows Installer scope is package-level, so it
     can't be mixed component-by-component).

The `.exe` itself is generated **live, on the spot, in exactly two places** — and never written to
storage in either case:
- **A customer downloading it** (`/account/downloads`, or the virtual entry on `/api/account/downloads`
  that appears once both files are uploaded) — `AccountPluginBuildDownloadView` calls
  `installer/builder.py::generate_installer_bytes` and streams the bare `.exe` straight back, no zip,
  no key attached. Every download re-runs the NSIS build; nothing is reused between downloads.
  **The customer types their license key into the plugin themselves** (copied from
  `/account/licenses`) — there's deliberately no auto-import: the plugin only ever works once a key
  is entered, and the first `/api/license/activate` call that carries one is what binds it to that
  machine and starts showing its end date on the Licenses page.
- **Staff/partner testing it** from the products list's **"..." menu** (per row, next to Edit) —
  `GET /api/admin/plugin-builds/<id>/download` runs the same live build and streams the raw `.exe`
  back directly, no purchase or license key needed, including for an unpublished draft product. The
  menu fetches that product's uploaded builds lazily on open and lists one entry per Revit year;
  since this is a live build, the frontend uses fetch+blob rather than a plain link, so a failed
  build shows its actual error instead of "downloading" a JSON error body.

This was a deliberate choice, not an oversight: the `.exe` carries no per-customer data (unlike the
legacy tool, which baked a machine whitelist directly into the binary — see the licensing reference
notes), so there's nothing to gain from pre-building and caching one ahead of time. Every trigger —
customer or admin — gets a fresh build.

The installer is built by NSIS (`makensis`), not WiX/MSI — WiX was tried first and dropped after a
real production failure: it explicitly only supports running on Windows
(`warning WIX0000: ... All behavior after this point is undefined` on any other OS) and silently
miscompiled every generated `.wxs` file on Railway's Linux container. NSIS is a real, long-supported
Linux-hosted cross-compiler for Windows installers (`apt-get install nsis` in the Dockerfile).

See `installer/` (models, `nsis_generator.py`, `builder.py`, `api.py`) — and the project's licensing
reference notes for the legacy tool this replaces and why (unstable `UpgradeCode`/`Version` per
build, unsigned client-trusted activation response).

## Licensing: single-use seats, not hardware-locked

The `.exe` an installer build produces is generic — the same file for every buyer of that product
and Revit year. What actually gates use is `/api/license/activate`: the first machine to activate a
purchase's license key claims it, and every other machine trying that same key gets refused
outright, even with the installer and key file in hand. This is deliberately Autodesk-serial-key
simple, not hardware-fingerprint security theater: the server doesn't try to verify the
`machineFingerprintHash` the plugin sends is genuinely MAC/CPU-derived (it can't — that's computed
client-side, and the shipped plugin's request shape is a fixed contract, see "Licensing
(byte-compatible...)" below) — it's just treated as an opaque per-install identifier so a repeat
call from the *same* install doesn't cost a new seat.

**Each seat is single-use, forever, once claimed — there is no customer self-service way to move
one to a different machine.** This was a deliberate choice: the previous version had a "this isn't
my computer anymore" self-service reactivation (rate-limited to once/90 days); it's gone. If a
customer's machine dies, staff resolve it by hand on `/admin-portal/licenses` — either **Release**
(frees that one seat so a different machine can claim it, `AdminLicenseReleaseView` /
`licensing/services.py::release_machine_binding`) or generating them a fresh License Code (see
below) — whichever fits.

`ProductPurchase.seats` (default 1) lets a *single key* be claimed by more than one machine at
once — this is a staff-only override (via the users icon button on `/admin-portal/orders`, e.g. to
comp extra machines onto one key without a real purchase) and is unrelated to how many copies
someone buys. Buying multiple copies is a different mechanism entirely — see "Checkout" below:
each copy bought is its own independent `ProductPurchase`/key, seats=1 each, not one key shared
across seats. `ProductPurchase.has_seat_for()` is still the activation check regardless of which
path set `seats`: an already-claimed machine always re-validates fine (a plugin restart doesn't
cost a seat), a new machine only claims a seat if fewer than `seats` are currently held.
`ProductPurchase.license_status` (`active` / `inactive` / `expired`) is the simplified
customer-facing label shown on `/account/licenses` — `payment_status` has more states than a buyer
needs to reason about.

## Checkout: real purchase flow, one key per copy, no payment processor connected yet

`POST /api/account/checkout` (`CheckoutView`) takes the client-side cart (`web/lib/cart.tsx` — real,
localStorage-backed, never had server state) and turns it into real `ProductPurchase` rows: `PAID`,
no card collected. This is the same honest trade-off `ClaimFreeProductView` already made for
free-only products (see the account API notes there), just extended to any price — Stripe/PayPal
aren't wired up yet, so this is what actually completing a purchase means today, and it's the
only way to exercise the full buy → license → download path with a real (non-free, non-staff)
purchase for testing.

**One purchase per unit bought, never one purchase covering a quantity** — buying qty=3 of the same
product in one cart creates three independent `ProductPurchase` rows, each its own `license_key`,
each `seats=1`, `amount` = unit price. One key per seat: each copy activates its own machine, and
none of the three keys are tied to each other. (This flipped from an earlier version that collapsed
a qty=3 buy into one purchase with `seats=3` — dropped once it became clear that isn't what "3
copies" should mean to a customer holding 3 separate keys; `ProductPurchase` no longer has a
`unique_together(user, product)` constraint, since holding several independent keys for the same
product is now the normal case, not an edge case.) Checking out a product you already own just adds
more purchases/keys — it never edits an existing one. `/checkout` shows an order summary with a
visible "no payment processor" notice and a single Complete Purchase button; `/checkout/confirmation`
is the thank-you page, listing every key from the order (reading the just-completed order out of
`sessionStorage`, since there's no server-side "current order" to fetch — the confirmation data is
handed off client-side at the moment of purchase). When Stripe/PayPal are actually wired up, this
view is exactly where real payment collection needs to be inserted before the `ProductPurchase`
rows are created.

## Free trials: configurable per product, download without buying

Each plugin product has a trial length set on its **Pricing & License** tab as days + hours +
minutes (`Product.default_trial_days/hours/minutes`, kept in sync onto the activation SKU by
`sync_license_sku` same as everything else there) — a new product defaults to 7 days, staff/partners
can change it per product, and setting all three to 0 turns the trial off entirely for that product
(the storefront's "Download Trial" button then just doesn't render — see `Product.has_trial`).

On a plugin product's page, `TrialDownloadCard` (rendered inside `BuyBox` when `has_trial` is true)
lets any logged-in customer download the installer with **no purchase at all** — `GET
/api/account/downloads/plugin-builds/<id>/trial` generates the same on-demand `.exe`
(`installer/builder.py::generate_installer_bytes`) but skips the license-key zip wrapper, since
there's no purchase yet to draw a key from. The trial clock itself isn't started by this download —
it starts the moment the installed plugin's first `/api/license/activate` call comes in with no
`licenseKey`, which already fell into the trial-issuing branch before this feature existed (see
"Licensing" above); the server caps that trial at the product's configured
`default_trial_days/hours/minutes` (`ProductPurchase.trial_minutes_total`), same clamping logic as
always, just now precise to the minute instead of only whole days. Once the trial expires the
already-installed plugin denies access on its own (the activation response's `expiresAt`/
`remainingSeconds` is what it enforces against) — buying a real license just means entering that key
directly in the plugin; nothing needs to be re-downloaded.

The legacy-compatible `GET /api/license/products` endpoint still returns `defaultTrialDays` as a
single whole integer (rounded **up** from the precise day/hour/minute total, so an old plugin
reading it as a plain int never sees a shorter trial than configured) — that field's shape is part
of the locked byte-compatible contract and was never going to change; the real to-the-minute value
only matters to `/api/license/activate`, which already accepted `trialMinutes` before this feature
and needed no contract change at all.

## License codes: redeemable, account-connected replacement for the old key files

The upgrade of the legacy installer-generator's manually-issued license keys (which were baked
directly into a specific compiled loader DLL per machine — see the licensing reference notes) into
something self-service and connected to a real account. On the **License Codes** tab of
`/admin-portal/licenses`, staff pick one specific product, a seat count, and a duration (or
"Lifetime"), and generate a single-use code. That code can be handed to anyone; whoever redeems it
— entered on `/account/licenses` while logged into their own account — gets a real `ProductPurchase`
for that product with the seats/duration the code specified, going through the exact same
seat-aware activation enforcement as anything bought through checkout (see "Licensing" above). A
time-limited redemption (`duration_days` set) actually expires: `ProductPurchase.expires_at` caps
the whole purchase, and `/api/license/activate` returns `status: "expired"` once it passes — staff
can extend a time-limited purchase's date via the existing Extend action on `/admin-portal/licenses`.
A redeemed code always records `amount: 0` regardless of the product's list price, since it's a
comp/grant, not a real transaction — Sales/Orders revenue reporting isn't inflated by it.

## API endpoints

- Storefront: `GET /api/home`, `/api/products/`, `/api/products/<slug>/`, `/api/categories/`, `/api/collections/`
- Auth: `GET /api/auth/csrf`, `GET|PATCH|DELETE /api/auth/me`, `POST /api/auth/{register,login,logout,change-password}`
- Admin (staff): `GET /api/admin/{stats,options,system-status}`; `GET|POST /api/admin/products`,
  `GET|PATCH|DELETE /api/admin/products/<id>`, file upload at `/api/admin/products/<id>/files`;
  CRUD at `/api/admin/{categories,tags,partners,collections,roles}`; `GET /api/admin/{licenses,orders,
  users,customers,reviews}` plus their action routes (revoke/restore/extend/release a license, set an
  order's status, update a user's role, `POST /api/admin/orders/<id>/seats` to set how many machines a
  purchase may bind at once — see "Licensing" above). A product's `product_code` auto-syncs to its
  licensing SKU on save (see `catalog/signals.py`) — creating/editing/publishing a product is
  immediately reflected in what the activation API will authorize.
- Partner self-service (auth-gated): `POST /api/partner/apply` (become a seller — company name +
  optional logo, creates a pending `Partner`), `GET|PATCH /api/partner/profile` (reachable at any
  application status), `GET /api/partner/sales` (approved partners only — own orders/revenue, no
  customer PII). Product/file/media CRUD is shared with staff via the `/api/admin/products*` routes
  (`IsStaffOrPartner` scopes a non-staff caller to their own approved partner automatically).
- Installer builds (staff/partner, same `?mine=1` scoping as products): `GET|POST
  /api/admin/products/<id>/plugin-builds`, `GET|PATCH|DELETE /api/admin/plugin-builds/<id>`,
  file uploads at `/api/admin/plugin-builds/<id>/{dll,addin,resources}`,
  `DELETE /api/admin/plugin-builds/<id>/resources/<id>`,
  `GET /api/admin/plugin-builds/destination-options` (the `{ADDIN_DIR}`/`{INSTALL_DIR}` tokens +
  their real on-disk hint text — single source of truth shared with the frontend),
  `GET /api/admin/plugin-builds/<id>/download` (generates the `.exe` live and streams it back — no
  purchase needed, no caching, works on an unpublished product; this is staff/partner's only way to
  test a build).
- License codes (staff): `GET|POST /api/admin/license-codes` (list/generate, filterable by
  `?product=`/`?status=`), `POST /api/admin/license-codes/<id>/revoke` (only while unredeemed).
  `POST /api/admin/licenses/<id>/release` (staff-only: frees one machine's seat so a different
  machine can claim it — the manual override for a customer whose PC died; see "Licensing" above).
- Account: `POST /api/account/checkout` (turns the client-side cart into real `ProductPurchase` rows —
  no payment collected, see "Checkout" above), `POST /api/account/licenses/redeem` (redeem a
  staff-generated license code onto the caller's own account — see "License codes" above),
  `GET /api/account/downloads/plugin-builds/<id>/get` (generates and streams the bare `.exe` live —
  no zip, no key attached; see "Auto-generated installers" above),
  `GET /api/account/downloads/plugin-builds/<id>/trial` (any logged-in customer, no purchase needed —
  same bare `.exe`, gated on `Product.has_trial`; see "Free trials" above).
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

`installer/test_builder.py` runs real NSIS builds (no mocking) end to end — needs `makensis` on
PATH (see Prerequisites). The rest of the suite doesn't touch NSIS and runs anywhere.

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
