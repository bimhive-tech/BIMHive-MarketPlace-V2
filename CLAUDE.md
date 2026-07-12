# BIM Hive Marketplace — Project Rules (CLAUDE.md)

> **Start here:** before planning or writing anything, read **`REBUILD_PROMPT.md`** (the project
> brief), **`style.md`** (the design system), and the **`design/`** folder (logo, hero image, and
> UI mockups — see `design/README.md` for what each file is).

These rules are **binding**. Follow them on every task, without exception. At the end of every
task, append the **Rules Compliance Checklist** (§10) so it's clear the rules were followed.

---

## 1. The Golden Rules (never break these)

1. **No inline.** No inline styles, no inline `<script>`, no giant "do-everything" files. Extract
   logic, markup, and styles into their own small modules. Prefer many small readable files over
   a few large ones.
2. **No Bootstrap, no Tailwind.** Style with **CSS Modules** (`Component.module.css`) co-located
   with each component, on top of a shared **design-token** layer (CSS variables). No utility-class
   frameworks, no CSS-in-JS strings inline.
3. **Modular & reusable.** Everything is a component. If a piece of UI or logic appears twice, it
   becomes one shared component/util/hook. Never copy-paste code.
4. **Readable, low-token code.** Write so any human *or* AI can understand a file quickly without
   reading the whole repo: descriptive names, single responsibility per file, short functions,
   comments only where intent isn't obvious. Optimize for "understandable in the fewest tokens."
5. **Fully responsive.** Everything must work and look good on **desktop, tablet, and phone**.
   Mobile-first CSS; test all three widths before calling anything done.
6. **No placeholders, no hardcoding.** No lorem ipsum, no fake/dummy data, no magic numbers, no
   hardcoded URLs/keys/paths. Content comes from the DB/API, config from env vars, constants from a
   named tokens/config file.
7. **Beautiful animations.** Motion is a first-class part of the design — purposeful, smooth
   transitions and micro-interactions everywhere it adds polish (never gratuitous). Always respect
   `prefers-reduced-motion`.
8. **Always update the README** when behavior, structure, setup, or scripts change.
9. **Good file structure.** Predictable, feature-oriented folders (§7). A newcomer should guess
   where a file lives.
10. **End every task with the Rules Compliance Checklist** (§10).

---

## 2. Tech Stack

- **Frontend:** React + **Next.js** (App Router, TypeScript) — chosen for SEO (SSR/SSG, metadata,
  sitemap, JSON-LD structured data).
- **Backend:** **Django** (+ Django REST Framework) as the API layer.
- **Database:** **PostgreSQL.**
- **File storage:** **Cloudflare R2** for all attachments/downloads (S3-compatible).
- **Styling:** CSS Modules + design tokens (CSS variables). **Animation:** a small motion system
  (tokens for duration/easing) using Framer Motion for orchestrated animations and CSS transitions
  for simple ones. No Tailwind/Bootstrap.

---

## 3. Architecture & Deployment (important constraint)

- **Railway = exactly two services:** (1) **Postgres**, and (2) **one combined web service that
  runs BOTH the Next.js frontend and the Django backend** — they are NOT split into separate
  services. Design the app so front + back build and run together in a single deployable unit
  (monorepo, single container/process group; e.g. Next.js serves the app and Django serves the API
  behind the same service, or one is proxied through the other). Do not architect anything that
  requires more than these two services.
- **Local dev mirrors prod:** local Postgres + local R2-compatible storage (MinIO). Never point
  local at production data or credentials.
- **Secrets** live only in `.env` (real) / `.env.example` (placeholders only). Never commit real
  secrets.

---

## 4. Styling & Animation Conventions

- One `*.module.css` per component; global CSS limited to reset + design tokens.
- All colors, spacing, radii, font sizes, shadows, z-index, and motion values come from **tokens**
  (CSS variables in a single source of truth). No raw hex or px scattered in components.
- Mobile-first; use a defined breakpoint scale for tablet/desktop.
- Animations: consistent easing/duration tokens; entrance/hover/state transitions; page/section
  reveals; always gated by `prefers-reduced-motion: reduce`.

---

## 5. Content & Configuration

- Every string of real content, every price, every asset URL comes from the API/DB — not the
  component.
