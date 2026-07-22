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
groups: Django core, `DATABASE_URL`, Cloudflare R2, licensing (`LICENSE_PEPPER`), and payments —
Stripe/PayPal are scaffolded but unused; **Paymob is the one actually wired up** (`PAYMOB_SECRET_KEY`,
`PAYMOB_PUBLIC_KEY`, `PAYMOB_HMAC_SECRET`, `PAYMOB_INTEGRATION_ID` — the last has no working default,
see "Checkout" below). **Never commit `.env`.**

**`R2_PUBLIC_BASE_URL` is still unset**, so product gallery images/covers and partner logos serve
over a presigned link instead of a real permanent public URL (see `STORAGES["public_media"]` in
`config/settings.py`) — this is fine functionally (`catalog/storage.py::refresh_storage_url`
re-signs the URL fresh on every API read, so nothing ever actually goes stale/broken), but it's
extra signing work on every request that a real public URL wouldn't need. Set it once the R2
bucket's public access (an `r2.dev` dev URL or a connected custom domain, from the Cloudflare R2
dashboard) is turned on — no other code change needed, `refresh_storage_url` just becomes a no-op
and everything switches to permanent URLs automatically.

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
  No key is baked into the `.exe` — see "Client-side license enforcement" below for what actually
  makes a key required to use the plugin at all, and where the customer types it in.
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

## Client-side license enforcement (the LicLoader shim)

Uploading a `.dll` + `.addin` isn't enough on its own — Revit will happily load and run any add-in
with no key at all unless something on the machine actually stops it. That something is
`LicLoader.dll`, a small prebuilt activation shim vendored into this repo at
`api/installer/vendor/LicLoader.dll` (source lives in a separate, non-Revit-API-buildable C# project
outside this repo — see `api/installer/vendor/README.md` for exactly where and how to rebuild it).

Every installer build wraps the real plugin with it, transparently, at packaging time
(`installer/license_shim.py`, wired into `installer/builder.py::_stage_payload` and
`installer/nsis_generator.py`):
1. The uploaded `.addin` manifest gets rewritten so its `<Assembly>`/`<FullClassName>` point at
   `LicLoader.dll` instead of the real plugin — Revit now loads the shim as the add-in entry point,
   not the plugin directly. `<AddInId>` and everything else is left untouched.