- Environment-specific values (API base URL, R2 bucket, Stripe keys, etc.) come from env.
- Repeated literals become named constants; no magic numbers/strings.

---

## 6. Documentation

- Keep `README.md` current: what the app is, setup, env vars, how to run locally (front + back +
  db + storage), how to deploy, and the project structure.
- Each major module/folder gets a short note (in the README or a local `README`) explaining its
  purpose, so navigation is cheap.

---

## 7. Suggested File Structure (adjust in planning, keep the spirit)

```
/web                      # Next.js frontend
  /app                    # routes (App Router)
  /components             # reusable UI components (each: Component.tsx + Component.module.css)
  /features              # feature-grouped components (catalog, checkout, account, ...)
  /lib                    # api client, helpers, hooks
  /styles                 # tokens.css, reset.css, globals
  /config                 # constants, env access
/api                      # Django backend
  /<apps>                 # catalog, licensing, orders, accounts, ...
  /config                 # settings, urls
docker-compose.yml        # local postgres + minio
README.md
CLAUDE.md
```

- Co-locate a component with its styles (and test if present).
- One component per file; one responsibility per module.

---

## 8. Domain Rule — ONE "Product" concept

There is exactly **one** sellable entity: **Product**. A Product may be a Revit plugin, script,
template, library, or service — differentiated by a `type`/category field, **not** by a separate
model. Do not create a parallel "Plugin" model or `/plugins/...` routes. (v1 had a confusing
Plugin-vs-Product split — do not repeat it.)

---

## 9. Page Inventory (living list — confirm & expand, don't miss any)

**Public / storefront**
- Home
- Catalog / browse all products (filters + sort)
- Search results
- Category page
- Collections index + Collection detail
- **Product Detail** (tabs: Overview, Features, Reviews, Compatibility, Documentation, Support)
- Documentation index + Documentation detail
- Knowledge Base index + article
- Blog index + post
- Partner/seller public profile
- "Sell on BIM Hive" / Become a Seller landing
- Static: About, Contact, FAQ, Terms of Service, Privacy Policy, Refund Policy

**Auth**
- Sign in
- Sign up
- Forgot password / reset password
- Email verification

**Cart & checkout**
- Cart
- Checkout / payment
- Order confirmation (thank-you)
- Payment failed / retry

**User account dashboard** (nav confirmed from mockups)
- Overview
- Licenses (license keys, machine fingerprint, trial/active/expired status, seats, renew, download)
- Subscriptions (view/manage recurring plans)
- Orders & Invoices (history, receipts/invoices)
- Payment Methods
- Address (billing address)
- Downloads (purchased items + download files by version)
- Profile (name, email, avatar, company, bio)
- Security (password, active sessions)
- Notifications
- Support Tickets (create/view)
- My Reviews

**System**
- 404, 500 error pages
- Maintenance / empty states / loading skeletons

**Admin Portal** — *to be defined from the mockup images you'll provide.* Do NOT assume v1's
structure; parts of it "don't fully make sense." Derive requirements from the images + confirmed
needs. (Expected areas at minimum: Dashboard, Products, Collections, Categories, Tags, Partners,
Orders, Customers, Reviews, **Licenses**, Support Tickets, Knowledge Base, Settings: General /
Payments / Emails / Users / Roles & Permissions.)

---

## 10. Rules Compliance Checklist (append at the END of every task)

```
### ✅ Rules Compliance
- [ ] No inline styles/scripts; split into small modules
- [ ] No Tailwind/Bootstrap (CSS Modules + tokens)
- [ ] Modular, reusable components; no duplicated code
- [ ] Clean, low-token, self-documenting code
- [ ] Responsive on desktop / tablet / phone
- [ ] No placeholders or hardcoded values
- [ ] Beautiful animations + respects prefers-reduced-motion
- [ ] README updated
- [ ] Good file structure
```
Tick each box. If any rule genuinely doesn't apply to the task, mark it `N/A` and say why in one line.

---

## 11. Definition of Done

A task is done only when: it meets all Golden Rules, works responsively on all three device sizes,
uses real data/config (no placeholders), is animated where appropriate, the README is updated, and
the Rules Compliance Checklist is appended and honest.
```