2. `LicLoader.dll` itself, a `_real_plugin.txt` hint (the real plugin's filename) and a `_license.bin`
   config (JSON despite the name — the product code + trial length LicLoader should request) all get
   staged as siblings of the rewritten `.addin` in the same Revit Addins folder.
3. On Revit startup, LicLoader computes a hardware fingerprint, calls this same server's
   `/api/license/activate` (same byte-compatible contract described below), and only if that
   succeeds does it load the real plugin via reflection and forward Revit's `OnStartup`/`OnShutdown`
   calls to it — an unlicensed machine never reaches the real plugin's code at all.
4. If activation comes back unauthorized, LicLoader shows a real "BIM Hive Activation" Windows
   dialog with a text box for the key — **this is where the customer actually types the key** they
   copied from `/account/licenses`. A successful key gets cached to
   `%APPDATA%\BIMHive\Licenses\<productCode>.key` so it's not re-typed on every launch. When the
   denial is specifically an expired trial (not a missing/blocked one), the dialog says so by name —
   "Your {N}-day free trial has ended..." — rather than a generic "Access denied," using the
   product's configured trial length from `_license.bin`. A trial never silently renews once its
   `MachineLicense` row exists (server-side, see below) — expiry always means a real key is required
   from then on for that machine.
5. A key is **always** required to activate — trial or paid, there's no anonymous/keyless grant on
   the plugin side (see "Free trials" below for where a trial key actually comes from). Once
   authorized, LicLoader tells the customer so with a "your trial is active, N remaining" notice
   whenever the status isn't a paid key — shown right after the very first successful key entry, and
   again on later launches once the key is cached and re-validates silently with no prompt. A
   "License Key" button LicLoader adds to its own Ribbon tab lets the customer open that same
   key-entry dialog voluntarily at any time — e.g. to upgrade from a trial to a paid key — without
   needing to be denied first or restart Revit.

Rewriting a `.addin` that doesn't parse as a normal Revit manifest fails the build loudly
(`AddinRewriteError` → `BuildError`) rather than silently shipping the real plugin unwrapped and
unprotected.

**Staff/partner test-downloads are exempt.** `GET /api/admin/plugin-builds/<id>/download` (the
products list's "..." menu — testing a build before it's published, or without a real purchase)
calls `generate_installer_bytes(build, protect_with_license=False)`, which skips the shim entirely
and ships the plain, unwrapped plugin — the same as before LicLoader existed. This is deliberate,
not a leftover gap: the online license check requires the product to actually be published
(`LicensedProduct.is_active`, see below), which would make it impossible to test-install a build on
a draft product — exactly the case this endpoint exists for. Only customer-facing downloads
(`/account/downloads`, trial downloads) are ever license-protected.

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

**A key is required to activate, always — including a trial.** `/api/license/activate` has no
anonymous/keyless path anymore: if the request carries no key, or a key that doesn't resolve to an
active `ProductPurchase`, the response is a plain `authorized: false, status: "blocked"` denial (see
"Free trials" below for how a trial actually gets its key). `ProductPurchase.is_trial` marks the one
kind of purchase that's free — otherwise it's activated through the exact same `paid_purchase`
branch as a real sale, so seat limits, expiry, and repeat-activation all behave identically; the
response's `status` is `"trial"` instead of `"paid"` purely so the client can phrase things
correctly (see LicLoader above), not because the enforcement path differs.

## Checkout: real purchase flow, one key per copy, Paymob (test mode) collects payment

`POST /api/account/checkout` (`CheckoutView`) takes the client-side cart (`web/lib/cart.tsx` — real,
localStorage-backed, never had server state) and creates `PENDING` `ProductPurchase` rows — one per
unit, never one purchase covering a quantity: buying qty=3 of the same product creates three
independent rows, each its own `license_key`, each `seats=1`, `amount` = unit price. One key per
seat: each copy activates its own machine, none of the three keys are tied to each other.
(`ProductPurchase` has no `unique_together(user, product)` constraint — holding several independent
keys for the same product is the normal case.) `/account/orders` and `/account/licenses` show one
row/card per purchase; **`/account/downloads` still shows exactly one card per distinct product**
regardless of how many keys you hold for it (`AccountDownloadListView` dedupes with
`distinct("product__product_id")`), since the files carry no per-purchase data.

**Nothing is ever marked `PAID` by `CheckoutView` itself.** It also creates a Paymob payment
intention for the order's total (`licensing/paymob.py::create_intention`) and returns a
`checkoutUrl` — the `/checkout` page redirects the browser straight to it, Paymob's own hosted
Unified Checkout page, so a card number never touches this app at all. Paymob confirms (or doesn't)
via a server-to-server webhook, `POST /api/webhooks/paymob` (`PaymobWebhookView`, registered at the
root, not under `/api/account/` — Paymob has no session to authenticate with). That webhook is the
**only** place a purchase ever becomes `PAID`: it verifies an HMAC-SHA512 signature
(`paymob.verify_hmac`, over a fixed field list Paymob's docs specify) before touching anything, and
is idempotent (a `PAID` purchase is left alone on redelivery). `/checkout/confirmation` — where
Paymob redirects the browser back to — never trusts that redirect for the actual grant decision
either; it polls `GET /api/account/checkout/status?reference=` (matching on `payment_reference`,
shared across every purchase from one checkout call) until the webhook has landed, showing a
"confirming…" state in the meantime and clearing the cart only once purchases genuinely come back
non-pending. See `api/installer/vendor/README.md`-style reasoning: a client-side "it worked" signal
is never sufficient for something that grants a real license.

**Test mode specifics, worth knowing before testing:**
- Paymob's test/sandbox card (from their published test-credentials docs): `4987654321098769`.
  The card *number* is the fixed part sandboxes actually check — expiry just needs to be any real
  future month/year (e.g. `12/29`) and CVV any 3 digits (e.g. `123`); update the month/year as time
  passes rather than reusing a fixed date that'll eventually read as expired. Any cardholder name.
- The Paymob merchant account behind the current test keys is Egypt-only (settles in EGP) —
  `PAYMOB_CURRENCY` (default `"EGP"`) is what's actually sent, regardless of a product's own
  `currency` field. The cart's real numeric total still flows through end-to-end, just relabeled;
  see the comment on `PAYMOB_CURRENCY` in `settings.py`. Not real FX, not meant to be.
- `PAYMOB_INTEGRATION_ID` has no working default — it's a per-merchant-account ID from the Paymob
  dashboard's Payment Integrations page and can't be guessed; `CheckoutView` fails with a clear 400
  until it's set.
- **The monthly subscription duration is TEMPORARILY 10 minutes, not 30 days** — see
  `account_api.py::_subscription_duration`'s comment. This is deliberate, for testing that a Paymob
  payment → webhook → license actually revoking on expiry works end to end without waiting a month;
  change it back to `timedelta(days=30)` once that's confirmed. Yearly is untouched (365 days).

(A subscription-priced product's cart item also carries a `billingPeriod` — see "Subscription
pricing" below for how that changes `amount`/`expires_at`.)

## Subscription pricing: monthly/yearly, on top of the same one-time flow

A product's normal `price` is one-time and perpetual, unchanged from before. Setting
`Product.monthly_price` and/or `yearly_price` on the **Pricing & License** tab (either or both —
leave both blank to keep one-time pricing) turns it into a subscription: `Product.is_subscription`
flips on, `BuyBox` swaps the single price for a `BillingToggle` (Monthly/Yearly, defaulting to
Yearly — the better-value option leads), and `Product.yearly_savings_percent` drives the "Save N%"
badge shown on the Yearly option (computed once, server-side, as `1 - yearly / (monthly × 12)`; not
shown at all if yearly isn't actually cheaper, so it can never read as a false discount).

The chosen interval rides along in the cart (`CartItem.billingPeriod`, part of the line item's key
so a Monthly and a Yearly line for the same product never merge into one with an ambiguous price)
straight through to `CheckoutView`, which is where a subscription purchase turns into something
the existing licensing system already knows how to enforce: `amount` is the chosen interval's price,
and `expires_at` is set 30 (monthly) or 365 (yearly) days out — the exact same field a `LicenseCode`
redemption or a trial already uses to expire a purchase. There's no separate recurring-billing
system, no webhook, nothing that re-charges a card on renewal (no payment processor is connected at
all yet, same as one-time checkout) — a subscription purchase is simply a purchase with a shorter
fuse, reusing 100% of the seat/expiry/activation machinery `/api/license/activate` already has.
`ProductPurchase.billing_period` (`""` / `"monthly"` / `"yearly"`) is stored purely for display —
`/account/orders` and `/account/licenses` show it as a small pill next to the price.

A product's one-time `price` still exists and is still what free-claim/checkout falls back to for a
subscription product that also lists one (buying it with no `billingPeriod` in the cart item), and
`Product.is_free`/`price_label` both know to ignore a subscription product's (irrelevant, usually
`$0.00`) one-time `price` field rather than misreporting it as free.

**The interval is also switchable on `/checkout` itself, not just back on the product page.**
`CartItem` carries `monthlyPrice`/`yearlyPrice` alongside `unitPrice` (set once, at add-to-cart time,
same snapshot-not-live-fetched approach the rest of the cart already uses) so `useCart().
setBillingPeriod(key, period)` can recompute the price and re-key the line entirely client-side, no
API round-trip. Each subscription line shows its own `BillingToggle` (same "Save N%" badge logic as
the product page) plus an honest "Grants access for 1 month/year — no auto-renewal, check out again
before it expires" note, since there's genuinely no recurring-charge mechanism yet (see above) and
the checkout copy should never imply one.

## Cancel / refund: self-service, 30-day window, abuse-proof by construction

`POST /api/account/orders/<id>/refund` (`AccountOrderRefundView`) is the self-service side of the
"30-Day Money Back Guarantee" the buy box has always advertised — until this shipped, that copy had
no mechanism behind it. Scoped to the caller's own order, only while `payment_status == "paid"`, and
only within `REFUND_WINDOW_DAYS` (30) of `paid_at`; past that it's a clear "contact support" error
instead of silently failing. Reuses `licensing/services.py::revoke_purchase_access` — the exact same
function staff use from `/admin-portal/orders` — so a self-service refund and a staff-issued one
behave identically. The **Cancel & Refund** button lives on `/account/orders`, next to each
refund-eligible order.

**Why refunding can't be used to farm a second free trial:** a trial is a real
`ProductPurchase(is_trial=True)`, and `AccountPluginBuildTrialDownloadView` only ever creates one per
`(user, product)` — backed by a DB partial-unique index (`one_trial_purchase_per_user_product`), not
just an app-level check, so even two near-simultaneous requests can't slip through and mint two. It
looks for an existing one first and reuses it, never resets `expires_at`, and refunding it
(`revoke_purchase_access`) just flips its `payment_status`, it doesn't delete the row or let a new
one be created. Redownloading the trial installer, or the plugin re-activating after a refund, both
land on that same purchase — now denied, never a fresh one.

**Why a second *account* on the same machine can't get a second trial either:**
`MachineLicense.used_trial` is a permanent, one-way flag — set the first time a trial purchase ever
binds a given `(product, machine)`, never cleared. `license_activate_api` denies (`status:
"trial_used"`) any attempt to bind a *different* trial purchase to a machine that already has it,
regardless of which account/key presents it — closing a real gap the keyed-trial redesign above
introduced: without this, a machine whose first trial lapsed could get "rebound" to a brand-new
trial purchase from a second account, since the machine→purchase link is resolved by whichever valid
key shows up, not by which machine has already used its one trial. A real paid key still always
works on that machine (the upgrade path is unaffected); only a second *trial* is blocked.

## Free trials: configurable per product, a real key, no purchase needed

Each plugin product has a trial length set on its **Pricing & License** tab as days + hours +
minutes (`Product.default_trial_days/hours/minutes`, kept in sync onto the activation SKU by
`sync_license_sku` same as everything else there) — a new product defaults to 7 days, staff/partners
can change it per product, and setting all three to 0 turns the trial off entirely for that product
(the storefront's "Download Trial" button then just doesn't render — see `Product.has_trial`).

On a plugin product's page, `TrialDownloadCard` (rendered inside `BuyBox` when `has_trial` is true)
lets any logged-in customer download the installer with **no checkout, no payment** —
`GET /api/account/downloads/plugin-builds/<id>/trial`
(`AccountPluginBuildTrialDownloadView`) generates the same on-demand `.exe`
(`installer/builder.py::generate_installer_bytes`) the paid flow does, still with no key embedded in
it, but it also creates (idempotently — the same call twice never resets the clock or issues a
second key) a real `ProductPurchase(is_trial=True, payment_status=PAID, amount=0)` with
`expires_at` set from the product's configured trial length. That purchase's `license_key` is what
shows up on `/account/licenses` with a "Trial" pill — **the customer has to copy it into the plugin
themselves**, exactly like a paid key, because the plugin no longer accepts activating without one
(see "Licensing" above). Once it expires, `/api/license/activate` denies it through the normal
`is_license_active`/expiry path — nothing trial-specific, the same code paid keys already go
through.

The legacy-compatible `GET /api/license/products` endpoint still returns `defaultTrialDays` as a
single whole integer (rounded **up** from the precise day/hour/minute total, so an old plugin
reading it as a plain int never sees a shorter trial than configured) — that field's shape is part
of the locked byte-compatible contract and was never going to change.

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
- Account: `POST /api/account/checkout` (creates PENDING `ProductPurchase` rows + a Paymob payment
  intention, returns a `checkoutUrl` to redirect to — see "Checkout" above),
  `GET /api/account/checkout/status?reference=` (polled by `/checkout/confirmation` to find out once
  the webhook has confirmed payment), `POST /api/account/orders/<id>/refund` (self-service
  cancel/refund, own orders only, 30-day window — see "Cancel / refund" above),
  `POST /api/account/licenses/redeem` (redeem a
  staff-generated license code onto the caller's own account — see "License codes" above),
  `GET /api/account/downloads/plugin-builds/<id>/get` (generates and streams the bare `.exe` live —
  no zip, no key attached; see "Auto-generated installers" above),
  `GET /api/account/downloads/plugin-builds/<id>/trial` (any logged-in customer, no checkout/payment —
  same bare `.exe`, gated on `Product.has_trial`, also issues a real trial `ProductPurchase`/key;
  see "Free trials" above).
- **Payment webhook (no auth, HMAC-verified instead): `POST /api/webhooks/paymob`** — registered at
  the URL root (not under `/api/account/`), the only place a checkout purchase ever becomes `PAID`;
  see "Checkout" above.
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

No local Postgres? Point `DATABASE_URL` at a throwaway SQLite file (or `:memory:` for a one-off run)
instead of editing `.env` — `dj_database_url` (used by `config/settings.py`) understands the
`sqlite://` scheme directly, migrations apply cleanly, and the whole suite runs against it:
```bash
DATABASE_URL="sqlite:///:memory:" pytest   # or sqlite:///path/to/file.sqlite3 for a persistent one
```
A handful of tests are genuinely Postgres-only and fail under SQLite for reasons unrelated to
whatever you're testing — not bugs, just what the real deployed database (Postgres, always) does
differently: `AccountDownloadListView`'s `distinct("product__product_id")` (Postgres `DISTINCT ON`,
unsupported elsewhere), and a couple of assertions on `Sum()`-aggregated `Decimal` string formatting
(`"25"` vs `"25.00"`).

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
